# Customer Churn Analytics Platform - Data Generator
# Generates 50,000 customers with realistic correlation patterns

import sqlite3
import random
import datetime
import math
import os
import json

# Set seed for reproducibility
random.seed(42)

DB_PATH = os.path.join(os.path.dirname(__file__), "churn_analytics.db")

STATES_CITIES = {
    "California": ["Los Angeles", "San Francisco", "San Diego", "San Jose", "Sacramento"],
    "New York": ["New York City", "Buffalo", "Rochester", "Yonkers", "Syracuse"],
    "Texas": ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth"],
    "Florida": ["Miami", "Tampa", "Orlando", "Jacksonville", "Tallahassee"],
    "Washington": ["Seattle", "Spokane", "Tacoma", "Bellevue", "Olympia"],
    "Illinois": ["Chicago", "Aurora", "Rockford", "Joliet", "Naperville"],
    "Massachusetts": ["Boston", "Worcester", "Springfield", "Cambridge", "Lowell"],
    "Colorado": ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Boulder"],
    "Georgia": ["Atlanta", "Augusta", "Columbus", "Macon", "Savannah"],
    "Pennsylvania": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading"]
}

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
               "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
               "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
               "Donald", "Ashley", "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna"]

LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

CONTRACTS = ["Monthly", "Quarterly", "Annual"]
LOGIN_FREQS = ["Daily", "Weekly", "Monthly"]

# Define baseline date for the analysis (June 12, 2026)
BASE_DATE = datetime.date(2026, 6, 12)

def generate_customer_id(index):
    return f"CUST{index:05d}"

def random_date(start_date, end_date):
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    return start_date + datetime.timedelta(days=random_days)

def create_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # SQLite tables
    cursor.execute("""
    CREATE TABLE customers (
        customer_id TEXT PRIMARY KEY,
        customer_name TEXT,
        gender TEXT,
        age INTEGER,
        city TEXT,
        state TEXT,
        country TEXT,
        signup_date TEXT,
        contract_type TEXT,
        monthly_charge REAL,
        total_spent REAL,
        tenure_months INTEGER
    )
    """)
    
    cursor.execute("""
    CREATE TABLE customer_usage (
        usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT,
        login_frequency TEXT,
        sessions_per_month INTEGER,
        avg_session_duration REAL,
        support_tickets INTEGER,
        products_used INTEGER,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE customer_feedback (
        feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT,
        satisfaction_score INTEGER,
        complaints_count INTEGER,
        last_feedback_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE churn (
        churn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT,
        churn_status TEXT,
        churn_date TEXT,
        churn_probability REAL DEFAULT 0.0,
        risk_score INTEGER DEFAULT 0,
        risk_segment TEXT DEFAULT 'Low',
        rfm_recency INTEGER,
        rfm_frequency INTEGER,
        rfm_monetary REAL,
        rfm_segment TEXT,
        churn_drivers TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )
    """)
    
    conn.commit()
    return conn

def run():
    print("Initializing Database...")
    conn = create_database()
    cursor = conn.cursor()
    
    print("Generating 50,000 customer records...")
    
    customers_batch = []
    usage_batch = []
    feedback_batch = []
    churn_batch = []
    
    start_signup = datetime.date(2022, 1, 1)
    end_signup = datetime.date(2026, 3, 1) # Signup ends slightly before BASE_DATE so they have at least some tenure
    
    for i in range(1, 50001):
        cust_id = generate_customer_id(i)
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        gender = random.choice(["Male", "Female", "Non-binary"])
        age = random.randint(18, 85)
        
        state = random.choice(list(STATES_CITIES.keys()))
        city = random.choice(STATES_CITIES[state])
        country = "United States"
        
        signup_dt = random_date(start_signup, end_signup)
        contract = random.choices(CONTRACTS, weights=[0.5, 0.25, 0.25])[0]
        
        # Charges depend slightly on contract type
        if contract == "Monthly":
            monthly_charge = round(random.uniform(49.0, 149.0), 2)
        elif contract == "Quarterly":
            monthly_charge = round(random.uniform(39.0, 119.0), 2)
        else:
            monthly_charge = round(random.uniform(29.0, 99.0), 2)
            
        # Compute maximum potential tenure (in months) from signup to base analysis date
        max_tenure_days = (BASE_DATE - signup_dt).days
        max_tenure_months = max(1, int(max_tenure_days / 30.44))
        
        # Engagement & Usage Factors (correlated with churn)
        # Low usage, low satisfaction, high complaints -> more churn
        satisfaction = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.15, 0.25, 0.35, 0.15])[0]
        
        # Increase complaints if satisfaction is low
        if satisfaction <= 2:
            complaints = random.choices([0, 1, 2, 3, 4, 5], weights=[0.1, 0.15, 0.2, 0.25, 0.2, 0.1])[0]
            support_tickets = random.randint(3, 12)
        else:
            complaints = random.choices([0, 1, 2], weights=[0.7, 0.25, 0.05])[0]
            support_tickets = random.randint(0, 4)
            
        # Engagement variables
        login_frequency = random.choice(LOGIN_FREQS)
        if login_frequency == "Daily":
            sessions = random.randint(20, 80)
            avg_duration = round(random.uniform(15.0, 90.0), 2)
        elif login_frequency == "Weekly":
            sessions = random.randint(5, 25)
            avg_duration = round(random.uniform(10.0, 60.0), 2)
        else:
            sessions = random.randint(1, 8)
            avg_duration = round(random.uniform(5.0, 30.0), 2)
            
        products_used = random.randint(1, 5)
        
        # Churn Probability simulation model (to build realistic relationships)
        # Start with a base probability
        p_churn = 0.05
        
        # Factors that INCREASE churn risk:
        if contract == "Monthly":
            p_churn += 0.25
        elif contract == "Quarterly":
            p_churn += 0.10
            
        if satisfaction == 1:
            p_churn += 0.35
        elif satisfaction == 2:
            p_churn += 0.20
            
        if complaints > 2:
            p_churn += 0.25
        elif complaints > 0:
            p_churn += 0.10
            
        if support_tickets > 6:
            p_churn += 0.20
        elif support_tickets > 3:
            p_churn += 0.05
            
        if sessions < 8:
            p_churn += 0.20
        elif sessions < 18:
            p_churn += 0.10
            
        # Age-based risk: younger and senior have slightly higher rates
        if age < 25 or age > 65:
            p_churn += 0.05
            
        # Tenure-based risk: shorter tenure -> more churn
        if max_tenure_months < 6:
            p_churn += 0.15
        elif max_tenure_months < 12:
            p_churn += 0.05
            
        # Cap probability between 0 and 0.95 (some random survival rate)
        p_churn = min(0.95, max(0.01, p_churn))
        
        # Decide if they churned
        is_churned = random.random() < p_churn
        
        if is_churned:
            churn_status = "Churned"
            # Churn date is some random months after signup
            actual_tenure = random.randint(1, max_tenure_months)
            churn_days = int(actual_tenure * 30.44)
            churn_dt = signup_dt + datetime.timedelta(days=churn_days)
            if churn_dt >= BASE_DATE:
                # Fallback to make sure they churn before analysis date
                churn_dt = BASE_DATE - datetime.timedelta(days=random.randint(1, 15))
                actual_tenure = max(1, int((churn_dt - signup_dt).days / 30.44))
            
            tenure_months = actual_tenure
            churn_date_str = churn_dt.strftime("%Y-%m-%d")
            # Last feedback must be before or on churn date
            last_fb_dt = random_date(signup_dt, churn_dt)
        else:
            churn_status = "Active"
            tenure_months = max_tenure_months
            churn_date_str = None
            last_fb_dt = random_date(signup_dt, BASE_DATE)
            
        total_spent = round(monthly_charge * tenure_months, 2)
        
        # Recency calculation: days since last feedback to base date (or to churn date if churned)
        ref_date = datetime.datetime.strptime(churn_date_str, "%Y-%m-%d").date() if churn_date_str else BASE_DATE
        rfm_recency = (ref_date - last_fb_dt).days
        
        # Append to batches
        customers_batch.append((cust_id, name, gender, age, city, state, country, signup_dt.strftime("%Y-%m-%d"), contract, monthly_charge, total_spent, tenure_months))
        usage_batch.append((cust_id, login_frequency, sessions, avg_duration, support_tickets, products_used))
        feedback_batch.append((cust_id, satisfaction, complaints, last_fb_dt.strftime("%Y-%m-%d")))
        
        # RFM Score calculations (temporary scores for initial database seed)
        # Recency score (1-5): lower days is better (1: >180, 2: 90-180, 3: 30-90, 4: 10-30, 5: 0-10)
        if rfm_recency <= 10: r_score = 5
        elif rfm_recency <= 30: r_score = 4
        elif rfm_recency <= 90: r_score = 3
        elif rfm_recency <= 180: r_score = 2
        else: r_score = 1
        
        # Frequency score (1-5): sessions_per_month (1: <5, 2: 5-12, 3: 12-25, 4: 25-50, 5: >50)
        if sessions > 50: f_score = 5
        elif sessions > 25: f_score = 4
        elif sessions > 12: f_score = 3
        elif sessions > 5: f_score = 2
        else: f_score = 1
        
        # Monetary score (1-5): total_spent quintiles approximate (1: <150, 2: 150-400, 3: 400-900, 4: 900-2000, 5: >2000)
        if total_spent > 2000: m_score = 5
        elif total_spent > 900: m_score = 4
        elif total_spent > 400: m_score = 3
        elif total_spent > 150: m_score = 2
        else: m_score = 1
        
        # Segmentation based on R, F, M averages
        avg_rf = (r_score + f_score) / 2
        if r_score >= 4 and f_score >= 4 and m_score >= 4:
            rfm_segment = "Champions"
        elif r_score >= 3 and f_score >= 3 and m_score >= 3:
            rfm_segment = "Loyal Customers"
        elif r_score >= 3 and f_score >= 1 and m_score >= 1:
            rfm_segment = "Potential Loyalists"
        elif r_score <= 2 and f_score >= 3 and m_score >= 3:
            rfm_segment = "At Risk"
        else:
            rfm_segment = "Lost Customers"
            
        churn_batch.append((cust_id, churn_status, churn_date_str, 0.0, 0, 'Low', rfm_recency, f_score, total_spent, rfm_segment, None))
        
        # Bulk insert every 10,000 to save memory
        if i % 10000 == 0:
            print(f"Generated {i} records...")

    print("Inserting data into database tables...")
    cursor.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", customers_batch)
    cursor.executemany("INSERT INTO customer_usage (customer_id, login_frequency, sessions_per_month, avg_session_duration, support_tickets, products_used) VALUES (?, ?, ?, ?, ?, ?)", usage_batch)
    cursor.executemany("INSERT INTO customer_feedback (customer_id, satisfaction_score, complaints_count, last_feedback_date) VALUES (?, ?, ?, ?)", feedback_batch)
    cursor.executemany("INSERT INTO churn (customer_id, churn_status, churn_date, churn_probability, risk_score, risk_segment, rfm_recency, rfm_frequency, rfm_monetary, rfm_segment, churn_drivers) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", churn_batch)
    
    conn.commit()
    
    # Run a quick check
    cursor.execute("SELECT COUNT(*) FROM customers")
    cust_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM churn WHERE churn_status='Churned'")
    churned_count = cursor.fetchone()[0]
    
    print(f"Database generation complete! Total Customers: {cust_count}, Churned: {churned_count} ({churned_count/cust_count*100:.2f}%)")
    conn.close()

if __name__ == "__main__":
    run()
