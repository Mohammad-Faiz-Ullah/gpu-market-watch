import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import psycopg2

# ==========================================
# 1. THE SETUP: Define Target & Headers
# ==========================================

URL = "https://www.videocardbenchmark.net/gpu_list.php"
HEADERS = {"User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

def clean_price(price_str):
    if "NA" in price_str or not price_str:
        return None
    clean_str = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(clean_str)
    except ValueError:
        return None

def get_db_connection():
    """Establishes connection to Supabase using Environment Variables"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database="postgres",
            user="postgres",
            password=os.getenv("DB_PASS"),
            port="6543"
        )
        return conn
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return None

def scrape_gpu_data():
    print(f"🚀 Connecting to {URL}...")

    # ==========================================
    # 2. THE REQUEST
    # ==========================================
    response = requests.get(URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"❌ Failed to fetch page. Status code: {response.status_code}")
        return

    print("✅ Connection Successful! Parsing HTML...")

    # ==========================================
    # 3. THE SOUP
    # ==========================================
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id":"cputable"})

    if not table:
        print("❌ Could not find the table.")
        return

    rows = table.find_all("tr")[1:]
    gpu_data=[]

    # ==========================================
    # 4. THE EXTRACTION
    # ==========================================
    print(f"🔍 Found {len(rows)} GPUs. Extracting data...")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            gpu_name = cols[0].text.strip()
            
            try:
                score = int(cols[1].text.replace(',', ''))
            except:
                score = 0

            price = None
            for col in cols:
                text = col.text.strip()
                if "$" in text or "*" in text:
                    found_price = clean_price(text)
                    if found_price and found_price > 30:
                        price = found_price
                        break

            if price and score > 0:
                # Calculate Value Rating (Score per Dollar)
                value_rating = score / price

                gpu_data.append({
                    "GPU_Name": gpu_name,
                    "Benchmark_Score": score,
                    "Price_USD": price,
                    "Value_Rating": value_rating,
                    "Manufacturer": "NVIDIA" if "GeForce" in gpu_name or "RTX" in gpu_name else "AMD" if "Radeon" in gpu_name else "Intel" if "Arc" in gpu_name else "Other"
                })

    # ==========================================
    # 5. THE CLEANUP (Pandas)
    # ==========================================
    df = pd.DataFrame(gpu_data)
    
    # Keeping only major brands and decent cards
    df = df[df['Manufacturer'].isin(['NVIDIA', 'AMD', 'Intel'])]
    df = df[df['Benchmark_Score'] > 1000]

    print(f"🎉 Scraped & Cleaned {len(df)} GPUs. Uploading to Supabase...")

    # ==========================================
    # 6. THE UPLOAD: Insert into Supabase
    # ==========================================
    conn = get_db_connection()
    
    if not conn:
        print("❌ Upload skipped due to connection error.")
        return

    cur = conn.cursor()

    # Clearing old data to get the latest prices
    cur.execute("TRUNCATE TABLE gpu_prices;") 
    
    count = 0
    for index, row in df.iterrows():
        try:
            cur.execute("""
                INSERT INTO gpu_prices (gpu_name, price, benchmark_score, value_rating, manufacturer)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                row['GPU_Name'], 
                row['Price_USD'], 
                row['Benchmark_Score'], 
                row['Value_Rating'], 
                row['Manufacturer']
            ))
            count += 1
        except Exception as e:
            print(f"⚠️ Error inserting {row['GPU_Name']}: {e}")
            conn.rollback() # Skip this row and continue

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Successfully uploaded {count} rows to Supabase!")

if __name__ == "__main__":
    scrape_gpu_data()


