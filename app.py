import io
from datetime import date, datetime
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

st.set_page_config(page_title="UPPCL UNBILLED Report Generator", page_icon="📊", layout="wide")

DIVISION_ORDER = [
    "DUBAGGA", "EUDD_ALAMBAGH", "EUDD_KANPUR_RD",
    "EUDD_VRINDAVAN", "MALIHABAD", "MOHAN LAL GANJ", "NADAR GANJ"
]
LOAD_BANDS = ["GT 50 KW", "10 KW to 49 KW", "5 KW to 9 KW", "LT 5 KW"]

REFERENCE = {
    "Total Unbilled Summary": {
        "DUBAGGA": [20957, 0, 32, 316, 20609],
        "EUDD_ALAMBAGH": [4444, 3, 104, 860, 3477],
        "EUDD_KANPUR_RD": [4967, 0, 66, 770, 4131],
        "EUDD_VRINDAVAN": [7275, 1, 73, 1205, 5996],
        "MALIHABAD": [12088, 1, 12, 50, 12025],
        "MOHAN LAL GANJ": [23961, 2, 51, 155, 23753],
        "NADAR GANJ": [21098, 3, 102, 771, 20222],
    },
    "MRI Unbilled Summary": {
        "DUBAGGA": [107, 0, 23, 84, 0],
        "EUDD_ALAMBAGH": [703, 1, 100, 599, 3],
        "EUDD_KANPUR_RD": [384, 0, 44, 339, 1],
        "EUDD_VRINDAVAN": [759, 0, 64, 683, 12],
        "MALIHABAD": [36, 0, 7, 28, 1],
        "MOHAN LAL GANJ": [114, 1, 42, 64, 7],
        "NADAR GANJ": [308, 2, 80, 223, 3],
    },
    "MD03 (AMISP) Unbilled Summary": {
        "DUBAGGA": [946, 0, 7, 48, 891],
        "EUDD_ALAMBAGH": [228, 0, 4, 60, 164],
        "EUDD_KANPUR_RD": [637, 0, 6, 140, 491],
        "EUDD_VRINDAVAN": [850, 0, 9, 147, 694],
        "MALIHABAD": [499, 1, 5, 8, 485],
        "MOHAN LAL GANJ": [613, 0, 9, 25, 579],
        "NADAR GANJ": [1498, 0, 12, 106, 1380],
    },
    "MD01 (EESL) Unbilled Summary": {
        "DUBAGGA": [1932, 0, 2, 29, 1901],
        "EUDD_ALAMBAGH": [355, 0, 0, 19, 336],
        "EUDD_KANPUR_RD": [949, 0, 16, 146, 787],
        "EUDD_VRINDAVAN": [97, 0, 0, 26, 71],
        "MOHAN LAL GANJ": [1, 0, 0, 0, 1],
        "NADAR GANJ": [1958, 0, 10, 174, 1774],
    },
    "SBM Unbilled Summary": {
        "DUBAGGA": [17972, 0, 0, 155, 17817],
        "EUDD_ALAMBAGH": [3156, 0, 0, 182, 2974],
        "EUDD_KANPUR_RD": [2996, 0, 0, 145, 2851],
        "EUDD_VRINDAVAN": [5568, 0, 0, 349, 5219],
        "MALIHABAD": [11553, 0, 0, 14, 11539],
        "MOHAN LAL GANJ": [23232, 0, 0, 66, 23166],
        "NADAR GANJ": [17332, 0, 0, 267, 17065],
    },
}

def clean_text(s):
    return s.fillna("").astype(str).str.strip()

def read_csv_safely(upload):
    upload.seek(0)
    try:
        return pd.read_csv(upload, dtype=str, low_memory=False)
    except UnicodeDecodeError:
        upload.seek(0)
        return pd.read_csv(upload, dtype=str, low_memory=False, encoding="latin1")

def normalize(df):
    df = df.copy()
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]
    for c in df.columns:
        df[c] = clean_text(df[c])
    for c in ["DIV_NAME", "BILL_CYC_CD", "TARIFF_TYPE", "SUPPLY_TYPE", "PRESYS_CODE", "SANCTION_LOAD_UOM", "LOAD_SLAB", "Connection type"]:
        if c in df.columns:
            df[c] = df[c].str.upper()
    if "SUPPLY_TYPE" in df.columns:
        df["SUPPLY_TYPE"] = df["SUPPLY_TYPE"].str.replace(r"\.0$", "", regex=True)
    return df

def load_band(row, load_col, uom_col):
    uom = str(row.get(uom_col, "KW")).strip().upper() if uom_col else "KW"
    raw = str(row.get(load_col, "")).strip().replace(",", "")
    try:
        load = float(raw)
    except (ValueError, TypeError):
        return "UNKNOWN"
    if uom not in ("KW", ""):
        return "UNKNOWN"
    if load > 50:
        return "GT 50 KW"
    if 10 <= load < 50:
        return "10 KW to 49 KW"
    if 5 <= load < 10:
        return "5 KW to 9 KW"
    if load < 5:
        return "LT 5 KW"
    return "UNKNOWN"

def summarize(frame, division_col, band_col):
    divisions = list(frame[division_col].dropna().astype(str).unique())
    ordered = [d for d in DIVISION_ORDER if d in divisions]
    ordered += sorted([d for d in divisions if d not in ordered])
    rows = []
    for div in ordered:
        sub = frame[frame[division_col] == div]
        vals = [int((sub[band_col] == b).sum()) for b in LOAD_BANDS]
        rows.append([div, int(len(sub)), *vals])
    if rows:
        totals = ["Grand Total"] + [sum(r[i] for r in rows) for i in range(1, 6)]
        rows.append(totals)
    return pd.DataFrame(rows, columns=["Division", "Total", *LOAD_BANDS])

def pdf_bytes(reports, report_date):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=12*mm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("UPPCLTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                                 fontSize=13, leading=16, textColor=colors.white, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("UPPCLSub", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=10, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#1F4E78"))
    story = []
    for idx, (name, table_df) in enumerate(reports.items()):
        if idx:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
        title = Table([[Paragraph("DAILY UNBILLED SUMMARY (excl PTW, Prepaid)", title_style)]], colWidths=[277*mm], rowHeights=[12*mm])
        title.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#1F4E78")),
                                   ("VALIGN",(0,0),(-1,-1),"MIDDLE"), ("BOX",(0,0),(-1,-1),0,colors.white)]))
        story.extend([title, Spacer(1, 4*mm),
                      Paragraph(f"Report Generated On: {report_date.strftime('%d %B %Y')}", styles["Normal"]),
                      Spacer(1, 7*mm), Paragraph(name, subtitle_style), Spacer(1, 5*mm)])
        data = [list(table_df.columns)]
        for _, row in table_df.iterrows():
            data.append([f"{int(v):,}" if isinstance(v, (int, float)) and pd.notna(v) else str(v) for v in row.tolist()])
        widths = [75*mm, 30*mm, 36*mm, 42*mm, 42*mm, 42*mm]
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="CENTER")
        style = [
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#5B9BD5")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8.5),
            ("ALIGN",(1,0),(-1,-1),"CENTER"),
            ("ALIGN",(0,0),(0,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("GRID",(0,0),(-1,-1),0.35,colors.grey),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#D9EAF7")),
            ("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),
            ("LINEABOVE",(0,-1),(-1,-1),1.2,colors.HexColor("#1F4E78")),
        ]
        table.setStyle(TableStyle(style))
        story.append(table)
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(landscape(A4)[0]/2, 6*mm, f"Page {doc.page} of 5")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()

st.title("UPPCL UNBILLED Report Generator")
st.caption("Local CSV upload → validation → five-section PDF and Excel. Data stays in this local app session.")
st.info("Important: the supplied CSV does not contain the existing script's required columns `Connection type` and `LOAD_SLAB`. This app derives load bands from `SANCTION_LOAD` only for KW records. Exact matching to the reference PDF requires validating the original MRI/MD03/MD01/SBM filters; any mismatch is shown, not hidden.")

uploaded = st.file_uploader("Upload UPPCL UNBILLED CSV", type=["csv"])
if not uploaded:
    st.markdown("### What this app generates")
    st.write("A five-section PDF: Total Unbilled, MRI, MD03 (AMISP), MD01 (EESL), and SBM.")
    st.write("Upload a CSV to inspect columns, validate the source data, preview summaries, and download reports.")
    st.stop()

try:
    raw_df = read_csv_safely(uploaded)
    df = normalize(raw_df)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

st.success(f"Loaded {len(df):,} rows and {len(df.columns)} columns.")
with st.expander("Inspect source columns and first 10 rows"):
    st.write(list(df.columns))
    st.dataframe(df.head(10), use_container_width=True)

required = ["DIV_NAME", "BILL_CYC_CD", "TARIFF_TYPE", "SANCTION_LOAD"]
missing = [c for c in required if c not in df.columns]
if missing:
    st.error("Required columns missing: " + ", ".join(missing))
    st.stop()

st.sidebar.header("Report settings")
report_date = st.sidebar.date_input("Report date", value=date.today())
exclude_lmv5 = st.sidebar.checkbox("Exclude TARIFF_TYPE = LMV5", value=True)
exclude_prepaid = st.sidebar.checkbox("Exclude PREPAID if a connection-type column exists", value=True)
exclude_blank_div = st.sidebar.checkbox("Exclude blank division", value=True)
exclude_blank_cycle = st.sidebar.checkbox("Exclude blank billing cycle", value=True)
cycle_col = "BILL_CYC_CD"
div_col = "DIV_NAME"
load_col = "SANCTION_LOAD"
uom_col = "SANCTION_LOAD_UOM" if "SANCTION_LOAD_UOM" in df.columns else None
connection_col = "Connection type" if "Connection type" in df.columns else None

work = df.copy()
before = len(work)
if exclude_lmv5:
    work = work[work["TARIFF_TYPE"] != "LMV5"]
if exclude_prepaid and connection_col:
    work = work[work[connection_col].str.upper() != "PREPAID"]
if exclude_blank_div:
    work = work[work[div_col] != ""]
if exclude_blank_cycle:
    work = work[work[cycle_col] != ""]
work["LOAD_BAND_DERIVED"] = work.apply(lambda r: load_band(r, load_col, uom_col), axis=1)

c1, c2, c3 = st.columns(3)
c1.metric("Uploaded rows", f"{len(df):,}")
c2.metric("Rows after selected filters", f"{len(work):,}")
c3.metric("Excluded rows", f"{before-len(work):,}")

if not connection_col:
    st.warning("`Connection type` is absent from this CSV, so the PREPAID exclusion in the original script cannot be applied. Confirm how prepaid accounts are identified before treating this as an exact business report.")
if "LOAD_SLAB" not in df.columns:
    st.warning("`LOAD_SLAB` is absent. Load bands are derived from `SANCTION_LOAD` where the unit is KW; non-KW and invalid values are marked UNKNOWN.")
unknown_count = int((work["LOAD_BAND_DERIVED"] == "UNKNOWN").sum())
if unknown_count:
    st.warning(f"{unknown_count:,} rows have an unknown load band and are not counted in the four load-band columns. They remain visible in each section's row total; resolve these before production use.")

st.subheader("Choose the report-section rules")
st.write("Default grouping uses `BILL_CYC_CD` for MRI, MD03, MD01 and SBM. These are provisional rules inferred from the sample report headings, not a verified reproduction of the legacy logic.")
section_options = {
    "MRI Unbilled Summary": "MRI",
    "MD03 (AMISP) Unbilled Summary": "MD03",
    "MD01 (EESL) Unbilled Summary": "MD01",
    "SBM Unbilled Summary": "SBM",
}
with st.expander("Advanced: filter section rules", expanded=False):
    st.caption("Select which billing-cycle values to include in each section. Adjust only after confirming the office's established rules.")
    section_cycles = {}
    for section, default_cycle in section_options.items():
        values = sorted(v for v in work[cycle_col].dropna().unique() if v)
        default = [default_cycle] if default_cycle in values else []
        section_cycles[section] = st.multiselect(section, values, default=default, key=f"cycles_{section}")
    total_cycles = st.multiselect(
        "Total Unbilled Summary: included billing-cycle values",
        sorted(v for v in work[cycle_col].dropna().unique() if v),
        default=[v for v in ["MRI", "MD03", "MD01", "SBM"] if v in set(work[cycle_col])],
        key="total_cycles"
    )

def section_frame(frame, cycles=None):
    if cycles is None:
        return frame.copy()
    return frame[frame[cycle_col].isin(cycles)].copy()

reports = {}
total_frame = section_frame(work, total_cycles)
reports["Total Unbilled Summary"] = summarize(total_frame, div_col, "LOAD_BAND_DERIVED")
for section, default_cycle in section_options.items():
    cycles = section_cycles.get(section, [default_cycle])
    reports[section] = summarize(section_frame(work, cycles), div_col, "LOAD_BAND_DERIVED")

st.subheader("Report previews")
for name, table_df in reports.items():
    with st.expander(f"{name} · {int(table_df.iloc[-1]['Total']) if len(table_df) else 0:,} total rows", expanded=(name == "Total Unbilled Summary")):
        st.dataframe(table_df, use_container_width=True, hide_index=True)

st.subheader("Reference validation")
st.caption("Reference totals come from the supplied PDF dated 15 October 2026. Since the CSV's legacy classification rules are not fully represented in the supplied Python script, comparisons are diagnostic only.")
ref_totals = {
    "Total Unbilled Summary": 94790,
    "MRI Unbilled Summary": 2411,
    "MD03 (AMISP) Unbilled Summary": 5271,
    "MD01 (EESL) Unbilled Summary": 5292,
    "SBM Unbilled Summary": 81809,
}
validation_rows = []
for name, tab in reports.items():
    generated = int(tab.iloc[-1]["Total"]) if len(tab) else 0
    ref = ref_totals.get(name)
    validation_rows.append({"Section": name, "Generated total": generated, "PDF reference total": ref, "Difference": (generated-ref) if ref is not None else None, "Status": "MATCH" if ref is not None and generated == ref else "CHECK RULES"})
validation_df = pd.DataFrame(validation_rows)
st.dataframe(validation_df, use_container_width=True, hide_index=True)
if any(r["Status"] != "MATCH" for r in validation_rows):
    st.warning("One or more totals differ from the reference PDF. Do not use the generated output as an exact official report until the section filters, prepaid exclusion, and load-band mapping have been confirmed.")

def excel_bytes(reports, validation):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, table in reports.items():
            table.to_excel(writer, sheet_name=name[:31], index=False)
        validation.to_excel(writer, sheet_name="Validation", index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "B2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = __import__("openpyxl").styles.Font(bold=True, color="FFFFFF")
                cell.fill = __import__("openpyxl").styles.PatternFill("solid", fgColor="1F4E78")
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max((len(str(c.value or "")) for c in col), default=10)
                ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 32)
    return buffer.getvalue()

pdf_report_names = list(reports.keys())
pdf_data = pdf_bytes(reports, report_date)
xlsx_data = excel_bytes(reports, validation_df)
st.download_button("Download five-section PDF", data=pdf_data, file_name=f"UNBILLED_SUMMARY_{report_date:%d-%m-%Y}.pdf", mime="application/pdf", type="primary")
st.download_button("Download Excel workbook", data=xlsx_data, file_name=f"UNBILLED_SUMMARY_{report_date:%d-%m-%Y}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
