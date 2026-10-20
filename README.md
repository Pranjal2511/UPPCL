# UPPCL CSV Report Generator (local Streamlit app)

## What it does
- Upload a CSV in the browser.
- Validates required columns and displays row counts.
- Applies the legacy script's `TARIFF_TYPE != LMV5`, non-empty division and non-empty billing-cycle filters by default.
- If a `Connection type` column exists, can exclude `PREPAID`.
- Derives load bands from `SANCTION_LOAD` for rows whose unit is KW.
- Builds five sections and exports PDF and Excel.
- Compares generated section totals against the reference PDF totals.

## Important accuracy note
The supplied `UNBILLED.csv` has 33 columns and does **not** include `Connection type` or `LOAD_SLAB`, although the supplied legacy script requires both. The section filters in the reference PDF are not fully recoverable from that script alone. Therefore this app labels the section grouping as provisional and flags mismatches against the reference totals. Do not treat it as an exact official report until the missing prepaid and section-classification rules are confirmed against the original production script/data.

The sample PDF's four section totals (MRI, MD03, MD01, SBM) add up to 94,783, while its Total Unbilled section says 94,790. This 7-row difference is preserved as a validation issue, not silently reconciled.

## Windows setup
1. Extract this ZIP to a folder, for example `D:\uppcl\uppcl_csv_report_generator`.
2. Open that folder in VS Code.
3. In VS Code, choose Terminal > New Terminal.
4. Run:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```bat
   python -m streamlit run app.py
   ```
6. Streamlit will show a local URL, usually `http://localhost:8501`. Open it in your browser.
7. Upload the CSV and review the validation panel before downloading reports.

## Data privacy
The app runs locally. Keep the terminal open while using it. Do not expose port 8501 to the public internet or upload consumer data to public hosting. Treat source CSV files and generated reports as confidential.
"# UPPCL" 
