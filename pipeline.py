from pathlib import Path
import pandas as pd
import duckdb

BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "customers_raw.csv"
CLEAN_FILE = BASE_DIR / "customers_clean.csv"
CRM_FILE = BASE_DIR / "simulated_crm.csv"
SUMMARY_FILE = BASE_DIR / "segment_summary.csv"

def main():
    print("1) Loading raw customer data...")
    raw = pd.read_csv(RAW_FILE)
    print(f"Raw rows: {len(raw):,}")

    print("\n2) Cleaning data...")
    df = raw.copy()
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["total_spent"] = pd.to_numeric(df["total_spent"], errors="coerce")
    df["purchase_count"] = pd.to_numeric(df["purchase_count"], errors="coerce")

    # Remove missing/invalid fields, impossible values, and duplicate customer IDs.
    before = len(df)
    df = df.dropna(subset=["customer_id", "name", "city", "total_spent", "purchase_count"])
    df["name"] = df["name"].astype(str).str.strip()
    df["city"] = df["city"].astype(str).str.strip()
    df = df[(df["name"] != "") & (df["city"] != "")]
    df = df[(df["total_spent"] >= 0) & (df["purchase_count"] > 0)]
    df = df.drop_duplicates(subset=["customer_id"], keep="first")
    df["customer_id"] = df["customer_id"].astype("int64")
    df["purchase_count"] = df["purchase_count"].astype("int64")
    print(f"Removed rows: {before - len(df):,}")
    print(f"Clean rows: {len(df):,}")
    df.to_csv(CLEAN_FILE, index=False)

    print("\n3) Loading clean data into DuckDB...")
    con = duckdb.connect(str(BASE_DIR / "customers.duckdb"))
    con.register("clean_df", df)
    con.execute("CREATE OR REPLACE TABLE customers AS SELECT * FROM clean_df")

    print("\n4) Analyzing and segmenting customers...")
    query = """
    SELECT
        customer_id,
        name,
        city,
        total_spent,
        purchase_count,
        ROUND(total_spent / purchase_count, 2) AS avg_spending,
        CASE
            WHEN total_spent >= 30000 AND purchase_count >= 20 THEN 'High Value'
            WHEN total_spent >= 15000 AND purchase_count >= 10 THEN 'Medium Value'
            ELSE 'Low Value'
        END AS customer_segment
    FROM customers
    """
    segments = con.execute(query).df()
    print(segments["customer_segment"].value_counts().to_string())

    summary = con.execute("""
        SELECT customer_segment,
               COUNT(*) AS customer_count,
               ROUND(AVG(total_spent), 2) AS avg_total_spent,
               ROUND(AVG(purchase_count), 2) AS avg_purchase_count
        FROM (
            SELECT *,
                CASE
                    WHEN total_spent >= 30000 AND purchase_count >= 20 THEN 'High Value'
                    WHEN total_spent >= 15000 AND purchase_count >= 10 THEN 'Medium Value'
                    ELSE 'Low Value'
                END AS customer_segment
            FROM customers
        )
        GROUP BY customer_segment
        ORDER BY customer_count DESC
    """).df()
    summary.to_csv(SUMMARY_FILE, index=False)

    print("\n5) Transforming High Value customers for the simulated CRM...")
    high = segments[segments["customer_segment"] == "High Value"].copy()
    crm = high.rename(columns={
        "customer_id": "crm_customer_id",
        "name": "customer_name",
        "city": "location",
        "total_spent": "lifetime_value",
        "customer_segment": "segment"
    })
    crm.to_csv(CRM_FILE, index=False)
    print(f"Exported {len(crm):,} High Value customers to {CRM_FILE.name}")

    print("\nDone. Outputs created:")
    print(f"- {CLEAN_FILE.name}")
    print(f"- {SUMMARY_FILE.name}")
    print(f"- {CRM_FILE.name}")
    print(f"- customers.duckdb")
    con.close()

if __name__ == "__main__":
    main()
