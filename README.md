# From Customer Data to Customer Action — Reverse ETL

A simple, runnable version of the PPT project using a synthetic dataset with about 100,000 raw rows.

## Pipeline
CSV (100k raw rows, including intentionally dirty records)
→ pandas cleaning
→ DuckDB table
→ SQL analysis and High / Medium / Low Value segmentation
→ transform High Value records
→ `simulated_crm.csv`

## Requirements
- Python 3.10+
- VS Code

## Run in VS Code terminal
```bash
python -m venv .venv
```
Windows:
```powershell
.venv\Scripts\Activate.ps1
```
macOS/Linux:
```bash
source .venv/bin/activate
```
Install and run:
```bash
pip install -r requirements.txt
python pipeline.py
```

## Files
- `customers_raw.csv`: 100,000 synthetic rows; includes deliberately injected unclean data.
- `pipeline.py`: cleaning, DuckDB loading, SQL segmentation, summary, and CRM export.
- `customers_clean.csv`: generated after cleaning.
- `segment_summary.csv`: generated segment counts and averages.
- `simulated_crm.csv`: transformed High Value customers, ready for a simulated CRM import.
- `customers.duckdb`: DuckDB database created when the pipeline runs.

## Cleaning rules
- Converts numeric fields using safe coercion; invalid values become missing.
- Removes rows with missing customer ID, name, city, spend, or purchase count.
- Removes blank names/cities.
- Removes negative spending and non-positive purchase counts.
- Removes duplicate customer IDs.

## Segmentation rules (same as the PPT)
- High Value: total_spent >= 30,000 AND purchase_count >= 20
- Medium Value: total_spent >= 15,000 AND purchase_count >= 10
- Low Value: all remaining valid customers

## Important
This is a simulated Reverse ETL pipeline. It exports a CSV for a CRM; it does not connect to a live CRM.

## Streamlit dashboard
Install the updated requirements, then launch:
```bash
pip install -r requirements.txt
streamlit run app.py
```
The dashboard includes an overview, segment charts, spending and purchase-frequency visualizations, a searchable/filterable data explorer, CSV downloads, and a button to rerun the pipeline.
