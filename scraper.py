import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# ==========================================
# 1. THE SETUP: Define Target & Headers
# ==========================================

# The URL where the data lives
URL = "https://www.videocardbenchmark.net/gpu_list.php"

# Looking like a real browser is a must, or the website will block us.

HEADERS = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

def clean_price(price_str):
    # Custom function to turn '$1,299.99*' into the number 1299.99
    if "NA" in price_str or not price_str:
        return None
    clean_str = re.sub(r'[^\d.]', '', price_str)  # Remove '$', '*', and ',' (commas break conversion)

    try:
        return float(clean_str)
    except ValueError:
        return  None

def scrape_gpu_data():
    print(f"🚀 Connecting to {URL}...")

    # ==========================================
    # 2. THE REQUEST: Fetch the HTML
    # ==========================================

    response = requests.get(URL, headers=HEADERS)

    if response.status_code != 200:
        print(f"❌ Failed to fetch page. Status code: {response.status_code}")
        return

    print("✅ Connection Successful! Parsing HTML...")

    # ==========================================
    # 3. THE SOUP: Parse the HTML
    # ==========================================

    # BeautifulSoup turns the raw HTML text into a tree of objects we can search
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the specific table. On PassMark, the big list has id="cputable"

    table = soup.find("table", {"id":"cputable"})  # FINDING ID: Right-click the table in Chrome -> Inspect

    if not table:
        print("❌ Could not find the table. The website structure might have changed.")
        return

    rows = table.find_all("tr")[1:]  # Getting all rows (<tr> tags), skipping the header row

    gpu_data=[]

    # ==========================================
    # 4. THE EXTRACTION: Loop through rows
    # ==========================================
    print(f"🔍 Found {len(rows)} GPUs. Extracting data...")

    for row in rows:
        cols = row.find_all("td")

        # Checking if row has enough columns (Passmark has Name, Price, Mark, etc.)
        if len(cols) >= 4:
            # Column 0: GPU Name
            gpu_name = cols[0].text.strip()

            # Column 1: Passmark G3D Score (Performance)
            try:
                score = int(cols[1].text.replace(',', ''))
            except:
                score = 0

            # Looking for the column with a '$' sign
            price = None
            for col in cols:
                text = col.text.strip()
                if "$" in text or "*" in text:  # Price usually has $ or * (e.g., $1,299*)
                    found_price = clean_price(text)
                    # Ensure it's not a tiny number like "1.03" (which is the Value column)
                    if found_price and found_price > 30:
                        price = found_price
                        break

                        # Only add if we found a valid price & score
            if price and score > 0:
                gpu_data.append({
                    "GPU_Name": gpu_name,
                    "Benchmark_Score": score,
                    "Price_USD": price,
                    "Manufacturer": "NVIDIA" if "GeForce" in gpu_name or "RTX" in gpu_name else "AMD" if "Radeon" in gpu_name else "Intel" if "Arc" in gpu_name else "Other"
                })

    # ==========================================
    # 5. THE LOAD: Save to CSV
    # ==========================================

    df = pd.DataFrame(gpu_data)

    # Filter: Let's remove "Other" brands and very weak cards to keep dataset clean
    df = df[df['Manufacturer'].isin(['NVIDIA', 'AMD', 'Intel'])]
    df = df[df['Benchmark_Score'] > 1000]  # Remove ancient cards

    output_file = "gpu_market_data.csv"
    df.to_csv(output_file, index=False)

    print(f"🎉 Success! Scraped {len(df)} GPUs.")
    print(f"💾 Data saved to '{output_file}'")
    print(df.head())

if __name__ == "__main__":
    scrape_gpu_data()