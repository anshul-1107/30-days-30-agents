import streamlit as st
import json
import os
import pandas as pd
from decimal import Decimal
from google import genai as google_genai

# Import agent and schema functions
import agent
from schema import PurchaseOrder

# Configure page settings
st.set_page_config(
    page_title="Validated Purchase Order Extractor",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global Font override */
    html, body, [class*="css"], .stText, .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Header Gradient */
    .header-container {
        background: linear-gradient(135deg, #1E1B4B 0%, #4338CA 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px rgba(67, 56, 202, 0.15);
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .header-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
        font-weight: 300;
    }
    
    /* Card Styles */
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
    }
    
    .status-badge {
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        display: inline-block;
    }
    
    .status-success { background-color: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
    .status-skipped { background-color: #F1F5F9; color: #475569; border: 1px solid #E2E8F0; }
    .status-failed { background-color: #FEE2E2; color: #B91C1C; border: 1px solid #FCA5A5; }
    
    .self-correct-badge {
        background-color: #FEF9C3;
        color: #854D0E;
        border: 1px solid #FEF08A;
        font-size: 0.8rem;
        font-weight: 500;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        display: inline-block;
        margin-left: 0.5rem;
    }
    
    .po-container {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }
    
    .po-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .mismatch-card {
        background: linear-gradient(90deg, #FFFBEB 0%, #FEF3C7 100%);
        border-left: 6px solid #D97706;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        color: #92400E;
    }
    
    .ambiguity-item {
        background-color: #FFF5F5;
        border-left: 3px solid #FEB2B2;
        padding: 0.5rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 4px;
        font-size: 0.9rem;
        color: #C53030;
    }
    </style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">📥 Validated Purchase Order Extractor</h1>
        <p class="header-subtitle">AI-powered document processing pipeline with schema enforcement, self-correction retry loops, and arithmetic reconciliation.</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("⚙️ Configuration")

# API Key handling
default_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
api_key_input = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    value=default_api_key,
    help="Enter your Gemini API key. Defaults to system configuration if not changed."
)

if api_key_input:
    agent.client = google_genai.Client(api_key=api_key_input)

# Model Selection
model_choice = st.sidebar.selectbox(
    "LLM Model",
    ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)
agent.MODEL = model_choice

# File uploader
uploaded_file = st.sidebar.file_uploader("Upload Emails Dataset (JSON)", type=["json"])
use_default = st.sidebar.checkbox("Use Sample Dataset (emails.json)", value=True if not uploaded_file else False)

# Load data
emails_data = None
if uploaded_file is not None:
    try:
        uploaded_file.seek(0)
        emails_data = json.load(uploaded_file)
        st.sidebar.success("✅ Dataset loaded successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading JSON: {e}")
elif use_default:
    try:
        with open("emails.json") as f:
            emails_data = json.load(f)
    except FileNotFoundError:
        st.error("Default emails.json not found in workspace.")

if emails_data:
    st.subheader(f"📂 Loaded Dataset: {len(emails_data)} email(s)")
    
    # Process Button
    if st.button("🚀 Process Emails and Extract Purchase Orders", type="primary", use_container_width=True):
        st.markdown("---")
        with st.spinner("Processing pipeline active... running schema-forced extraction and verification layers..."):
            for idx, email in enumerate(emails_data):
                try:
                    po, log = agent.extract(email)
                except Exception as e:
                    po = None
                    log = [f"API Call Failed: {e}"]
                
                # Render email block
                status_class = "status-success"
                status_text = "Extracted Successfully"
                
                if po is None:
                    status_class = "status-failed"
                    status_text = "Extraction Failed"
                elif not po.is_purchase_order:
                    status_class = "status-skipped"
                    status_text = "Not a Purchase Order"
                
                # Email metadata header
                st.markdown(f"""
                    <div class="po-container">
                        <div class="po-header">
                            <div>
                                <span style="font-size: 1.25rem; font-weight: 600; color: #1E293B;">{email['id']} | {email['subject'][:55]}</span>
                                {f'<span class="self-correct-badge">🔄 Self-Corrected: {", ".join(log)}</span>' if log and po else ''}
                            </div>
                            <span class="status-badge {status_class}">{status_text}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Create split UI layout within container
                with st.expander("📬 View Raw Email Metadata & Content"):
                    st.markdown(f"**Received Date**: `{email['received']}`")
                    st.markdown(f"**Subject**: `{email['subject']}`")
                    st.text_area(label="Email Body", value=email['body'], height=150, disabled=True, key=f"body_{idx}")
                
                if po and po.is_purchase_order:
                    # Metrics Row
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"**Supplier Name**:  \n`{po.supplier_name or '— None —'}`")
                    with col2:
                        st.markdown(f"**PO Number**:  \n`{po.po_number or '— None stated —'}`")
                    with col3:
                        st.markdown(f"**Order Date**:  \n`{po.order_date or '— None —'}`")
                    with col4:
                        st.markdown(f"**Expected Delivery**:  \n`{po.expected_delivery or '— None —'}`")
                    
                    # Line items
                    st.markdown("##### 🛒 Extracted Line Items")
                    items_list = []
                    for i in po.line_items:
                        subtotal = None
                        if i.unit_price is not None:
                            subtotal = Decimal(i.quantity) * i.unit_price
                        items_list.append({
                            "SKU": i.sku or "— None stated —",
                            "Description": i.description,
                            "Quantity": i.quantity,
                            "Unit Price": f"{po.currency} {i.unit_price:,}" if i.unit_price else "—",
                            "Subtotal": f"{po.currency} {subtotal:,}" if subtotal else "—"
                        })
                    
                    df_items = pd.DataFrame(items_list)
                    st.dataframe(df_items, use_container_width=True, hide_index=True)
                    
                    # Cross-check details
                    check = agent.cross_check(po)
                    
                    col_total1, col_total2 = st.columns(2)
                    with col_total1:
                        st.markdown(f"**Stated Total (Email)**: `{po.currency} {po.stated_total:,.2f}`" if po.stated_total is not None else "**Stated Total (Email)**: `— None stated —`")
                    with col_total2:
                        if check.get("computed_total") is not None:
                            st.markdown(f"**Computed Total (Items Sum)**: `{po.currency} {check['computed_total']:,.2f}`")
                    
                    if check.get("mismatch"):
                        st.markdown(f"""
                            <div class="mismatch-card">
                                <b>⚠️ Price Discrepancy Detected!</b><br/>
                                The stated total in the email ({po.currency} {check['stated_total']:,}) 
                                does not match the sum of line items ({po.currency} {check['computed_total']:,}). 
                                <b>Difference: {po.currency} {check['delta']:,}</b>. Held for manual validation.
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Ambiguities
                    if po.ambiguities:
                        st.markdown("##### ❓ Flagged Ambiguities")
                        for a in po.ambiguities:
                            st.markdown(f'<div class="ambiguity-item">❓ {a}</div>', unsafe_allow_html=True)
                
                elif po is None and log:
                    st.error(f"Failed extraction after {agent.MAX_ATTEMPTS} attempts. Logs: {log}")
                    
                st.markdown("<br/>", unsafe_allow_html=True)
else:
    st.info("Upload a dataset or enable the sample dataset checkbox to load emails.")
