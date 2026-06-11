-- Customer Churn & Retention Advanced SQL Analytics Scripts
-- Designed for PostgreSQL / SQLite (compatible with standard ANSI SQL)

-- 1. Overall Churn Rate & Customer Status Summary
-- Calculates active counts, churned counts, and total churn percentages
SELECT 
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_status = 'Active' THEN 1 ELSE 0 END) AS active_customers,
    SUM(CASE WHEN churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(SUM(CASE WHEN churn_status = 'Churned' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS churn_rate_pct,
    ROUND(SUM(CASE WHEN churn_status = 'Active' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS retention_rate_pct
FROM churn;


-- 2. Monthly Churn Time-Series Trend
-- Tracks customer attrition counts and Monthly Recurring Revenue (MRR) lost month-over-month
WITH monthly_losses AS (
    SELECT 
        strftime('%Y-%m', ch.churn_date) AS churn_month, -- SQLite format; in Postgres use TO_CHAR(ch.churn_date, 'YYYY-MM')
        COUNT(ch.customer_id) AS churned_customers,
        SUM(c.monthly_charge) AS monthly_revenue_lost
    FROM churn ch
    JOIN customers c ON ch.customer_id = c.customer_id
    WHERE ch.churn_status = 'Churned' AND ch.churn_date IS NOT NULL
    GROUP BY 1
)
SELECT 
    churn_month,
    churned_customers,
    ROUND(monthly_revenue_lost, 2) AS monthly_revenue_lost,
    SUM(churned_customers) OVER (ORDER BY churn_month) AS cumulative_churned_customers,
    ROUND(SUM(monthly_revenue_lost) OVER (ORDER BY churn_month), 2) AS cumulative_revenue_lost
FROM monthly_losses
ORDER BY churn_month ASC;


-- 3. Churn Rate & Rankings by Region (State)
-- Uses window functions (DENSE_RANK) to identify the highest risk regions
WITH regional_stats AS (
    SELECT 
        c.state,
        COUNT(c.customer_id) AS total_customers,
        SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
        SUM(c.monthly_charge) AS monthly_revenue_potential
    FROM customers c
    JOIN churn ch ON c.customer_id = ch.customer_id
    GROUP BY c.state
)
SELECT 
    state,
    total_customers,
    churned_customers,
    ROUND((churned_customers * 100.0 / total_customers), 2) AS churn_rate_pct,
    DENSE_RANK() OVER (ORDER BY (churned_customers * 100.0 / total_customers) DESC) AS rank_by_churn_rate
FROM regional_stats
ORDER BY rank_by_churn_rate ASC;


-- 4. Churn Risk & Revenue Impact by Contract Type
-- Compares monthly, quarterly, and annual contract performance
SELECT 
    c.contract_type,
    COUNT(c.customer_id) AS total_customers,
    SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS churn_rate_pct,
    ROUND(SUM(c.monthly_charge), 2) AS total_mrr_pool,
    ROUND(SUM(CASE WHEN ch.churn_status = 'Churned' THEN c.monthly_charge ELSE 0 END), 2) AS mrr_lost
FROM customers c
JOIN churn ch ON c.customer_id = ch.customer_id
GROUP BY c.contract_type
ORDER BY churn_rate_pct DESC;


-- 5. Customer Churn Segmentation by Age Group
-- Demographics categorization with CASE statements
WITH age_groups AS (
    SELECT 
        c.customer_id,
        ch.churn_status,
        CASE 
            WHEN c.age >= 18 AND c.age <= 25 THEN '18-25'
            WHEN c.age >= 26 AND c.age <= 35 THEN '26-35'
            WHEN c.age >= 36 AND c.age <= 45 THEN '36-45'
            WHEN c.age >= 46 AND c.age <= 60 THEN '46-60'
            ELSE '60+' 
        END AS age_cohort
    FROM customers c
    JOIN churn ch ON c.customer_id = ch.customer_id
)
SELECT 
    age_cohort,
    COUNT(*) AS total_customers,
    SUM(CASE WHEN churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(SUM(CASE WHEN churn_status = 'Churned' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS churn_rate_pct
FROM age_groups
GROUP BY age_cohort
ORDER BY age_cohort ASC;


-- 6. Behavioral Analysis: Satisfaction Score vs Churn Attrition
-- Correlates satisfaction score metrics with customer turnover
SELECT 
    f.satisfaction_score,
    COUNT(c.customer_id) AS total_customers,
    SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1.0 ELSE 0.0 END) / COUNT(*) * 100, 2) AS churn_rate_pct
FROM customer_feedback f
JOIN customers c ON f.customer_id = c.customer_id
JOIN churn ch ON f.customer_id = ch.customer_id
GROUP BY f.satisfaction_score
ORDER BY f.satisfaction_score ASC;


-- 7. Corporate Revenue Health Metrics
-- Focuses on MRR, ARR, CLV, Churn Cost and Net Revenue Retention (NRR)
-- Calculates values before and after churn events
WITH revenue_summary AS (
    SELECT 
        SUM(c.monthly_charge) AS original_mrr,
        SUM(CASE WHEN ch.churn_status = 'Active' THEN c.monthly_charge ELSE 0 END) AS current_active_mrr,
        SUM(CASE WHEN ch.churn_status = 'Churned' THEN c.monthly_charge ELSE 0 END) AS lost_mrr,
        AVG(c.total_spent) AS average_clv,
        COUNT(c.customer_id) AS total_customers,
        SUM(CASE WHEN ch.churn_status = 'Churned' THEN 1 ELSE 0 END) AS churned_customers
    FROM customers c
    JOIN churn ch ON c.customer_id = ch.customer_id
)
SELECT 
    ROUND(original_mrr, 2) AS monthly_recurring_revenue_mrr,
    ROUND(original_mrr * 12, 2) AS annual_recurring_revenue_arr,
    ROUND(lost_mrr, 2) AS mrr_lost_to_churn,
    ROUND(lost_mrr * 12, 2) AS arr_lost_to_churn,
    ROUND(current_active_mrr, 2) AS active_mrr_pool,
    ROUND(average_clv, 2) AS avg_customer_lifetime_value_clv,
    -- NRR = (Active MRR / Original MRR) * 100 (assuming no expansion for simplicity)
    ROUND((current_active_mrr * 100.0 / original_mrr), 2) AS net_revenue_retention_nrr_pct,
    -- Estimated Churn Cost = lost MRR + Customer Acquisition cost (assumed standard CAC of $150 per churned customer)
    ROUND(lost_mrr + (churned_customers * 150.0), 2) AS total_churn_financial_cost
FROM revenue_summary;


-- 8. Advanced Retention Cohort Analysis Matrix
-- Tracks cohort survival rates month-by-month based on customer signup date
WITH cohort_sizes AS (
    -- Groups customers into monthly cohorts based on signup dates
    SELECT 
        strftime('%Y-%m', signup_date) AS cohort_month, -- SQLite format
        COUNT(customer_id) AS cohort_size
    FROM customers
    GROUP BY 1
),
customer_survival AS (
    -- Calculates active/churned milestones for each customer
    SELECT 
        c.customer_id,
        strftime('%Y-%m', c.signup_date) AS cohort_month,
        c.tenure_months,
        ch.churn_status
    FROM customers c
    JOIN churn ch ON c.customer_id = ch.customer_id
)
SELECT 
    cs.cohort_month,
    sz.cohort_size,
    -- Retention rate calculations at month 1, 3, 6, 12 milestones
    ROUND(SUM(CASE WHEN cs.tenure_months >= 1 THEN 1.0 ELSE 0.0 END) / sz.cohort_size * 100, 2) AS month_1_retention_pct,
    ROUND(SUM(CASE WHEN cs.tenure_months >= 3 THEN 1.0 ELSE 0.0 END) / sz.cohort_size * 100, 2) AS month_3_retention_pct,
    ROUND(SUM(CASE WHEN cs.tenure_months >= 6 THEN 1.0 ELSE 0.0 END) / sz.cohort_size * 100, 2) AS month_6_retention_pct,
    ROUND(SUM(CASE WHEN cs.tenure_months >= 12 THEN 1.0 ELSE 0.0 END) / sz.cohort_size * 100, 2) AS month_12_retention_pct
FROM customer_survival cs
JOIN cohort_sizes sz ON cs.cohort_month = sz.cohort_month
GROUP BY cs.cohort_month
ORDER BY cs.cohort_month ASC;


-- 9. Top High-Risk Customer Profiles (CTEs and Multi-Joins)
-- Identifies premium monthly subscribers with low satisfaction and active support tickets
WITH critical_risk_list AS (
    SELECT 
        c.customer_id,
        c.customer_name,
        c.contract_type,
        c.monthly_charge,
        f.satisfaction_score,
        f.complaints_count,
        u.support_tickets,
        ch.churn_status
    FROM customers c
    JOIN customer_usage u ON c.customer_id = u.customer_id
    JOIN customer_feedback f ON c.customer_id = f.customer_id
    JOIN churn ch ON c.customer_id = ch.customer_id
    WHERE ch.churn_status = 'Active'
      AND c.contract_type = 'Monthly'
      AND f.satisfaction_score <= 2
      AND (f.complaints_count > 1 OR u.support_tickets > 4)
)
SELECT 
    customer_id,
    customer_name,
    monthly_charge,
    satisfaction_score,
    complaints_count,
    support_tickets,
    ROUND(monthly_charge * 12, 2) AS projected_revenue_at_risk_arr
FROM critical_risk_list
ORDER BY monthly_charge DESC
LIMIT 100;
