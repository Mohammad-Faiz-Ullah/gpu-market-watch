# 🚀 GPU Market Watch

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://gpu-market-watch-pxogjqtjs6ij8kf8kjihze.streamlit.app)
[![Daily GPU Scraper](https://github.com/Mohammad-Faiz-Ullah/gpu-market-watch/actions/workflows/daily_scraper.yml/badge.svg)](https://github.com/Mohammad-Faiz-Ullah/gpu-market-watch/actions/workflows/daily_scraper.yml)

A fully automated data pipeline that tracks GPU prices daily to find the best "Price-to-Performance" value cards.

## 📊 How It Works
This project uses an **ETL (Extract, Transform, Load)** architecture to run completely autonomously:

1.  **Extract:** A Python script scrapes real-time pricing and benchmark scores from *VideoCardBenchmark.net*.
2.  **Transform:** Data is cleaned using **Pandas**, and a "Value Rating" (Score / Price) is calculated for every GPU.
3.  **Load:** The clean data is pushed to a **Supabase (PostgreSQL)** database.
4.  **Visualize:** A **Streamlit** dashboard fetches the latest data from the DB to display the top deals.
5.  **Automate:** **GitHub Actions** runs the scraper every day at 06:00 UTC (11:30 AM IST) to keep data fresh.

## 🛠️ Tech Stack
* **Language:** Python 3.13
* **Cloud Database:** Supabase (PostgreSQL)
* **Automation:** GitHub Actions (Cron Job)
* **Frontend:** Streamlit
* **Libraries:** `pandas`, `beautifulsoup4`, `psycopg2`, `requests`

## 📂 Project Structure
```text
├── .github/workflows/   # Contains the automation config (daily_scraper.yml)
├── app.py               # The Streamlit Dashboard frontend
├── scraper.py           # The backend script (runs on GitHub Actions)
├── requirements.txt     # List of dependencies
└── README.md            # Project Documentation
