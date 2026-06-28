~"""
ui_app.py
Streamlit web UI for the AI OCR Pipeline
Display receipt processing results with interactive dashboard
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
from main import run

# Configure page
st.set_page_config(
    page_title="OCR Pipeline Dashboard",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .confidence-high { color: #2ecc71; font-weight: bold; }
    .confidence-low { color: #e74c3c; font-weight: bold; }
    .confidence-medium { color: #f39c12; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

def load_json(path):
    """Load JSON file safely"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading {path}: {e}")
        return None

def get_confidence_color(confidence):
    """Return color based on confidence level"""
    if confidence is None:
        return "secondary"
    elif confidence >= 0.85:
        return "success"
    elif confidence >= 0.70:
        return "warning"
    else:
        return "danger"

def format_currency(amount):
    """Format amount as currency"""
    if isinstance(amount, (int, float)):
        return f"${amount:.2f}"
    return str(amount)

def main():
    st.title("📋 OCR Pipeline Dashboard")
    st.markdown("---")
    
    # Sidebar controls
    with st.sidebar:
        st.header("Controls")
        
        # Input/Output paths
        input_dir = st.text_input(
            "Input Folder (receipts)",
            value="data/receipts",
            help="Folder containing receipt images"
        )
        
        output_dir = st.text_input(
            "Output Folder",
            value="output",
            help="Folder where results will be saved"
        )
        
        st.markdown("---")
        
        # Process button
        if st.button("🔄 Process Receipts", key="process_btn", use_container_width=True):
            with st.spinner("Processing receipts..."):
                try:
                    result = run(input_dir, output_dir)
                    st.success("✓ Processing complete!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        # Upload new receipt
        st.markdown("---")
        st.subheader("Upload Receipt")
        uploaded_file = st.file_uploader(
            "Upload a receipt image",
            type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
            help="Upload a single receipt image to process"
        )
        
        if uploaded_file:
            # Save and process uploaded file
            receipt_dir = Path(input_dir)
            receipt_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = receipt_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✓ Saved {uploaded_file.name}")
            
            if st.button("Process This Receipt", use_container_width=True):
                with st.spinner("Processing uploaded receipt..."):
                    try:
                        result = run(str(receipt_dir), output_dir)
                        st.success("✓ Receipt processed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    
    # Main content
    output_path = Path(output_dir)
    summary_path = output_path / "financial_summary.json"
    all_results_path = output_path / "all_results.json"
    receipts_dir = output_path / "receipts"
    
    # Check if data exists
    if not summary_path.exists():
        st.info("📌 No processed receipts found. Click 'Process Receipts' in the sidebar to get started!")
        return
    
    # Load data
    summary = load_json(summary_path)
    all_results = load_json(all_results_path)
    
    if not summary:
        st.error("Failed to load summary data")
        return
    
    # Financial Summary Section
    st.header("💰 Financial Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Spend",
            format_currency(summary.get("total_spend", 0)),
            delta=None
        )
    
    with col2:
        st.metric(
            "Transactions",
            summary.get("num_transactions", 0),
            delta=None
        )
    
    with col3:
        avg_spend = (
            summary.get("total_spend", 0) / max(summary.get("num_transactions", 1), 1)
        )
        st.metric(
            "Average per Receipt",
            format_currency(avg_spend),
            delta=None
        )
    
    # Spend per store
    if summary.get("spend_per_store"):
        st.subheader("Spending by Store")
        
        store_data = summary["spend_per_store"]
        
        # Bar chart
        col1, col2 = st.columns(2)
        
        with col1:
            df = pd.DataFrame(
                list(store_data.items()),
                columns=["Store", "Amount"]
            )
            st.bar_chart(df.set_index("Store"))
        
        with col2:
            # Table
            df_display = df.copy()
            df_display["Amount"] = df_display["Amount"].apply(format_currency)
            st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    # Failed files
    if summary.get("failed_files"):
        st.warning(f"⚠️ {len(summary['failed_files'])} files failed to process")
        with st.expander("View failed files"):
            for failed in summary["failed_files"]:
                st.text(failed)
    
    st.markdown("---")
    
    # Individual Receipts Section
    st.header("📄 Receipt Details")
    
    if all_results and "receipts" in all_results:
        receipts = all_results["receipts"]
        
        # Filter tabs
        tab_all, tab_success, tab_failed = st.tabs(
            [f"All ({len(receipts)})", 
             f"Successful ({len([r for r in receipts if 'error' not in r])})",
             f"Failed ({len([r for r in receipts if 'error' in r])}))"]
        )
        
        with tab_all:
            for idx, receipt in enumerate(receipts):
                _display_receipt_card(receipt, idx, receipts_dir)
        
        with tab_success:
            for idx, receipt in enumerate([r for r in receipts if "error" not in r]):
                _display_receipt_card(receipt, idx, receipts_dir)
        
        with tab_failed:
            failed_receipts = [r for r in receipts if "error" in r]
            if failed_receipts:
                for receipt in failed_receipts:
                    st.error(f"❌ {receipt.get('file', 'Unknown')}: {receipt.get('error', 'Unknown error')}")
            else:
                st.info("All receipts processed successfully!")
    
    # Metadata
    st.markdown("---")
    with st.expander("📊 Raw Data"):
        st.json(summary)

def _display_receipt_card(receipt, idx, receipts_dir):
    """Display individual receipt card"""
    
    if "error" in receipt:
        st.error(f"❌ {receipt['file']}: {receipt['error']}")
        return
    
    with st.expander(f"📋 {receipt.get('file', f'Receipt {idx}')}"):
        # Organized layout
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Extracted Data")
            structured = receipt.get("structured", {})
            
            # Display key fields
            if structured:
                for key, value in structured.items():
                    st.write(f"**{key}:** `{value}`")
            else:
                st.info("No structured data extracted")
        
        with col2:
            st.subheader("Confidence Scores")
            confidence_output = receipt.get("confidence_output", {})
            
            if confidence_output:
                confidence_data = []
                for field, data in confidence_output.items():
                    if isinstance(data, dict):
                        conf = data.get("confidence", "N/A")
                        value = data.get("value", "N/A")
                        flag = "🚩" if isinstance(conf, (int, float)) and conf < 0.70 else "✓"
                        confidence_data.append({
                            "Field": f"{flag} {field}",
                            "Confidence": f"{conf:.2%}" if isinstance(conf, (int, float)) else conf,
                            "Value": str(value)[:30]
                        })
                
                if confidence_data:
                    df = pd.DataFrame(confidence_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No confidence data available")
        
        # Raw text preview
        with st.expander("Raw OCR Text"):
            raw_text = receipt.get("raw_text", "")
            st.text(raw_text[:500] + ("..." if len(raw_text) > 500 else ""))
        
        # Full JSON view
        with st.expander("Full JSON"):
            st.json(receipt)

if __name__ == "__main__":
    main()
