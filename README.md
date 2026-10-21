# 🍽️ Zomato AI Data Engineering Platform

An end-to-end data engineering and AI analytics project that transforms **10 million food-delivery orders** into business insights through data modeling, analytics dashboards, and natural-language querying.

🔗 **Live Dashboard:** [https://zomato-eben-ai.streamlit.app/]  
💻 **GitHub Repository:** https://github.com/ManLikeEben/zomato-ai-data-engineering

## 🚀 Project Overview

This project demonstrates how large-scale food-delivery data can be processed, transformed, validated, and analyzed using an end-to-end data engineering workflow.

The platform combines a DuckDB analytical warehouse, dbt transformations, an interactive Streamlit dashboard, and an AI-powered SQL assistant called **EBEN(Enhanced Being for Exploration & Navigation)**.

Users can explore business metrics through the dashboard or ask EBEN questions in plain English.

## 🏗️ Architecture

```text
Raw CSV Datasets
       │
       ▼
Python + Pandas
       │
       ▼
DuckDB Data Warehouse
       │
       ▼
dbt Transformations & Tests
       │
       ▼
Analytical Data Models
       │
       ├──────────────► Streamlit Dashboard
       │
       └──────────────► EBEN AI Assistant
                              │
                              ▼
                       Google Gemini
                              │
                              ▼
                      SQL Validation
                              │
                              ▼
                      DuckDB Query Results
```

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Data processing and application logic |
| Pandas | Data cleaning and manipulation |
| DuckDB | Analytical data warehouse |
| SQL | Data querying and analysis |
| dbt | Data transformation and quality testing |
| Streamlit | Interactive web dashboard |
| Google Gemini | Natural-language SQL generation |
| Hugging Face | Hosting the cloud-accessible database |
| Git & GitHub | Version control and source code management |

## 📊 Dataset & Key Metrics

The project processes millions of records across restaurant, customer, food, order, order-item, and review datasets.

| Metric | Validated Result |
|---|---:|
| Total orders | 10,000,000 |
| Delivered orders | 9,150,122 |
| Delivery success rate | 91.50% |
| Total delivered revenue | ₹4,418,169,887 |

The dataset covers **1 January 2024 to 30 June 2026**.

These figures reflect the project's dataset and analytical definitions, not official live Zomato business statistics.

## 🤖 Meet EBEN: AI-Powered Data Querying

EBEN allows users to ask questions about the warehouse in natural language rather than writing SQL manually.

Example questions:

- How many orders were delivered?
- What is the total revenue from delivered orders?
- What are the top 10 restaurants by revenue?
- Which month had the highest revenue?
- What is the delivery success rate?

### How it works

1. The user submits a question.
2. Google Gemini generates a DuckDB SQL query.
3. The application validates the generated SQL.
4. DuckDB executes the query against the analytical database.
5. EBEN presents the results in a readable format.

## 📈 Analytical Capabilities

The platform supports exploration of:

- Order volumes and delivery performance.
- Delivered revenue and monthly trends.
- Restaurant revenue rankings.
- Customer and food-related analytics.
- Business performance indicators.

## ☁️ Deployment

The dashboard is deployed using Streamlit Community Cloud, while the analytical database is hosted on Hugging Face.

This setup makes the project accessible online without requiring a continuously running personal computer or a paid cloud database.

The Gemini API is used for AI-powered querying. API availability and quota limits may affect response reliability.

## 🔒 Security & Data Integrity

- API credentials are stored outside source code.
- Environment files containing secrets are excluded from version control.
- The AI query workflow validates generated SQL before execution.
- The original local warehouse is retained separately from the cloud-accessible database.
- Data transformations are tested to help ensure consistency and reliability.

## 💻 Local Setup

### Prerequisites

- Python
- Git
- A Google Gemini API key for AI querying

### Installation

Clone the repository:

```bash
git clone https://github.com/ManLikeEben/zomato-ai-data-engineering.git
cd zomato-ai-data-engineering
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables using a local `.env` file. Never commit API keys or other secrets.

Run the dashboard:

```bash
streamlit run streamlit_app/app.py
```

Follow the project's configuration for accessing the database and enabling Gemini.

## 🔮 Potential Future Improvements

- Improve AI retry and error handling.
- Add automated pipeline scheduling.
- Expand automated data quality monitoring.
- Improve query-result visualization.
- Add further business KPIs and analytical views.
- Add automated deployment and testing workflows.

## 👨‍💻 Author

**Ebenezer Oluwajuwon Olatunya**

Data Analytics | Data Engineering | AI Applications

[GitHub Profile](https://github.com/ManLikeEben)