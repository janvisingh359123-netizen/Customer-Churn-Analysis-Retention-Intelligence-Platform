# Customer Churn Backend API
# Built with FastAPI and Pandas for lightning-fast database filtering and analytics

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import pandas as pd
import numpy as np
import os
import json
import io
from datetime import datetime

# Setup FastAPI App
app = FastAPI(title="Churn Retention Intelligence API", version="1.0.0")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "churn_analytics.db")

# In-memory dataframe cache for high-performance sub-second filters
_cached_df = None
_last_cache_time = None

def get_df_from_db(force_reload=False):
    global _cached_df, _last_cache_time
    if _cached_df is not None and not force_reload:
        return _cached_df
        
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run generate_data.py and train.py first.")
        
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            c.customer_id, c.customer_name, c.gender, c.age, c.city, c.state, c.country, 
            c.signup_date, c.contract_type, c.monthly_charge, c.total_spent, c.tenure_months,
            u.login_frequency, u.sessions_per_month, u.avg_session_duration, 
            u.support_tickets, u.products_used,
            f.satisfaction_score, f.complaints_count, f.last_feedback_date,
            ch.churn_status, ch.churn_date, ch.churn_probability, ch.risk_score, 
            ch.risk_segment, ch.rfm_recency, ch.rfm_frequency, ch.rfm_monetary, 
            ch.rfm_segment, ch.churn_drivers
        FROM customers c
        JOIN customer_usage u ON c.customer_id = u.customer_id
        JOIN customer_feedback f ON c.customer_id = f.customer_id
        JOIN churn ch ON c.customer_id = ch.customer_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Calculate Engagement Score & Health Score (mirror ml pipeline)
    sessions_norm = (df["sessions_per_month"] - df["sessions_per_month"].min()) / (df["sessions_per_month"].max() - df["sessions_per_month"].min() + 1e-5)
    duration_norm = (df["avg_session_duration"] - df["avg_session_duration"].min()) / (df["avg_session_duration"].max() - df["avg_session_duration"].min() + 1e-5)
    df["engagement_score"] = np.round((sessions_norm + duration_norm) * 50, 1)
    
    # Customer Health Score
    health_base = 50
    health_sat = df["satisfaction_score"].map({5: 25, 4: 15, 3: 5, 2: -15, 1: -30})
    health_tickets = df["support_tickets"] * -4
    health_complaints = df["complaints_count"] * -10
    health_freq = df["login_frequency"].map({"Daily": 15, "Weekly": 5, "Monthly": -5})
    df["health_score"] = np.clip(health_base + health_sat + health_tickets + health_complaints + health_freq, 0, 100)
    
    _cached_df = df
    _last_cache_time = datetime.now()
    return _cached_df

def apply_global_filters(df, 
                         region: str = None, 
                         age_group: str = None, 
                         contract_type: str = None, 
                         churn_risk: str = None,
                         rfm_segment: str = None):
    filtered_df = df.copy()
    
    if region and region != "All":
        filtered_df = filtered_df[filtered_df["state"] == region]
        
    if contract_type and contract_type != "All":
        filtered_df = filtered_df[filtered_df["contract_type"] == contract_type]
        
    if churn_risk and churn_risk != "All":
        filtered_df = filtered_df[filtered_df["risk_segment"] == churn_risk]
        
    if rfm_segment and rfm_segment != "All":
        filtered_df = filtered_df[filtered_df["rfm_segment"] == rfm_segment]
        
    if age_group and age_group != "All":
        if age_group == "18-25":
            filtered_df = filtered_df[(filtered_df["age"] >= 18) & (filtered_df["age"] <= 25)]
        elif age_group == "26-35":
            filtered_df = filtered_df[(filtered_df["age"] >= 26) & (filtered_df["age"] <= 35)]
        elif age_group == "36-45":
            filtered_df = filtered_df[(filtered_df["age"] >= 36) & (filtered_df["age"] <= 45)]
        elif age_group == "46-60":
            filtered_df = filtered_df[(filtered_df["age"] >= 46) & (filtered_df["age"] <= 60)]
        elif age_group == "60+":
            filtered_df = filtered_df[filtered_df["age"] > 60]
            
    return filtered_df

# Helper function to get filter parameters
def get_filter_params(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    return {
        "region": region,
        "age_group": age_group,
        "contract_type": contract_type,
        "churn_risk": churn_risk,
        "rfm_segment": rfm_segment
    }

@app.get("/api/meta")
def get_metadata():
    """Returns available states and filter parameters for dropdown lists"""
    try:
        df = get_df_from_db()
        states = sorted(df["state"].unique().tolist())
        return {
            "states": ["All"] + states,
            "age_groups": ["All", "18-25", "26-35", "36-45", "46-60", "60+"],
            "contract_types": ["All", "Monthly", "Quarterly", "Annual"],
            "churn_risks": ["All", "Low", "Medium", "High", "Critical"],
            "rfm_segments": ["All", "Champions", "Loyal Customers", "Potential Loyalists", "At Risk", "Lost Customers"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/overview")
def get_overview(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """Executive KPI Cards"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        total_cust = len(filtered)
        if total_cust == 0:
            return {
                "total_customers": 0, "active_customers": 0, "churned_customers": 0,
                "churn_rate": 0.0, "mrr": 0.0, "arr": 0.0, "revenue_at_risk": 0.0,
                "average_clv": 0.0, "net_revenue_retention": 0.0, "churn_cost": 0.0
            }
            
        active_mask = filtered["churn_status"] == "Active"
        churned_mask = filtered["churn_status"] == "Churned"
        
        active_count = int(active_mask.sum())
        churned_count = int(churned_mask.sum())
        churn_rate = round((churned_count / total_cust) * 100, 2)
        retention_rate = round(100 - churn_rate, 2)
        
        # Monthly Recurring Revenue (MRR) - potential from active
        active_mrr = float(filtered[active_mask]["monthly_charge"].sum())
        total_mrr = float(filtered["monthly_charge"].sum())
        arr = active_mrr * 12
        
        # Net Revenue Retention (NRR) - estimated
        nrr = round((active_mrr / total_mrr) * 100, 2) if total_mrr > 0 else 0.0
        
        # Revenue at risk: Monthly charge of Active customers with Critical/High Churn Risk
        high_risk_mask = filtered["risk_segment"].isin(["High", "Critical"])
        revenue_at_risk = float(filtered[active_mask & high_risk_mask]["monthly_charge"].sum())
        
        # Customer Lifetime Value (CLV)
        avg_clv = float(filtered["total_spent"].mean())
        
        # Churn cost: Lost MRR + (Churned Customers * Acquisition Cost of $150)
        lost_mrr = float(filtered[churned_mask]["monthly_charge"].sum())
        churn_cost = lost_mrr + (churned_count * 150.0)
        
        return {
            "total_customers": total_cust,
            "active_customers": active_count,
            "churned_customers": churned_count,
            "churn_rate": churn_rate,
            "retention_rate": retention_rate,
            "mrr": round(active_mrr, 2),
            "arr": round(arr, 2),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "average_clv": round(avg_clv, 2),
            "net_revenue_retention": nrr,
            "churn_cost": round(churn_cost, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trends")
def get_trends(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """Historical Churn Trends & Revenue Impact"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        churned_only = filtered[filtered["churn_status"] == "Churned"].copy()
        if len(churned_only) == 0:
            return {"months": [], "churn_counts": [], "revenue_lost": []}
            
        churned_only["churn_month"] = pd.to_datetime(churned_only["churn_date"]).dt.to_period("M")
        monthly = churned_only.groupby("churn_month").agg(
            churn_count=("customer_id", "count"),
            mrr_lost=("monthly_charge", "sum")
        ).reset_index()
        
        monthly["month_str"] = monthly["churn_month"].astype(str)
        monthly = monthly.sort_values("churn_month")
        
        # Quarterly aggregation
        churned_only["churn_quarter"] = pd.to_datetime(churned_only["churn_date"]).dt.to_period("Q")
        quarterly = churned_only.groupby("churn_quarter").agg(
            churn_count=("customer_id", "count"),
            mrr_lost=("monthly_charge", "sum")
        ).reset_index()
        quarterly["quarter_str"] = quarterly["churn_quarter"].astype(str)
        
        # Yearly aggregation
        churned_only["churn_year"] = pd.to_datetime(churned_only["churn_date"]).dt.year
        yearly = churned_only.groupby("churn_year").agg(
            churn_count=("customer_id", "count"),
            mrr_lost=("monthly_charge", "sum")
        ).reset_index()
        
        return {
            "monthly": {
                "months": monthly["month_str"].tolist(),
                "churn_counts": monthly["churn_count"].tolist(),
                "revenue_lost": [round(float(x), 2) for x in monthly["mrr_lost"].tolist()]
            },
            "quarterly": {
                "quarters": quarterly["quarter_str"].tolist(),
                "churn_counts": quarterly["churn_count"].tolist(),
                "revenue_lost": [round(float(x), 2) for x in quarterly["mrr_lost"].tolist()]
            },
            "yearly": {
                "years": yearly["churn_year"].tolist(),
                "churn_counts": yearly["churn_count"].tolist(),
                "revenue_lost": [round(float(x), 2) for x in yearly["mrr_lost"].tolist()]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/segmentation")
def get_segmentation(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """Analyze churn rate and customer distribution across demographic segments"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        # Age Group helper
        def get_age_lbl(age):
            if age <= 25: return "18-25"
            elif age <= 35: return "26-35"
            elif age <= 45: return "36-45"
            elif age <= 60: return "46-60"
            else: return "60+"
            
        filtered = filtered.copy()
        filtered["age_group"] = filtered["age"].apply(get_age_lbl)
        
        # Tenure Group helper
        def get_tenure_lbl(m):
            if m <= 6: return "0-6 months"
            elif m <= 12: return "6-12 months"
            elif m <= 24: return "1-2 years"
            elif m <= 36: return "2-3 years"
            else: return "3+ years"
        filtered["tenure_group"] = filtered["tenure_months"].apply(get_tenure_lbl)
        
        results = {}
        
        for segment_col in ["age_group", "gender", "contract_type", "tenure_group", "state"]:
            grouped = filtered.groupby(segment_col).agg(
                total=("customer_id", "count"),
                churned=("churn_status", lambda x: (x == "Churned").sum())
            ).reset_index()
            
            grouped["churn_rate"] = np.round((grouped["churned"] / grouped["total"]) * 100, 2)
            grouped = grouped.sort_values("churn_rate", ascending=False)
            
            results[segment_col] = {
                "categories": grouped[segment_col].tolist(),
                "totals": grouped["total"].tolist(),
                "churned": grouped["churned"].tolist(),
                "churn_rates": grouped["churn_rate"].tolist()
            }
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/behavior")
def get_behavior(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """Analyze behavioral features and correlations vs churn"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        # Support tickets binning
        support_grouped = filtered.groupby("support_tickets").agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        support_grouped["churn_rate"] = np.round((support_grouped["churned"] / support_grouped["total"]) * 100, 2)
        
        # Satisfaction score binning
        sat_grouped = filtered.groupby("satisfaction_score").agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        sat_grouped["churn_rate"] = np.round((sat_grouped["churned"] / sat_grouped["total"]) * 100, 2)
        
        # Login frequency
        login_grouped = filtered.groupby("login_frequency").agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        login_grouped["churn_rate"] = np.round((login_grouped["churned"] / login_grouped["total"]) * 100, 2)
        
        # Product usage binning
        prod_grouped = filtered.groupby("products_used").agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        prod_grouped["churn_rate"] = np.round((prod_grouped["churned"] / prod_grouped["total"]) * 100, 2)
        
        # Session duration bins
        filtered = filtered.copy()
        filtered["session_duration_bucket"] = pd.cut(filtered["avg_session_duration"], bins=[0, 15, 30, 45, 60, 120], labels=["0-15m", "15-30m", "30-45m", "45-60m", "60m+"])
        dur_grouped = filtered.groupby("session_duration_bucket", observed=False).agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        dur_grouped["churn_rate"] = np.round((dur_grouped["churned"] / dur_grouped["total"]) * 100, 2)
        
        # Complaints count bins
        comp_grouped = filtered.groupby("complaints_count").agg(
            total=("customer_id", "count"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        comp_grouped["churn_rate"] = np.round((comp_grouped["churned"] / comp_grouped["total"]) * 100, 2)

        return {
            "support_tickets": {
                "categories": [str(x) for x in support_grouped["support_tickets"].tolist()],
                "churn_rates": support_grouped["churn_rate"].tolist()
            },
            "satisfaction": {
                "categories": [str(x) for x in sat_grouped["satisfaction_score"].tolist()],
                "churn_rates": sat_grouped["churn_rate"].tolist()
            },
            "login_frequency": {
                "categories": login_grouped["login_frequency"].tolist(),
                "churn_rates": login_grouped["churn_rate"].tolist()
            },
            "products_used": {
                "categories": [str(x) for x in prod_grouped["products_used"].tolist()],
                "churn_rates": prod_grouped["churn_rate"].tolist()
            },
            "session_duration": {
                "categories": [str(x) for x in dur_grouped["session_duration_bucket"].tolist()],
                "churn_rates": dur_grouped["churn_rate"].tolist()
            },
            "complaints": {
                "categories": [str(x) for x in comp_grouped["complaints_count"].tolist()],
                "churn_rates": comp_grouped["churn_rate"].tolist()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rfm")
def get_rfm(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """RFM Segmentation Metrics"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        rfm_grouped = filtered.groupby("rfm_segment").agg(
            count=("customer_id", "count"),
            avg_recency=("rfm_recency", "mean"),
            avg_frequency=("rfm_frequency", "mean"),
            avg_monetary=("monthly_charge", "mean"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        
        rfm_grouped["churn_rate"] = np.round((rfm_grouped["churned"] / rfm_grouped["count"]) * 100, 2)
        
        return {
            "segments": rfm_grouped["rfm_segment"].tolist(),
            "counts": rfm_grouped["count"].tolist(),
            "avg_recency": [round(float(x), 1) for x in rfm_grouped["avg_recency"].tolist()],
            "avg_frequency": [round(float(x), 1) for x in rfm_grouped["avg_frequency"].tolist()],
            "avg_monetary": [round(float(x), 2) for x in rfm_grouped["avg_monetary"].tolist()],
            "churn_rates": rfm_grouped["churn_rate"].tolist()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cohorts")
def get_cohorts():
    """Returns monthly signup cohorts and their retention rate matrix for the heatmap"""
    try:
        df = get_df_from_db()
        df = df.copy()
        df["cohort_month"] = pd.to_datetime(df["signup_date"]).dt.to_period("M").astype(str)
        
        # Calculate retention at month milestones: 1, 3, 6, 12
        cohorts = df.groupby("cohort_month").agg(
            size=("customer_id", "count"),
            m1=("tenure_months", lambda x: (x >= 1).sum()),
            m3=("tenure_months", lambda x: (x >= 3).sum()),
            m6=("tenure_months", lambda x: (x >= 6).sum()),
            m12=("tenure_months", lambda x: (x >= 12).sum())
        ).reset_index()
        
        cohorts = cohorts.sort_values("cohort_month")
        
        # Calculate percentages
        cohorts["m1_pct"] = np.round((cohorts["m1"] / cohorts["size"]) * 100, 1)
        cohorts["m3_pct"] = np.round((cohorts["m3"] / cohorts["size"]) * 100, 1)
        cohorts["m6_pct"] = np.round((cohorts["m6"] / cohorts["size"]) * 100, 1)
        cohorts["m12_pct"] = np.round((cohorts["m12"] / cohorts["size"]) * 100, 1)
        
        return {
            "cohort_months": cohorts["cohort_month"].tolist(),
            "sizes": cohorts["size"].tolist(),
            "matrix": [
                cohorts["m1_pct"].tolist(),
                cohorts["m3_pct"].tolist(),
                cohorts["m6_pct"].tolist(),
                cohorts["m12_pct"].tolist()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/revenue-risk")
def get_revenue_risk(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None)
):
    """Page 5: Revenue at risk and High Value Customers list"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        # Segment by Value (Low Value: <$50 charge, Medium: $50-$100, High Value: >$100)
        def get_value_segment(charge):
            if charge < 55: return "Low Value"
            elif charge < 95: return "Medium Value"
            else: return "High Value"
            
        filtered = filtered.copy()
        filtered["value_segment"] = filtered["monthly_charge"].apply(get_value_segment)
        
        val_grouped = filtered.groupby("value_segment").agg(
            count=("customer_id", "count"),
            revenue=("monthly_charge", "sum"),
            churned=("churn_status", lambda x: (x == "Churned").sum())
        ).reset_index()
        val_grouped["revenue"] = np.round(val_grouped["revenue"], 2)
        val_grouped["churn_rate"] = np.round((val_grouped["churned"] / val_grouped["count"]) * 100, 2)
        
        # High value active customers at risk
        active_high_value = filtered[(filtered["churn_status"] == "Active") & (filtered["monthly_charge"] >= 80.0)]
        high_risk_customers = active_high_value.sort_values(by="churn_probability", ascending=False).head(50)
        
        customer_list = []
        for _, row in high_risk_customers.iterrows():
            customer_list.append({
                "customer_id": row["customer_id"],
                "customer_name": row["customer_name"],
                "monthly_charge": float(row["monthly_charge"]),
                "satisfaction_score": int(row["satisfaction_score"]),
                "churn_probability": round(float(row["churn_probability"]), 1),
                "risk_segment": row["risk_segment"]
            })
            
        return {
            "revenue_by_segment": {
                "segments": val_grouped["value_segment"].tolist(),
                "counts": val_grouped["count"].tolist(),
                "revenue": val_grouped["revenue"].tolist(),
                "churn_rates": val_grouped["churn_rate"].tolist()
            },
            "high_value_at_risk": customer_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/forecasting")
def get_forecasting():
    """Endpoint serving saved forecasting trend metrics"""
    try:
        forecast_file = os.path.join(BASE_DIR, "ml", "forecast_results.json")
        if not os.path.exists(forecast_file):
            raise HTTPException(status_code=404, detail="Forecasting results have not been generated yet. Please run ML pipeline.")
        with open(forecast_file, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/model-performance")
def get_model_performance():
    """Model comparison metrics and feature importances"""
    try:
        comparison_file = os.path.join(BASE_DIR, "ml", "model_comparison.json")
        importances_file = os.path.join(BASE_DIR, "ml", "feature_importances.json")
        
        if not os.path.exists(comparison_file) or not os.path.exists(importances_file):
            raise HTTPException(status_code=404, detail="ML performance files missing. Run train.py first.")
            
        with open(comparison_file, "r") as f:
            comparison = json.load(f)
            
        with open(importances_file, "r") as f:
            importances = json.load(f)
            
        return {
            "comparison": comparison,
            "feature_importances": importances
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/customer360/{customer_id}")
def get_customer_360(customer_id: str):
    """Retrieve full detail profile view for a single customer ID"""
    try:
        df = get_df_from_db()
        cust_df = df[df["customer_id"] == customer_id]
        if len(cust_df) == 0:
            # Try searching by exact numeric index match
            cleaned_id = customer_id.upper().strip()
            cust_df = df[df["customer_id"] == cleaned_id]
            if len(cust_df) == 0:
                raise HTTPException(status_code=404, detail=f"Customer ID {customer_id} not found.")
                
        row = cust_df.iloc[0]
        
        # Parse JSON drivers
        try:
            drivers = json.loads(row["churn_drivers"]) if row["churn_drivers"] else []
        except Exception:
            drivers = ["Baseline Account Factors"]
            
        # Retention actions recommendation mapping based on details
        rec_action = "Maintain standard communication."
        if row["churn_status"] == "Churned":
            rec_action = "Customer has churned. Targeted win-back campaign can be offered."
        elif row["risk_segment"] in ["High", "Critical"]:
            if row["contract_type"] == "Monthly":
                rec_action = f"Immediate outreach: Offer annual plan discount. Customer MRR is ${row['monthly_charge']}."
            elif row["satisfaction_score"] <= 2:
                rec_action = "High Priority: Customer Support account manager assignment for satisfaction review."
            else:
                rec_action = "Re-activation promo: Send personalized feature engagement newsletter."
        elif row["rfm_segment"] == "Champions":
            rec_action = "Vanguard VIP: Offer exclusive beta test features and thank-you reward program."
            
        return {
            "customer_id": row["customer_id"],
            "customer_name": row["customer_name"],
            "gender": row["gender"],
            "age": int(row["age"]),
            "city": row["city"],
            "state": row["state"],
            "signup_date": row["signup_date"],
            "contract_type": row["contract_type"],
            "monthly_charge": float(row["monthly_charge"]),
            "total_spent": float(row["total_spent"]),
            "tenure_months": int(row["tenure_months"]),
            "login_frequency": row["login_frequency"],
            "sessions_per_month": int(row["sessions_per_month"]),
            "avg_session_duration": float(row["avg_session_duration"]),
            "support_tickets": int(row["support_tickets"]),
            "products_used": int(row["products_used"]),
            "satisfaction_score": int(row["satisfaction_score"]),
            "complaints_count": int(row["complaints_count"]),
            "last_feedback_date": row["last_feedback_date"],
            "churn_status": row["churn_status"],
            "churn_probability": round(float(row["churn_probability"]), 1),
            "risk_score": int(row["risk_score"]),
            "risk_segment": row["risk_segment"],
            "rfm_segment": row["rfm_segment"],
            "churn_drivers": drivers,
            "recommended_action": rec_action,
            "health_score": int(row["health_score"])
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/whatif")
def calculate_whatif(data: dict):
    """Calculates projected MRR savings and Churn reductions based on simulated parameters"""
    try:
        # Inputs:
        # - contract_shift: float (0-100) % of monthly customers to convert to annual
        # - satisfaction_boost: float (0-100) % reduction in customers with satisfaction <= 2
        # - campaign_success: float (0-100) success rate of targeted retention offers to High Risk users
        
        contract_shift = float(data.get("contract_shift", 0)) / 100.0
        sat_boost = float(data.get("satisfaction_boost", 0)) / 100.0
        camp_success = float(data.get("campaign_success", 0)) / 100.0
        
        df = get_df_from_db()
        active = df[df["churn_status"] == "Active"].copy()
        
        baseline_mrr = active["monthly_charge"].sum()
        
        # Calculate how many would churn in the next cycle based on risk probability
        # Let's model that probability * monthly charge = expected revenue loss
        baseline_expected_loss = (active["churn_probability"] / 100.0 * active["monthly_charge"]).sum()
        
        # What-if alterations:
        # 1. Shifting contract types: monthly contracts are higher risk.
        # Annual contract churn probabilities are about 4.5x lower.
        # We decrease the churn probability of shifted contract users by 70%.
        shifted_loss = 0.0
        for idx, row in active.iterrows():
            prob = row["churn_probability"] / 100.0
            charge = row["monthly_charge"]
            
            # Apply contract shift if they are monthly
            if row["contract_type"] == "Monthly" and np.random.random() < contract_shift:
                prob = prob * 0.30 # 70% decrease
                
            # Apply satisfaction boost
            if row["satisfaction_score"] <= 2 and np.random.random() < sat_boost:
                prob = prob * 0.40 # 60% decrease (satisfaction increases to normal)
                
            # Apply targeted campaigns
            if row["risk_segment"] in ["High", "Critical"] and np.random.random() < camp_success:
                prob = prob * 0.50 # 50% decrease (retention offer accepted)
                
            shifted_loss += prob * charge
            
        mrr_saved = max(0.0, baseline_expected_loss - shifted_loss)
        projected_loss_mrr = baseline_expected_loss - mrr_saved
        
        # New projected churn rate offset
        churned_count = len(df[df["churn_status"] == "Churned"])
        total_count = len(df)
        baseline_churn_rate = (churned_count / total_count) * 100
        
        # Reduce projected future additions to churn
        expected_new_churn_count = (active["churn_probability"] / 100.0).sum()
        shifted_new_churn_count = expected_new_churn_count * (projected_loss_mrr / (baseline_expected_loss + 1e-9))
        
        churn_saved_count = max(0, int(expected_new_churn_count - shifted_new_churn_count))
        new_projected_churn_rate = max(0.0, baseline_churn_rate - (churn_saved_count / total_count * 100))
        
        return {
            "baseline_revenue_loss": round(float(baseline_expected_loss), 2),
            "projected_revenue_loss": round(float(projected_loss_mrr), 2),
            "monthly_recurring_revenue_saved": round(float(mrr_saved), 2),
            "annual_recurring_revenue_saved": round(float(mrr_saved * 12), 2),
            "baseline_churn_rate": round(float(baseline_churn_rate), 2),
            "projected_churn_rate": round(float(new_projected_churn_rate), 2),
            "expected_churned_saved": int(churn_saved_count)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
def export_data(
    region: str = Query(None),
    age_group: str = Query(None),
    contract_type: str = Query(None),
    churn_risk: str = Query(None),
    rfm_segment: str = Query(None),
    format: str = Query("csv")
):
    """Exports currently filtered customer base in CSV format"""
    try:
        df = get_df_from_db()
        filtered = apply_global_filters(df, region, age_group, contract_type, churn_risk, rfm_segment)
        
        # Format columns for business readability
        export_cols = [
            "customer_id", "customer_name", "gender", "age", "state", "signup_date", 
            "contract_type", "monthly_charge", "total_spent", "tenure_months",
            "sessions_per_month", "support_tickets", "satisfaction_score", 
            "complaints_count", "churn_status", "churn_probability", "risk_segment", "rfm_segment"
        ]
        export_df = filtered[export_cols].copy()
        export_df.columns = [
            "Customer ID", "Customer Name", "Gender", "Age", "State", "Signup Date",
            "Contract Type", "Monthly Charge", "Total Spent", "Tenure (Months)",
            "Sessions / Month", "Support Tickets", "Satisfaction Score",
            "Complaints Count", "Churn Status", "Churn Probability (%)", "Risk Segment", "RFM Segment"
        ]
        
        stream = io.StringIO()
        export_df.to_csv(stream, index=False)
        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=customer_churn_export.csv"
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report")
def get_executive_report():
    """Auto-generates text executive report summarize core findings"""
    try:
        df = get_df_from_db()
        active = df[df["churn_status"] == "Active"]
        churned = df[df["churn_status"] == "Churned"]
        
        total = len(df)
        churn_rate = (len(churned) / total) * 100
        
        # Identify key segments
        monthly_churn_rate = (len(churned[churned["contract_type"] == "Monthly"]) / len(df[df["contract_type"] == "Monthly"])) * 100
        annual_churn_rate = (len(churned[churned["contract_type"] == "Annual"]) / len(df[df["contract_type"] == "Annual"])) * 100
        
        high_tickets_churn_rate = (len(churned[churned["support_tickets"] >= 5]) / len(df[df["support_tickets"] >= 5])) * 100
        low_sat_churn_rate = (len(churned[churned["satisfaction_score"] <= 2]) / len(df[df["satisfaction_score"] <= 2])) * 100
        
        total_mrr_at_risk = active[active["risk_segment"].isin(["High", "Critical"])]["monthly_charge"].sum()
        total_mrr_lost = churned["monthly_charge"].sum()
        
        report = {
            "title": "Customer Churn & Retention Intelligence Report",
            "date": datetime.today().strftime("%Y-%m-%d"),
            "summary_metrics": {
                "overall_churn_rate": f"{churn_rate:.2f}%",
                "total_monitored_customers": f"{total:,}",
                "active_monthly_recurring_revenue": f"${active['monthly_charge'].sum():,.2f}",
                "annualized_revenue_lost": f"${total_mrr_lost * 12:,.2f}",
                "arr_at_immediate_risk": f"${total_mrr_at_risk * 12:,.2f}",
                "customer_lifetime_value_clv": f"${df['total_spent'].mean():,.2f}"
            },
            "critical_findings": [
                f"Monthly contract subscribers represent the largest retention threat, exhibiting a churn rate of {monthly_churn_rate:.1f}% compared to just {annual_churn_rate:.1f}% for Annual plans (a 6x difference).",
                f"Customer satisfaction is the strongest leading indicator: customers rating their experience below 3 churn with a {low_sat_churn_rate:.1f}% probability.",
                f"Operational friction drives attrition: customer profiles with 5 or more support tickets churn at a rate of {high_tickets_churn_rate:.1f}%.",
                f"We currently have {len(active[active['risk_segment'].isin(['High', 'Critical'])]):,} active customers classified in High or Critical Risk segments, threatening ${total_mrr_at_risk:,.2f} in MRR."
            ],
            "strategic_recommendations": [
                "Launch a contract migration campaign: incentivize Monthly contract subscribers with a 15% discount to upgrade to Annual plans.",
                "Deploy customer success agents to prioritize outreach for clients with Satisfaction Scores < 3 or who have submitted > 4 support tickets.",
                "Target High Value At Risk customers (MRR > $100, Churn Probability > 70%) with high-priority loyalty benefits.",
                "Introduce automated triggers that alert Account Managers whenever an account's monthly login frequency declines below Weekly."
            ]
        }
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/retrain")
def retrain_model(background_tasks: BackgroundTasks):
    """POST endpoint to trigger background ML pipeline retraining"""
    def run_retrain():
        try:
            import ml.train as train
            train.perform_ml_pipeline()
            get_df_from_db(force_reload=True)
        except Exception as e:
            print(f"Background model retraining failed: {e}")
            
    background_tasks.add_task(run_retrain)
    return {"status": "success", "message": "Model retraining task initiated in background."}

# Mount static files at the root to serve the dashboard frontend SPA (added at the end)
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "frontend"), html=True), name="frontend")
