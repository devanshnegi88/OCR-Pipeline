## Running the UI

The OCR Pipeline now includes a **web-based dashboard** built with Streamlit!

### Installation

First, install the updated dependencies:

```bash
pip install -r requirements.txt
```

### Start the Dashboard

Navigate to the project directory and run:

```bash
streamlit run ui_app.py
```

This will:
- Open a browser window automatically at `http://localhost:8501`
- Display a beautiful dashboard with your receipt data

### Features

**Dashboard:**
- 📊 Financial summary with total spend & metrics
- 💰 Spending breakdown by store (bar chart + table)
- 📊 Transaction count and average receipts

**Receipt Management:**
- 📋 View all processed receipts with details
- ✓ Filter by successful/failed receipts  
- 📄 Expandable receipt cards showing:
  - Extracted structured data
  - Confidence scores (flagged if < 70%)
  - Raw OCR text preview
  - Full JSON data

**Processing:**
- 🔄 Process button to run full pipeline from sidebar
- 📤 Upload new receipt images directly in the UI
- 🔍 Automatic processing after upload

### Workflow

1. **Start**: Run `streamlit run ui_app.py`
2. **Process**: Click "🔄 Process Receipts" to process all images in `data/receipts/`
3. **View**: Browse results in the dashboard
4. **Upload**: Add new receipts via the sidebar uploader
5. **Analyze**: Check financial summary and individual receipt details

### Customization

- Edit `ui_app.py` to customize colors, layout, or metrics
- Change input/output paths in the sidebar at runtime
- Add new charts or analytics as needed

### Tips

- Results are cached in the `output/` folder
- Use keyboard shortcut `C` to clear Streamlit cache if needed
- Use `--logger.level=debug` flag for verbose logging: `streamlit run ui_app.py --logger.level=debug`

Enjoy! 🎉
