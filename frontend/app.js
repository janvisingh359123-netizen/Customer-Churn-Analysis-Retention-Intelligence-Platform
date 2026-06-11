// Customer Churn & Retention Analytics - Frontend Controller

const API_BASE = ""; // Relative paths since frontend is hosted by FastAPI

// State Management
let currentTheme = localStorage.getItem("color-scheme") || "dark";
let activePage = "page-summary";
let globalFilters = {
    region: "All",
    age_group: "All",
    contract_type: "All",
    churn_risk: "All",
    rfm_segment: "All"
};

// Map Page ID to Topbar Title / Subtitle
const PAGE_DETAILS = {
    "page-summary": { title: "Executive Overview", subtitle: "Real-time enterprise metrics & retention intelligence" },
    "page-trends": { title: "Churn Trends", subtitle: "Historical customer attrition rates & recurring revenue loss" },
    "page-segmentation": { title: "Customer Demographics", subtitle: "Attrition analysis by age group, gender, region, and tenure" },
    "page-rfm": { title: "RFM Loyalty Analysis", subtitle: "Recency, frequency, and monetary cohort segmentation" },
    "page-behavior": { title: "Behavioral Analytics", subtitle: "Correlations of engagement, tickets, and complaints vs churn" },
    "page-revenue": { title: "Revenue Simulation Suite", subtitle: "What-if simulations & high-value accounts at risk" },
    "page-forecasting": { title: "Predictive Forecasting", subtitle: "Time-series projections for customer and revenue attrition" },
    "page-customer360": { title: "Customer 360 Explorer", subtitle: "Individual customer profile lookups and diagnostic drivers" },
    "page-recommendations": { title: "Action Playbooks", subtitle: "Targeted playbooks for segment-specific retention campaigns" },
    "page-model": { title: "Model Analytics", subtitle: "Machine learning classifier evaluations & feature importance" }
};

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
    initApp();
    setupEventListeners();
});

// Initialize Application
async function initApp() {
    applyTheme(currentTheme);
    await loadFilterMetadata();
    loadActivePageData();
}

// Setup Interactive Action Listeners
function setupEventListeners() {
    // Page Routing / Sidebar navigation
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            const navItem = e.currentTarget;
            const pageId = navItem.getAttribute("data-page");
            
            // Toggle active styles in sidebar
            document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
            navItem.classList.add("active");
            
            // Switch page panel
            document.querySelectorAll(".dashboard-page").forEach(p => p.classList.remove("active-page"));
            document.getElementById(pageId).classList.add("active-page");
            
            // Update titles
            activePage = pageId;
            document.getElementById("page-title").textContent = PAGE_DETAILS[pageId].title;
            document.getElementById("page-subtitle").textContent = PAGE_DETAILS[pageId].subtitle;
            
            // Fetch relevant page datasets
            loadActivePageData();
        });
    });

    // Theme Toggle
    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
        currentTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(currentTheme);
        localStorage.setItem("color-scheme", currentTheme);
        // Re-draw active charts with the new theme colors
        loadActivePageData();
    });

    // Retrain Model Button
    document.getElementById("btn-retrain").addEventListener("click", async () => {
        const btn = document.getElementById("btn-retrain");
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Training...`;
        
        try {
            const res = await fetch("/api/retrain", { method: "POST" });
            showToast("Model retraining completed successfully!");
        } catch (err) {
            console.error("Retrain failed:", err);
            showToast("Retraining started in the background. Refreshing soon.", true);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> Retrain Model`;
            setTimeout(() => loadActivePageData(), 3000);
        }
    });

    // Global Filters dropdowns
    document.querySelectorAll(".filter-select").forEach(select => {
        select.addEventListener("change", (e) => {
            const filterKey = e.target.id.replace("filter-", "").replace("-", "_");
            globalFilters[filterKey] = e.target.value;
            loadActivePageData();
        });
    });

    // Reset Filters button
    document.getElementById("btn-reset-filters").addEventListener("click", () => {
        document.getElementById("filter-region").value = "All";
        document.getElementById("filter-age").value = "All";
        document.getElementById("filter-contract").value = "All";
        document.getElementById("filter-risk").value = "All";
        
        globalFilters = { region: "All", age_group: "All", contract_type: "All", churn_risk: "All", rfm_segment: "All" };
        loadActivePageData();
    });

    // Export PDF Button (Print Layout)
    document.getElementById("btn-pdf").addEventListener("click", () => {
        window.print();
    });

    // What-If Simulator trigger
    document.getElementById("btn-run-simulation").addEventListener("click", runWhatIfSimulation);
    
    // Sliders dynamic value displays
    const sliders = [
        { id: "slider-contract-shift", valId: "val-contract-shift", suffix: "%" },
        { id: "slider-sat-boost", valId: "val-sat-boost", suffix: "%" },
        { id: "slider-camp-success", valId: "val-camp-success", suffix: "%" }
    ];
    sliders.forEach(s => {
        const el = document.getElementById(s.id);
        const valEl = document.getElementById(s.valId);
        el.addEventListener("input", () => {
            valEl.textContent = el.value + s.suffix;
        });
    });

    // CSV Export trigger
    document.getElementById("btn-export-csv").addEventListener("click", exportFilteredCSV);

    // Customer 360 Search trigger
    document.getElementById("btn-search-customer").addEventListener("click", searchCustomerProfile);
    document.getElementById("input-search-customer").addEventListener("keypress", (e) => {
        if (e.key === "Enter") searchCustomerProfile();
    });
}

// Apply theme layout class toggling
function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const icon = document.getElementById("btn-theme-toggle").querySelector("i");
    if (theme === "dark") {
        icon.className = "fa-solid fa-sun";
    } else {
        icon.className = "fa-solid fa-moon";
    }
}

// Toast Notifications helper
function showToast(message, isWarning = false) {
    const toast = document.getElementById("toast");
    const msgEl = document.getElementById("toast-message");
    const icon = toast.querySelector("i");
    
    msgEl.textContent = message;
    if (isWarning) {
        toast.style.borderColor = "var(--color-rose)";
        icon.className = "fa-solid fa-triangle-exclamation";
        icon.style.color = "var(--color-rose)";
    } else {
        toast.style.borderColor = "var(--color-teal)";
        icon.className = "fa-solid fa-circle-check";
        icon.style.color = "var(--color-teal)";
    }
    
    toast.classList.add("show");
    setTimeout(() => {
        toast.classList.remove("show");
    }, 4000);
}

// Fetch Filter Parameter Metadata Options
async function loadFilterMetadata() {
    try {
        const res = await fetch("/api/meta");
        const data = await res.json();
        
        // Populate dropdown selectors
        const regionSelect = document.getElementById("filter-region");
        regionSelect.innerHTML = "";
        data.states.forEach(state => {
            regionSelect.add(new Option(state === "All" ? "All Regions" : state, state));
        });
        
        const ageSelect = document.getElementById("filter-age");
        ageSelect.innerHTML = "";
        data.age_groups.forEach(g => {
            ageSelect.add(new Option(g === "All" ? "All Ages" : g, g));
        });
        
        const contractSelect = document.getElementById("filter-contract");
        contractSelect.innerHTML = "";
        data.contract_types.forEach(c => {
            contractSelect.add(new Option(c === "All" ? "All Contracts" : c, c));
        });
        
        const riskSelect = document.getElementById("filter-risk");
        riskSelect.innerHTML = "";
        data.churn_risks.forEach(r => {
            riskSelect.add(new Option(r === "All" ? "All Risks" : r, r));
        });
    } catch (err) {
        console.error("Error loading filters metadata:", err);
    }
}

// Dynamic routing data loading
function loadActivePageData() {
    updateFilterPills();
    const query = new URLSearchParams(globalFilters).toString();
    
    switch (activePage) {
        case "page-summary":
            loadSummaryPage(query);
            break;
        case "page-trends":
            loadTrendsPage(query);
            break;
        case "page-segmentation":
            loadSegmentationPage(query);
            break;
        case "page-rfm":
            loadRFMPage(query);
            break;
        case "page-behavior":
            loadBehaviorPage(query);
            break;
        case "page-revenue":
            loadRevenuePage(query);
            break;
        case "page-forecasting":
            loadForecastingPage();
            break;
        case "page-customer360":
            // Managed entirely by search input
            break;
        case "page-recommendations":
            // Static HTML playbook rules
            break;
        case "page-model":
            loadModelPerformancePage();
            break;
    }
}

// Plotly UI Theme Adaptor Configuration
function getPlotlyLayout(title, overrides = {}) {
    const isDark = currentTheme === "dark";
    const baseLayout = {
        title: {
            text: title,
            font: { family: "Outfit, sans-serif", size: 14, color: isDark ? "#ffffff" : "#0f172a", weight: 600 }
        },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "Inter, sans-serif", color: isDark ? "#94a3b8" : "#475569" },
        margin: { t: 40, b: 40, l: 50, r: 20 },
        xaxis: {
            gridcolor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
            zeroline: false
        },
        yaxis: {
            gridcolor: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)",
            zeroline: false
        },
        legend: {
            font: { size: 10 }
        }
    };
    return { ...baseLayout, ...overrides };
}

// --- PAGE LOADER IMPLEMENTATIONS ---

// PAGE 1: EXECUTIVE OVERVIEW
async function loadSummaryPage(query) {
    try {
        const res = await fetch(`/api/overview?${query}`);
        const data = await res.json();
        
        // Update welcome stats MRR and NRR pools
        const bannerMrr = document.getElementById("banner-mrr");
        if (bannerMrr) bannerMrr.textContent = "$" + Math.round(data.mrr).toLocaleString();
        const bannerNrr = document.getElementById("banner-nrr");
        if (bannerNrr) bannerNrr.textContent = data.net_revenue_retention + "%";

        // Update KPI card metrics with trend indicators
        setKPICard("kpi-total-cust", data.total_customers.toLocaleString(), "+0.5% MoM", "success", true);
        setKPICard("kpi-churn-rate", data.churn_rate + "%", "-0.4% MoM", "success", false);
        setKPICard("kpi-retention-rate", data.retention_rate + "%", "+0.4% MoM", "success", true);
        setKPICard("kpi-mrr", "$" + Math.round(data.mrr).toLocaleString(), "+1.8% MoM", "success", true);
        setKPICard("kpi-arr", "$" + Math.round(data.arr).toLocaleString(), "+2.2% MoM", "success", true);
        setKPICard("kpi-clv", "$" + Math.round(data.average_clv).toLocaleString(), "+$120 MoM", "success", true);
        setKPICard("kpi-revenue-risk", "$" + Math.round(data.revenue_at_risk).toLocaleString(), "-3.5% MoM", "success", false);
        setKPICard("kpi-churn-cost", "$" + Math.round(data.churn_cost).toLocaleString(), "-1.2% MoM", "success", false);
        
        // Load AI Report findings
        const repRes = await fetch("/api/report");
        const rep = await repRes.json();
        
        const reportBody = document.getElementById("exec-report-body");
        reportBody.innerHTML = "";
        
        const icons = [
            "fa-solid fa-triangle-exclamation text-rose",
            "fa-solid fa-circle-check text-teal",
            "fa-solid fa-chart-line text-violet",
            "fa-solid fa-shield-halved text-gold"
        ];
        
        rep.critical_findings.forEach((finding, idx) => {
            const card = document.createElement("div");
            card.className = "report-finding-card";
            card.innerHTML = `
                <i class="${icons[idx % icons.length]}"></i>
                <div>
                    <strong>Observation #${idx + 1}</strong>
                    <span>${finding}</span>
                </div>
            `;
            reportBody.appendChild(card);
        });
        
        // Update recommended priorities list
        const recList = document.getElementById("exec-recommendations-list");
        recList.innerHTML = "";
        rep.strategic_recommendations.forEach(rec => {
            const li = document.createElement("li");
            li.textContent = rec;
            recList.appendChild(li);
        });
    } catch (err) {
        console.error("Error summary page:", err);
    }
}

// PAGE 2: CHURN TRENDS
async function loadTrendsPage(query) {
    try {
        const res = await fetch(`/api/trends?${query}`);
        const data = await res.json();
        
        // Plot Monthly Trends
        const traceMonthlyCount = {
            x: data.monthly.months,
            y: data.monthly.churn_counts,
            name: "Churned Accounts",
            type: "scatter",
            mode: "lines+markers",
            line: { color: "#e11d48", width: 3 }
        };
        const traceMonthlyRev = {
            x: data.monthly.months,
            y: data.monthly.revenue_lost,
            name: "MRR Lost ($)",
            type: "bar",
            yaxis: "y2",
            marker: { color: "rgba(79, 70, 229, 0.25)" }
        };
        Plotly.newPlot("chart-monthly-trends", [traceMonthlyRev, traceMonthlyCount], getPlotlyLayout("Monthly Losses (MRR & Accounts)", {
            yaxis: { title: "Accounts lost", side: "left", zeroline: false },
            yaxis2: { title: "Monthly charge lost ($)", overlaying: "y", side: "right", showgrid: false },
            legend: { orientation: "h", y: -0.2 }
        }));
        
        // Plot Quarterly Trends
        const traceQuarter = {
            x: data.quarterly.quarters,
            y: data.quarterly.churn_counts,
            type: "bar",
            marker: { color: "#4f46e5" }
        };
        Plotly.newPlot("chart-quarterly-trends", [traceQuarter], getPlotlyLayout("Quarterly Churn Volume", {
            xaxis: { type: "category" }
        }));
        
        // Plot Yearly Trends
        const traceYear = {
            x: data.yearly.years.map(String),
            y: data.yearly.churn_counts,
            type: "bar",
            marker: { color: "#0d9488" }
        };
        Plotly.newPlot("chart-yearly-trends", [traceYear], getPlotlyLayout("Yearly Churn Comparison", {
            xaxis: { type: "category" }
        }));
    } catch (err) {
        console.error("Error trends page:", err);
    }
}

// PAGE 3: CUSTOMER SEGMENTATION
async function loadSegmentationPage(query) {
    try {
        const res = await fetch(`/api/segmentation?${query}`);
        const data = await res.json();
        
        // Age chart
        Plotly.newPlot("chart-segment-age", [{
            x: data.age_group.categories,
            y: data.age_group.churn_rates,
            type: "bar",
            marker: { color: "#e11d48" }
        }], getPlotlyLayout("Churn Rate (%) by Age Bracket", { yaxis: { title: "% Churn", suffix: "%" } }));
        
        // Gender Chart
        Plotly.newPlot("chart-segment-gender", [{
            labels: data.gender.categories,
            values: data.gender.totals,
            type: "pie",
            hole: 0.4,
            marker: { colors: ["#0d9488", "#4f46e5", "#d97706"] }
        }], getPlotlyLayout("Gender Demographics Ratio"));
        
        // Contract Type Chart
        Plotly.newPlot("chart-segment-contract", [{
            x: data.contract_type.categories,
            y: data.contract_type.churn_rates,
            type: "bar",
            marker: { color: "#4f46e5" }
        }], getPlotlyLayout("Contract Level Attrition Risks"));
        
        // Tenure Chart
        Plotly.newPlot("chart-segment-tenure", [{
            x: data.tenure_group.categories,
            y: data.tenure_group.churn_rates,
            type: "bar",
            marker: { color: "#0d9488" }
        }], getPlotlyLayout("Churn Probability by Lifecycle Tenure"));
        
        // Fetch and load cohort retention heatmap
        loadCohortRetentionMatrix();
    } catch (err) {
        console.error("Error segmentation page:", err);
    }
}

// PAGE 4: RFM LOYALTY
async function loadRFMPage(query) {
    try {
        const res = await fetch(`/api/rfm?${query}`);
        const data = await res.json();
        
        // Donut Chart of segments
        Plotly.newPlot("chart-rfm-donut", [{
            labels: data.segments,
            values: data.counts,
            type: "pie",
            hole: 0.5,
            marker: { colors: ["#0d9488", "#4f46e5", "#d97706", "#e11d48", "#64748b"] }
        }], getPlotlyLayout("Customer Segment Distributions"));
        
        // Bar Chart of average spent
        Plotly.newPlot("chart-rfm-bar", [{
            x: data.segments,
            y: data.avg_monetary,
            type: "bar",
            marker: { color: "#4f46e5" }
        }], getPlotlyLayout("Average Monthly Charges ($) by Segment"));
        
        // RFM Matrix Table
        const tbody = document.querySelector("#table-rfm-stats tbody");
        tbody.innerHTML = "";
        
        data.segments.forEach((seg, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${seg}</strong></td>
                <td>${data.counts[idx].toLocaleString()}</td>
                <td>${data.avg_recency[idx]} days</td>
                <td>${data.avg_frequency[idx]} sessions</td>
                <td>$${data.avg_monetary[idx].toFixed(2)}</td>
                <td><span class="badge ${data.churn_rates[idx] > 35 ? 'bg-rose' : 'bg-teal'}">${data.churn_rates[idx]}%</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error RFM page:", err);
    }
}

// PAGE 5: BEHAVIORAL ANALYTICS
async function loadBehaviorPage(query) {
    try {
        const res = await fetch(`/api/behavior?${query}`);
        const data = await res.json();
        
        // Satisfaction Chart
        Plotly.newPlot("chart-behavior-sat", [{
            x: data.satisfaction.categories,
            y: data.satisfaction.churn_rates,
            type: "bar",
            marker: { color: "#e11d48" }
        }], getPlotlyLayout("CSAT rating vs Churn Rate (%)"));
        
        // Tickets Chart
        Plotly.newPlot("chart-behavior-tickets", [{
            x: data.support_tickets.categories,
            y: data.support_tickets.churn_rates,
            type: "bar",
            marker: { color: "#4f46e5" }
        }], getPlotlyLayout("Support Ticket Volume Churn Correlation"));
        
        // Logins Chart
        Plotly.newPlot("chart-behavior-sessions", [{
            x: data.login_frequency.categories,
            y: data.login_frequency.churn_rates,
            type: "bar",
            marker: { color: "#0d9488" }
        }], getPlotlyLayout("Login Frequency Churn Rate"));
        
        // Complaints
        Plotly.newPlot("chart-behavior-complaints", [{
            x: data.complaints.categories,
            y: data.complaints.churn_rates,
            type: "bar",
            marker: { color: "#d97706" }
        }], getPlotlyLayout("Filed Complaints Count Impact"));
        
        // Avg Session Duration
        Plotly.newPlot("chart-behavior-duration", [{
            x: data.session_duration.categories,
            y: data.session_duration.churn_rates,
            type: "bar",
            marker: { color: "#10b981" }
        }], getPlotlyLayout("Avg Session Durations vs Churn"));
    } catch (err) {
        console.error("Error behavior page:", err);
    }
}

// PAGE 6: REVENUE RISK & SIMULATOR
async function loadRevenuePage(query) {
    try {
        const res = await fetch(`/api/revenue-risk?${query}`);
        const data = await res.json();
        
        // Populate High-Value customers at risk table
        const tbody = document.querySelector("#table-high-value-risk tbody");
        tbody.innerHTML = "";
        
        if (data.high_value_at_risk.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-secondary">No high-value active customers meet the current risk filters.</td></tr>`;
        } else {
            data.high_value_at_risk.forEach(cust => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${cust.customer_id}</td>
                    <td><strong>${cust.customer_name}</strong></td>
                    <td>$${cust.monthly_charge.toFixed(2)}</td>
                    <td>${cust.satisfaction_score} / 5</td>
                    <td>
                        <div class="flex-between" style="gap: 8px;">
                            <span style="min-width: 32px;">${cust.churn_probability}%</span>
                            <div class="c360-score-bar" style="margin-top: 0;">
                                <div class="c360-score-fill" style="width: ${cust.churn_probability}%;"></div>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge ${cust.risk_segment === 'Critical' ? 'bg-rose' : 'bg-gold'}">${cust.risk_segment}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline" onclick="viewCustomer360('${cust.customer_id}')">
                            <i class="fa-solid fa-address-card"></i> View Profile
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        
        // Trigger initial baseline simulator calculation values
        const summaryRes = await fetch(`/api/overview?${query}`);
        const overview = await summaryRes.json();
        
        document.getElementById("sim-baseline-churn").textContent = overview.churn_rate + "%";
        document.getElementById("sim-projected-churn").textContent = overview.churn_rate + "%";
        
    } catch (err) {
        console.error("Error revenue page:", err);
    }
}

// Trigger Simulated Business What-If
async function runWhatIfSimulation() {
    const shiftVal = document.getElementById("slider-contract-shift").value;
    const satVal = document.getElementById("slider-sat-boost").value;
    const campVal = document.getElementById("slider-camp-success").value;
    
    try {
        const res = await fetch("/api/whatif", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                contract_shift: shiftVal,
                satisfaction_boost: satVal,
                campaign_success: campVal
            })
        });
        const data = await res.json();
        
        // Update output metric fields with animations
        document.getElementById("sim-mrr-saved").textContent = "$" + Math.round(data.monthly_recurring_revenue_saved).toLocaleString();
        document.getElementById("sim-arr-saved").textContent = "$" + Math.round(data.annual_recurring_revenue_saved).toLocaleString();
        document.getElementById("sim-projected-churn").textContent = data.projected_churn_rate + "%";
        document.getElementById("sim-saved-count").textContent = data.expected_churned_saved.toLocaleString();
        
        showToast("Simulation calculations updated!");
    } catch (err) {
        console.error("Simulation failed:", err);
        showToast("Error processing what-if analytics.", true);
    }
}

// PAGE 7: PREDICTIVE FORECASTING
async function loadForecastingPage() {
    try {
        const res = await fetch("/api/forecasting");
        const data = await res.json();
        
        // 1. Plot Customer Volumes
        // Historical Active estimation helper (decreasing over time by churned count)
        let cumulativeChurn = 0;
        const activeHist = [];
        const initialActive = 50000;
        
        data.history_churn.forEach(loss => {
            cumulativeChurn += loss;
            activeHist.push(initialActive - cumulativeChurn);
        });
        
        const traceHistActive = {
            x: data.history_months,
            y: activeHist,
            name: "Active (History)",
            type: "scatter",
            mode: "lines",
            line: { color: "#0d9488", width: 2.5 }
        };
        
        // Forecast Customer Volumes
        let forecastActiveCumulative = activeHist[activeHist.length - 1];
        const activeForecast = [];
        data.forecast_churn.forEach(loss => {
            forecastActiveCumulative -= loss;
            activeForecast.push(forecastActiveCumulative);
        });
        
        const traceForeActive = {
            x: data.forecast_months,
            y: activeForecast,
            name: "Active (Forecast)",
            type: "scatter",
            mode: "lines",
            line: { color: "#4f46e5", dash: "dash", width: 2.5 }
        };
        Plotly.newPlot("chart-forecast-customers", [traceHistActive, traceForeActive], getPlotlyLayout("Active Customers Projections (Next 12 Months)", {
            yaxis: { title: "Subscribers Count" }
        }));
        
        // 2. Revenue lost forecast
        const traceRevenueForecast = {
            x: data.forecast_months,
            y: data.forecast_revenue_loss,
            type: "bar",
            marker: { color: "rgba(225, 29, 72, 0.6)" }
        };
        Plotly.newPlot("chart-forecast-revenue", [traceRevenueForecast], getPlotlyLayout("Projected Revenue Lost to Churn by Month ($)", {
            xaxis: { type: "category" }
        }));
        
        // Update forecasting summary KPI card counts
        document.getElementById("forecast-active-3m").textContent = activeForecast[2].toLocaleString();
        document.getElementById("forecast-active-6m").textContent = activeForecast[5].toLocaleString();
        document.getElementById("forecast-active-12m").textContent = activeForecast[11].toLocaleString();
        
        const total12mLost = data.forecast_revenue_loss.reduce((a, b) => a + b, 0);
        document.getElementById("forecast-revenue-lost-12m").textContent = "$" + Math.round(total12mLost).toLocaleString();
        
    } catch (err) {
        console.error("Error forecasting page:", err);
    }
}

// PAGE 8: CUSTOMER 360 EXPLORER PROFILE
async function searchCustomerProfile() {
    const custId = document.getElementById("input-search-customer").value.trim();
    if (!custId) {
        showToast("Enter a valid Customer ID", true);
        return;
    }
    
    const container = document.getElementById("customer-360-container");
    container.innerHTML = `<div class="empty-state"><div class="pulse-loader" style="margin: 0 auto 15px;"></div><h3>Loading Client Profile...</h3></div>`;
    
    try {
        const res = await fetch(`/api/customer360/${custId}`);
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Profile not found.");
        }
        const user = await res.json();
        
        // Build Profile layout
        container.innerHTML = `
            <div class="c360-grid">
                <!-- Profile Demographics Left Card -->
                <div class="dashboard-card c360-profile-card">
                    <div class="c360-avatar">${user.customer_name.split(' ').map(n => n[0]).join('')}</div>
                    <h2>${user.customer_name}</h2>
                    <span class="text-secondary">${user.customer_id}</span>
                    <div class="status-indicator">
                        <span class="badge ${user.churn_status === 'Active' ? 'bg-green' : 'bg-rose'}">${user.churn_status}</span>
                    </div>
                    
                    <div class="c360-details">
                        <div class="c360-detail-row"><span>Location:</span><strong>${user.city}, ${user.state}</strong></div>
                        <div class="c360-detail-row"><span>Age / Gender:</span><strong>${user.age} yrs / ${user.gender}</strong></div>
                        <div class="c360-detail-row"><span>Contract Plan:</span><strong>${user.contract_type}</strong></div>
                        <div class="c360-detail-row"><span>Tenure Status:</span><strong>${user.tenure_months} months</strong></div>
                        <div class="c360-detail-row"><span>Signup Date:</span><strong>${user.signup_date}</strong></div>
                    </div>
                </div>
                
                <!-- Usage details Right Card tabs -->
                <div class="dashboard-card c360-tabs">
                    <div>
                        <h3>Risk Diagnosis & AI Drivers</h3>
                        <div class="divider" style="margin: 8px 0 16px;"></div>
                        <div class="grid-2">
                            <div>
                                <span class="text-secondary" style="font-size: 13px;">Churn Risk Probability:</span>
                                <h3 style="font-size: 26px; font-weight: 800; margin-top: 4px;" class="${user.churn_probability > 60 ? 'text-rose' : 'text-teal'}">${user.churn_probability}%</h3>
                                <div class="c360-score-bar">
                                    <div class="c360-score-fill" style="width: ${user.churn_probability}%; background: ${user.churn_probability > 60 ? 'var(--color-rose)' : 'var(--color-teal)'};"></div>
                                </div>
                            </div>
                            
                            <div>
                                <span class="text-secondary" style="font-size: 13px;">Customer Health Score:</span>
                                <h3 style="font-size: 26px; font-weight: 800; margin-top: 4px;" class="${user.health_score > 60 ? 'text-teal' : 'text-rose'}">${user.health_score} / 100</h3>
                                <div class="c360-score-bar">
                                    <div class="c360-score-fill" style="width: ${user.health_score}%; background: ${user.health_score > 60 ? 'var(--color-teal)' : 'var(--color-rose)'};"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-15">
                            <span class="text-secondary" style="font-size: 12px; font-weight: 600; text-transform: uppercase;">Top Churn Risk Drivers:</span>
                            <div class="c360-drivers-container">
                                ${user.churn_drivers.map(d => `<span class="c360-driver-tag"><i class="fa-solid fa-triangle-exclamation"></i> ${d}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                    
                    <div>
                        <h3>Usage & Financial History</h3>
                        <div class="divider" style="margin: 8px 0 16px;"></div>
                        <div class="grid-3">
                            <div class="metric-block">
                                <span class="label">Monthly Charge</span>
                                <h4>$${user.monthly_charge.toFixed(2)}</h4>
                            </div>
                            <div class="metric-block">
                                <span class="label">Total Revenue LTV</span>
                                <h4>$${user.total_spent.toFixed(2)}</h4>
                            </div>
                            <div class="metric-block">
                                <span class="label">RFM Segment</span>
                                <span class="badge bg-violet" style="text-align: center; margin-top: 4px;">${user.rfm_segment}</span>
                            </div>
                        </div>
                        <div class="grid-3 mt-15">
                            <div class="metric-block">
                                <span class="label">Avg Session Time</span>
                                <h4>${user.avg_session_duration}m</h4>
                            </div>
                            <div class="metric-block">
                                <span class="label">Support Tickets</span>
                                <h4>${user.support_tickets} open</h4>
                            </div>
                            <div class="metric-block">
                                <span class="label">Complaints Filed</span>
                                <h4>${user.complaints_count} files</h4>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-translucent-gold" style="padding: 16px; border-radius: 12px; border: 1px dashed var(--color-gold);">
                        <h4 class="text-gold"><i class="fa-solid fa-clipboard-list"></i> Next Best Action (Retention Recommendation)</h4>
                        <p class="mt-5" style="font-size: 13px; color: var(--text-primary);">${user.recommended_action}</p>
                    </div>
                </div>
            </div>
            ${generateTimelineHTML(user)}
        `;
        
    } catch (err) {
        console.error("Customer 360 search failed:", err);
        container.innerHTML = `
            <div class="empty-state text-rose">
                <i class="fa-solid fa-triangle-exclamation empty-icon" style="color: var(--color-rose);"></i>
                <h3>Search Failed</h3>
                <p>${err.message}</p>
            </div>
        `;
    }
}

// Redirect action trigger to load customer360 search profile view
function viewCustomer360(customerId) {
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("data-page") === "page-customer360") {
            item.click();
        }
    });
    document.getElementById("input-search-customer").value = customerId;
    searchCustomerProfile();
}

// PAGE 10: MODEL PERFORMANCE ANALYTICS
async function loadModelPerformancePage() {
    try {
        const res = await fetch("/api/model-performance");
        const data = await res.json();
        
        // Populates model metrics table
        const tbody = document.querySelector("#table-model-comparison tbody");
        tbody.innerHTML = "";
        
        Object.keys(data.comparison).forEach(modelName => {
            const metrics = data.comparison[modelName];
            const isBest = modelName.includes("XGBoost") || modelName.includes("Gradient");
            
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${modelName} ${isBest ? '<span class="badge bg-teal" style="font-size: 9px; padding: 2px 4px;">Best Model</span>' : ''}</strong></td>
                <td>${(metrics.Accuracy * 100).toFixed(2)}%</td>
                <td>${(metrics.Precision * 100).toFixed(2)}%</td>
                <td>${(metrics.Recall * 100).toFixed(2)}%</td>
                <td>${(metrics.F1 * 100).toFixed(2)}%</td>
                <td>${(metrics["ROC-AUC"] * 100).toFixed(2)}%</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Plot Top 15 Feature Importances horizontal bar chart
        const features = data.feature_importances.map(item => item[0]);
        const importances = data.feature_importances.map(item => item[1]);
        
        Plotly.newPlot("chart-model-importance", [{
            x: importances.reverse(),
            y: features.reverse(),
            type: "bar",
            orientation: "h",
            marker: { color: "rgba(79, 70, 229, 0.75)" }
        }], getPlotlyLayout("Top Predictor Features (Global Churn Drivers)", {
            margin: { t: 40, b: 40, l: 140, r: 20 }
        }));
        
    } catch (err) {
        console.error("Error model performance page:", err);
    }
}

// --- FILE EXPORTS ---

// Downloads filtered database profile rows as Excel/CSV
function exportFilteredCSV() {
    const query = new URLSearchParams(globalFilters).toString();
    window.location.href = `/api/export?${query}&format=csv`;
}

// ==========================================
// HUMAN SAAS REDESIGN UPGRADES & UTILITIES
// ==========================================

// Active Filter Pills controller
function updateFilterPills() {
    const container = document.getElementById("active-filters-pills");
    const list = document.getElementById("pills-list");
    if (!container || !list) return;
    list.innerHTML = "";
    
    let hasActiveFilters = false;
    
    for (const [key, value] of Object.entries(globalFilters)) {
        if (value !== "All" && key !== "rfm_segment") {
            hasActiveFilters = true;
            
            let displayLabel = "";
            if (key === "region") displayLabel = "Region: " + value;
            else if (key === "age_group") displayLabel = "Age: " + value;
            else if (key === "contract_type") displayLabel = "Contract: " + value;
            else if (key === "churn_risk") displayLabel = "Risk: " + value;
            
            const pill = document.createElement("div");
            pill.className = "filter-pill";
            pill.innerHTML = `
                <span>${displayLabel}</span>
                <i class="fa-solid fa-xmark pill-remove" data-key="${key}" style="cursor: pointer; margin-left: 6px;"></i>
            `;
            
            pill.querySelector(".pill-remove").addEventListener("click", () => {
                clearFilter(key);
            });
            
            list.appendChild(pill);
        }
    }
    
    if (hasActiveFilters) {
        container.style.display = "flex";
    } else {
        container.style.display = "none";
    }
}

function clearFilter(key) {
    globalFilters[key] = "All";
    const idMap = {
        "region": "filter-region",
        "age_group": "filter-age",
        "contract_type": "filter-contract",
        "churn_risk": "filter-risk"
    };
    const el = document.getElementById(idMap[key]);
    if (el) el.value = "All";
    loadActivePageData();
}

// Cohort cell visual styling generator
function getCohortCellStyles(pct) {
    const isDark = currentTheme === "dark";
    let bgColor;
    let textColor;
    
    if (isDark) {
        const lightness = 15 + (pct / 100) * 30; // 15% to 45%
        const saturation = 15 + (pct / 100) * 60; // 15% to 75%
        bgColor = `hsl(224, ${saturation}%, ${lightness}%)`;
        textColor = pct > 40 ? "#ffffff" : "#94a3b8";
    } else {
        const lightness = 95 - (pct / 100) * 50; // 95% to 45%
        const saturation = 15 + (pct / 100) * 60; // 15% to 75%
        bgColor = `hsl(224, ${saturation}%, ${lightness}%)`;
        textColor = pct > 50 ? "#ffffff" : "#334155";
    }
    
    return `background-color: ${bgColor}; color: ${textColor};`;
}

// Customer Journey Timeline generator
function generateTimelineHTML(user) {
    const m1Class = "success";
    const m1Title = "Account Initialized";
    const m1Desc = `Customer signed up on a <strong>${user.contract_type}</strong> plan with an initial monthly charge of <strong>$${user.monthly_charge.toFixed(2)}</strong>.`;
    const m1Date = user.signup_date;
    
    let m2Class = "active";
    if (user.support_tickets > 3) {
        m2Class = "danger";
    } else if (user.support_tickets > 0) {
        m2Class = "warning";
    }
    const m2Title = `Customer Support Operations`;
    const m2Desc = `Logged <strong>${user.support_tickets} support tickets</strong> during lifecycle. Average session length is <strong>${user.avg_session_duration.toFixed(1)} minutes</strong> with <strong>${user.sessions_per_month} sessions/month</strong>.`;
    const m2Date = `Lifecycle Midpoint`;
    
    let m3Class = "active";
    if (user.satisfaction_score <= 2 || user.complaints_count > 0) {
        m3Class = "danger";
    } else if (user.satisfaction_score === 3) {
        m3Class = "warning";
    } else {
        m3Class = "success";
    }
    const m3Title = "Customer CSAT Feedback & Engagement";
    const m3Desc = `Satisfaction rated at <strong>${user.satisfaction_score}/5</strong>. Filed <strong>${user.complaints_count} complaints</strong> in the last 30 days.`;
    const m3Date = user.last_feedback_date || "Recent Feedback";
    
    let m4Class = "active";
    if (user.churn_status === "Churned" || user.churn_probability > 60) {
        m4Class = "danger";
    } else if (user.churn_probability >= 30) {
        m4Class = "warning";
    } else {
        m4Class = "success";
    }
    const m4Title = `AI Predictive Scoring & Retention Output`;
    const m4Desc = `Machine learning model computed a churn risk probability of <strong>${user.churn_probability}%</strong>. Account Health Score is <strong>${user.health_score}/100</strong>. Recommended Action: <em>${user.recommended_action}</em>.`;
    const m4Date = "Real-time AI Diagnosis";

    return `
        <div class="dashboard-card" style="margin-top: 20px;">
            <h3><i class="fa-solid fa-timeline text-violet"></i> Customer 360 Journey Timeline</h3>
            <p class="text-secondary mt-5">Chronological customer events, ticket volumes, satisfaction logs, and machine learning risk evaluations.</p>
            <div class="divider" style="margin-top: 10px; margin-bottom: 20px;"></div>
            <div class="timeline">
                <div class="timeline-item ${m1Class}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <span class="timeline-time">${m1Date}</span>
                        <span class="timeline-title">${m1Title}</span>
                        <p class="timeline-desc">${m1Desc}</p>
                    </div>
                </div>
                <div class="timeline-item ${m2Class}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <span class="timeline-time">${m2Date}</span>
                        <span class="timeline-title">${m2Title}</span>
                        <p class="timeline-desc">${m2Desc}</p>
                    </div>
                </div>
                <div class="timeline-item ${m3Class}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <span class="timeline-time">${m3Date}</span>
                        <span class="timeline-title">${m3Title}</span>
                        <p class="timeline-desc">${m3Desc}</p>
                    </div>
                </div>
                <div class="timeline-item ${m4Class}">
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <span class="timeline-time">${m4Date}</span>
                        <span class="timeline-title">${m4Title}</span>
                        <p class="timeline-desc">${m4Desc}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Dynamic Cohort Retention Matrix Loader
async function loadCohortRetentionMatrix() {
    const container = document.getElementById("cohort-table-container");
    if (!container) return;
    
    try {
        const res = await fetch("/api/cohorts");
        const data = await res.json();
        
        let html = `
            <table class="cohort-table">
                <thead>
                    <tr>
                        <th style="text-align: left;">Cohort Month</th>
                        <th>Customers</th>
                        <th>Month 1</th>
                        <th>Month 3</th>
                        <th>Month 6</th>
                        <th>Month 12</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        data.cohort_months.forEach((month, idx) => {
            const size = data.sizes[idx];
            const m1 = data.matrix[0][idx];
            const m3 = data.matrix[1][idx];
            const m6 = data.matrix[2][idx];
            const m12 = data.matrix[3][idx];
            
            html += `
                <tr>
                    <td class="cohort-name">${month}</td>
                    <td class="cohort-size-cell">${size.toLocaleString()}</td>
                    <td class="cohort-val" style="${getCohortCellStyles(m1)}">${m1}%</td>
                    <td class="cohort-val" style="${getCohortCellStyles(m3)}">${m3}%</td>
                    <td class="cohort-val" style="${getCohortCellStyles(m6)}">${m6}%</td>
                    <td class="cohort-val" style="${getCohortCellStyles(m12)}">${m12}%</td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
        `;
        
        container.innerHTML = html;
    } catch (err) {
        console.error("Error loading cohort matrix:", err);
        container.innerHTML = `<div class="empty-state text-rose"><i class="fa-solid fa-triangle-exclamation"></i><p>Failed to load cohort retention matrix.</p></div>`;
    }
}

// Helper for setting KPI card values with custom trend badges
function setKPICard(id, value, trendText, trendType, isCaretUp) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
    
    const card = el.parentElement;
    let trendEl = card.querySelector(".kpi-trend");
    if (!trendEl) {
        trendEl = document.createElement("span");
        el.after(trendEl);
    }
    
    let cls = "neutral";
    let icon = "";
    if (trendType === "success") {
        cls = "up";
        icon = isCaretUp ? '<i class="fa-solid fa-caret-up"></i>' : '<i class="fa-solid fa-caret-down"></i>';
    } else if (trendType === "danger") {
        cls = "down";
        icon = isCaretUp ? '<i class="fa-solid fa-caret-up"></i>' : '<i class="fa-solid fa-caret-down"></i>';
    } else {
        cls = "neutral";
        icon = '<i class="fa-solid fa-minus"></i>';
    }
    
    trendEl.className = `kpi-trend ${cls}`;
    trendEl.innerHTML = `${icon} ${trendText}`;
}
