-- Customer Churn Analysis & Retention Intelligence DDL Schema (PostgreSQL)

-- 1. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    gender VARCHAR(15) NOT NULL,
    age INT CHECK (age >= 18 AND age <= 100),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    signup_date DATE NOT NULL,
    contract_type VARCHAR(20) NOT NULL, -- 'Monthly', 'Quarterly', 'Annual'
    monthly_charge DECIMAL(10, 2) NOT NULL CHECK (monthly_charge >= 0),
    total_spent DECIMAL(10, 2) NOT NULL CHECK (total_spent >= 0),
    tenure_months INT NOT NULL CHECK (tenure_months >= 0)
);

-- 2. Customer Usage Table
CREATE TABLE IF NOT EXISTS customer_usage (
    usage_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    login_frequency VARCHAR(20) NOT NULL, -- 'Daily', 'Weekly', 'Monthly'
    sessions_per_month INT NOT NULL CHECK (sessions_per_month >= 0),
    avg_session_duration DECIMAL(10, 2) NOT NULL CHECK (avg_session_duration >= 0), -- in minutes
    support_tickets INT NOT NULL CHECK (support_tickets >= 0),
    products_used INT NOT NULL CHECK (products_used >= 0)
);

-- 3. Customer Feedback Table
CREATE TABLE IF NOT EXISTS customer_feedback (
    feedback_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    satisfaction_score INT NOT NULL CHECK (satisfaction_score >= 1 AND satisfaction_score <= 5),
    complaints_count INT NOT NULL CHECK (complaints_count >= 0),
    last_feedback_date DATE NOT NULL
);

-- 4. Churn Table
CREATE TABLE IF NOT EXISTS churn (
    churn_id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    churn_status VARCHAR(20) NOT NULL, -- 'Active', 'Churned'
    churn_date DATE, -- NULL if Active, random date post-signup if Churned
    churn_probability DECIMAL(5, 2) NOT NULL CHECK (churn_probability >= 0.00 AND churn_probability <= 100.00), -- ML Prediction
    risk_score INT NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100), -- Composite Score
    risk_segment VARCHAR(20) NOT NULL, -- 'Low', 'Medium', 'High', 'Critical'
    rfm_recency INT NOT NULL CHECK (rfm_recency >= 0), -- Days since last interaction
    rfm_frequency INT NOT NULL CHECK (rfm_frequency >= 1 AND rfm_frequency <= 5), -- RFM Frequency score (1-5)
    rfm_monetary DECIMAL(10, 2) NOT NULL CHECK (rfm_monetary >= 0), -- RFM Monetary Value
    rfm_segment VARCHAR(50) NOT NULL, -- 'Champions', 'Loyal Customers', 'Potential Loyalists', 'At Risk', 'Lost'
    churn_drivers TEXT -- JSON list of top local churn factors for Customer 360 lookup
);

-- Create Indexes for Query Performance Optimization (Enterprise best practices)
CREATE INDEX IF NOT EXISTS idx_customers_signup ON customers(signup_date);
CREATE INDEX IF NOT EXISTS idx_customers_contract ON customers(contract_type);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state);
CREATE INDEX IF NOT EXISTS idx_usage_customer ON customer_usage(customer_id);
CREATE INDEX IF NOT EXISTS idx_feedback_customer ON customer_feedback(customer_id);
CREATE INDEX IF NOT EXISTS idx_churn_customer ON churn(customer_id);
CREATE INDEX IF NOT EXISTS idx_churn_status ON churn(churn_status);
CREATE INDEX IF NOT EXISTS idx_churn_segment ON churn(risk_segment);
CREATE INDEX IF NOT EXISTS idx_churn_rfm ON churn(rfm_segment);
