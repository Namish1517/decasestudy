from pathlib import Path
import subprocess
import sys

import pandas as pd
import streamlit as st
import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent
RAW_FILE = BASE_DIR / "customers_raw.csv"
CLEAN_FILE = BASE_DIR / "customers_clean.csv"
SUMMARY_FILE = BASE_DIR / "segment_summary.csv"
CRM_FILE = BASE_DIR / "simulated_crm.csv"
PIPELINE_FILE = BASE_DIR / "pipeline.py"

st.set_page_config(
    page_title="Customer Action | Reverse ETL",
    page_icon="📊",
    layout="wide",
)

st.title("📊 From Customer Data to Customer Action")
st.caption("Reverse ETL dashboard • Synthetic customer dataset • pandas + DuckDB + Streamlit")

# Sidebar controls
st.sidebar.header("Dashboard")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Customer Segments", "Data Explorer", "Pipeline & Exports"],
)
st.sidebar.markdown("---")
st.sidebar.caption("Pipeline: Raw CSV → Cleaning → DuckDB → Segmentation → CRM export")

def load_csv(path):
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as exc:
            st.error(f"Could not read {path.name}: {exc}")
    return pd.DataFrame()

raw = load_csv(RAW_FILE)
clean = load_csv(CLEAN_FILE)
summary = load_csv(SUMMARY_FILE)
crm = load_csv(CRM_FILE)

if clean.empty:
    st.warning("Cleaned data was not found yet. Run the pipeline from the Pipeline & Exports page.")
    st.stop()

# Recreate segment column for consistent filtering and charting
if "customer_segment" not in clean.columns:
    clean["customer_segment"] = "Low Value"
    high_mask = (clean["total_spent"] >= 30000) & (clean["purchase_count"] >= 20)
    med_mask = (clean["total_spent"] >= 15000) & (clean["purchase_count"] >= 10)
    clean.loc[med_mask, "customer_segment"] = "Medium Value"
    clean.loc[high_mask, "customer_segment"] = "High Value"

segment_order = ["High Value", "Medium Value", "Low Value"]
colors = {"High Value": "#16a34a", "Medium Value": "#2563eb", "Low Value": "#f59e0b"}

if page == "Overview":
    st.subheader("Pipeline at a glance")
    raw_count = len(raw) if not raw.empty else 100000
    clean_count = len(clean)
    removed = max(raw_count - clean_count, 0)
    high_count = int((clean["customer_segment"] == "High Value").sum())
    medium_count = int((clean["customer_segment"] == "Medium Value").sum())
    low_count = int((clean["customer_segment"] == "Low Value").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Raw customer rows", f"{raw_count:,}")
    c2.metric("Clean customer rows", f"{clean_count:,}", delta=f"{clean_count - raw_count:,} rows after cleaning")
    c3.metric("Rows removed", f"{removed:,}")
    c4.metric("High-value customers", f"{high_count:,}")

    st.markdown("### Customer segmentation")
    left, right = st.columns(2)
    counts = clean["customer_segment"].value_counts().reindex(segment_order, fill_value=0).rename_axis("Segment").reset_index(name="Customers")
    with left:
        fig = px.pie(
            counts, names="Segment", values="Customers", hole=0.52,
            color="Segment", color_discrete_map=colors,
            title="Customer mix by segment",
        )
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.bar(
            counts, x="Segment", y="Customers", color="Segment",
            color_discrete_map=colors, text_auto=",",
            title="Number of customers in each segment",
        )
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Customers")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Key customer metrics")
    a, b, c = st.columns(3)
    a.metric("Average total spend", f"₹{clean['total_spent'].mean():,.0f}")
    b.metric("Average purchases", f"{clean['purchase_count'].mean():.1f}")
    c.metric("Average spend per purchase", f"₹{(clean['total_spent'] / clean['purchase_count']).mean():,.0f}")

    st.info("The dashboard uses the same segmentation rules as the project pipeline. High Value customers are exported to simulated_crm.csv.")

elif page == "Customer Segments":
    st.subheader("Explore customer segments")
    segment_filter = st.multiselect(
        "Choose segment(s)",
        options=segment_order,
        default=segment_order,
    )
    filtered = clean[clean["customer_segment"].isin(segment_filter)].copy()
    if filtered.empty:
        st.info("Select at least one segment.")
        st.stop()

    a, b, c = st.columns(3)
    a.metric("Customers shown", f"{len(filtered):,}")
    b.metric("Mean total spend", f"₹{filtered['total_spent'].mean():,.0f}")
    c.metric("Mean purchase count", f"{filtered['purchase_count'].mean():.1f}")

    left, right = st.columns(2)
    with left:
        fig = px.histogram(
            filtered, x="total_spent", color="customer_segment",
            color_discrete_map=colors, nbins=40, barmode="overlay",
            title="Distribution of total spending",
        )
        fig.update_layout(xaxis_title="Total spent (₹)", yaxis_title="Customers")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig = px.box(
            filtered, x="customer_segment", y="purchase_count",
            color="customer_segment", color_discrete_map=colors,
            category_orders={"customer_segment": segment_order},
            title="Purchase frequency by segment",
        )
        fig.update_layout(xaxis_title="", yaxis_title="Purchase count", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    fig = px.scatter(
        filtered.sample(min(5000, len(filtered)), random_state=42),
        x="purchase_count", y="total_spent", color="customer_segment",
        color_discrete_map=colors, hover_data=["name", "city"],
        title="Spending vs. purchase frequency (up to 5,000 points)",
        opacity=0.65,
    )
    fig.update_layout(xaxis_title="Purchase count", yaxis_title="Total spent (₹)")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Segment summary")
    calculated_summary = (
        clean.groupby("customer_segment")
        .agg(
            customer_count=("customer_id", "count"),
            avg_total_spent=("total_spent", "mean"),
            avg_purchase_count=("purchase_count", "mean"),
        )
        .reindex(segment_order)
        .reset_index()
    )
    calculated_summary["avg_total_spent"] = calculated_summary["avg_total_spent"].round(2)
    calculated_summary["avg_purchase_count"] = calculated_summary["avg_purchase_count"].round(2)
    st.dataframe(calculated_summary, use_container_width=True, hide_index=True)

elif page == "Data Explorer":
    st.subheader("Search and filter customer records")
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        city_options = sorted(clean["city"].dropna().unique().tolist())
        selected_cities = st.multiselect("City", city_options, default=[])
    with f2:
        selected_segments = st.multiselect("Segment", segment_order, default=segment_order)
    with f3:
        min_spend = float(clean["total_spent"].min())
        max_spend = float(clean["total_spent"].max())
        spend_range = st.slider(
            "Total spend range (₹)",
            min_value=float(min_spend),
            max_value=float(max_spend),
            value=(float(min_spend), float(max_spend)),
        )

    view = clean[
        clean["customer_segment"].isin(selected_segments)
        & clean["total_spent"].between(spend_range[0], spend_range[1])
    ].copy()
    if selected_cities:
        view = view[view["city"].isin(selected_cities)]

    st.caption(f"Showing {len(view):,} matching records.")
    cols = ["customer_id", "name", "city", "total_spent", "purchase_count", "customer_segment"]
    st.dataframe(view[cols].head(500), use_container_width=True, hide_index=True)
    st.caption("For performance, the table displays the first 500 matching records.")
    st.download_button(
        "Download filtered records as CSV",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="filtered_customers.csv",
        mime="text/csv",
    )

elif page == "Pipeline & Exports":
    st.subheader("Pipeline status and output files")
    st.write("Re-run the data pipeline whenever you want to regenerate cleaned data, segments, and the CRM export.")
    if st.button("▶ Run pipeline.py", type="primary"):
        with st.spinner("Running cleaning, DuckDB analysis, segmentation, and CRM export..."):
            result = subprocess.run(
                [sys.executable, str(PIPELINE_FILE)],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
            )
        if result.returncode == 0:
            st.success("Pipeline completed successfully.")
            st.code(result.stdout or "Pipeline completed.")
            st.rerun()
        else:
            st.error("Pipeline failed. Check the error output below.")
            st.code(result.stdout + "\n" + result.stderr)

    st.markdown("### Output files")
    files = [
        ("Raw data", RAW_FILE, "Original synthetic data with intentionally dirty records"),
        ("Clean data", CLEAN_FILE, "Validated records used by the analysis"),
        ("Segment summary", SUMMARY_FILE, "Counts and averages by segment"),
        ("Simulated CRM export", CRM_FILE, "Transformed High Value customer records"),
        ("DuckDB database", BASE_DIR / "customers.duckdb", "Local analytical database"),
    ]
    for label, path, description in files:
        exists = path.exists()
        col1, col2, col3 = st.columns([2, 4, 2])
        col1.write(f"**{label}**")
        col2.write(description)
        col3.write("✅ Available" if exists else "— Not generated")

        if exists and path.suffix == ".csv":
            with open(path, "rb") as file:
                st.download_button(
                    f"Download {path.name}",
                    data=file.read(),
                    file_name=path.name,
                    mime="text/csv",
                    key=f"download_{path.name}",
                )

    if not crm.empty:
        st.markdown("### CRM export preview")
        st.write(f"**{len(crm):,}** high-value customer records are ready for simulated CRM import.")
        st.dataframe(crm.head(10), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Demo project • Reverse ETL is simulated through a CRM-ready CSV export; no live CRM is connected.")
