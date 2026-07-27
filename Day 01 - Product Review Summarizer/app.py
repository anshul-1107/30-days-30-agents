import streamlit as st
import json
import os
import pandas as pd
import google.generativeai as genai
from google import genai as google_genai

# Import functions and variables from agent.py
import agent

# Configure page settings
st.set_page_config(
    page_title="Product Review Summarizer",
    page_icon="📊",
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
        background: linear-gradient(135deg, #4F46E5 0%, #06B6D4 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
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
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
    }
    
    .sentiment-badge {
        font-size: 1.2rem;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        display: inline-block;
        margin-top: 0.5rem;
    }
    
    .sentiment-positive { background-color: #DCFCE7; color: #15803D; }
    .sentiment-mixed { background-color: #FEF9C3; color: #854D0E; }
    .sentiment-negative { background-color: #FEE2E2; color: #B91C1C; }
    
    .action-card {
        background: linear-gradient(90deg, #EFF6FF 0%, #DBEAFE 100%);
        border-left: 6px solid #2563EB;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }
    
    .theme-card {
        background-color: white;
        border: 1px solid #F1F5F9;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .theme-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    
    .severity-pill {
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        text-transform: uppercase;
        display: inline-block;
        margin-right: 0.5rem;
    }
    .severity-high { background-color: #FEE2E2; color: #991B1B; }
    .severity-medium { background-color: #FEF3C7; color: #92400E; }
    .severity-low { background-color: #F1F5F9; color: #475569; }
    
    .theme-title {
        font-weight: 600;
        font-size: 1.05rem;
        color: #1E293B;
        margin-top: 0.25rem;
    }
    .theme-stats {
        font-size: 0.85rem;
        color: #64748B;
        margin-top: 0.25rem;
    }
    
    .hallucination-warning {
        background-color: #FFFBEB;
        border: 1px solid #FCD34D;
        color: #92400E;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">🛍️ Product Review Summarizer</h1>
        <p class="header-subtitle">AI-powered eCommerce review intelligence briefing with Python-verified analysis</p>
    </div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.header("🛠️ Settings")

# API Key handling
default_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
api_key_input = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    value=default_api_key,
    help="Enter your Gemini API key. Defaults to system configuration if not changed."
)

# Overwrite agent client with input key if changed
if api_key_input:
    agent.client = google_genai.Client(api_key=api_key_input)

# Model Selection
model_choice = st.sidebar.selectbox(
    "LLM Model",
    ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)
agent.MODEL = model_choice

# File uploader
uploaded_file = st.sidebar.file_uploader("Upload Product Reviews JSON", type=["json"])

# Default dataset option
use_default = st.sidebar.checkbox("Use Sample Reviews (AeroPods X2)", value=True if not uploaded_file else False)

# Load review data
reviews_data = None
if uploaded_file is not None:
    try:
        # Reset file pointer to read from beginning in case Streamlit re-runs
        uploaded_file.seek(0)
        reviews_data = json.load(uploaded_file)
        st.sidebar.success("✅ Custom reviews file uploaded successfully!")
    except Exception as e:
        st.sidebar.error(f"❌ Error loading JSON: {e}")
elif use_default:
    # Read reviews.json from project folder
    try:
        with open("reviews.json") as f:
            reviews_data = json.load(f)
    except FileNotFoundError:
        st.error("Default reviews.json not found in workspace.")

if reviews_data:
    # Normalize reviews_data if it is a list or structured differently
    if isinstance(reviews_data, list):
        reviews_data = {
            "product": "Uploaded Reviews Dataset",
            "reviews": reviews_data
        }
    elif isinstance(reviews_data, dict):
        if "reviews" not in reviews_data:
            # If reviews key is missing but product key is present
            if "product" in reviews_data:
                reviews_data["reviews"] = []
            else:
                # If it's a dictionary representing a single review or other key-value structure
                reviews_data = {
                    "product": "Uploaded Product",
                    "reviews": [reviews_data]
                }
        if "product" not in reviews_data:
            reviews_data["product"] = "Uploaded Product"

    # Normalize each review item to ensure it has id, rating, and text
    raw_reviews = reviews_data.get("reviews", [])
    if not isinstance(raw_reviews, list):
        raw_reviews = []
        
    normalized_reviews = []
    for idx, r in enumerate(raw_reviews):
        if not isinstance(r, dict):
            continue
        
        # 1. Determine ID with sequential fallback
        rid = r.get("id") or r.get("review_id") or r.get("ID") or f"R{idx+1:03d}"
        
        # 2. Determine rating (convert to int)
        rating_val = r.get("rating") or r.get("stars") or r.get("score") or r.get("rating_value") or 5
        try:
            rating = int(float(rating_val))
        except (ValueError, TypeError):
            rating = 5
            
        # 3. Determine text
        text = r.get("text") or r.get("review") or r.get("comment") or r.get("body") or r.get("text_content") or ""
        
        normalized_reviews.append({
            "id": str(rid),
            "rating": rating,
            "text": str(text)
        })
        
    reviews_data["reviews"] = normalized_reviews

    # Main Dashboard Page
    st.subheader(f"📦 Product: {reviews_data.get('product', 'Unknown Product')}")
    
    # Grid summary layout
    reviews = reviews_data.get("reviews", [])
    total_reviews = len(reviews)
    ratings = [r["rating"] for r in reviews]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: #64748B; font-weight: 500;">Total Reviews</div>
                <div style="font-size: 2.2rem; font-weight: 700; color: #0F172A; margin: 0.5rem 0;">{total_reviews}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: #64748B; font-weight: 500;">Average Rating</div>
                <div style="font-size: 2.2rem; font-weight: 700; color: #0F172A; margin: 0.5rem 0;">{avg_rating:.2f} ★</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        # Create Rating Distribution
        rating_counts = {i: ratings.count(i) for i in range(1, 6)}
        # Custom mini bar chart in col3
        chart_data = pd.DataFrame({
            "Rating": [f"{i}★" for i in range(1, 6)],
            "Count": [rating_counts[i] for i in range(1, 6)]
        })
        st.markdown(f"""
            <div class="metric-card" style="padding-bottom: 0.5rem;">
                <div style="font-size: 0.9rem; color: #64748B; font-weight: 500; margin-bottom: 0.25rem;">Rating Distribution</div>
            </div>
        """, unsafe_allow_html=True)
        # Display small bar chart
        st.bar_chart(chart_data.set_index("Rating"), height=100)

    # Accordion for Raw Reviews List
    with st.expander("📝 View Raw Reviews List"):
        df = pd.DataFrame(reviews)
        st.dataframe(df, use_container_width=True)

    # Summarize Button
    st.markdown("---")
    if st.button("🚀 Generate Intelligence Briefing", type="primary", use_container_width=True):
        with st.spinner("Analyzing reviews using Gemini and running verification script..."):
            try:
                # 1. Summarize
                raw_summary = agent.summarize(reviews_data)
                
                # 2. Verify
                verified_result = agent.verify(raw_summary, reviews_data)
                
                st.success("✅ Analysis completed and verified by python script!")
                
                # Display Results
                meta = verified_result["_meta"]
                
                # Sentiment Display
                sentiment = verified_result.get("overall_sentiment", "mixed").lower()
                sentiment_class = f"sentiment-{sentiment}"
                
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.5rem;">
                        <span style="font-size: 1.3rem; font-weight: 600; color: #1E293B;">Overall Sentiment:</span>
                        <span class="sentiment-badge {sentiment_class}">{sentiment.upper()}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Recommended Action Display
                action = verified_result.get("recommended_action", "No action specified.")
                st.markdown(f"""
                    <div class="action-card">
                        <h4 style="margin: 0 0 0.5rem 0; color: #1E40AF; font-size: 1.15rem; font-weight: 600;">💡 Recommended Action</h4>
                        <p style="margin: 0; color: #1E3A8A; font-size: 1rem; line-height: 1.5;">{action}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Issues & Strengths Columns
                col_issues, col_strengths = st.columns(2)
                
                with col_issues:
                    st.markdown("### ⚠️ Customer Issues")
                    
                    product_issues = verified_result.get("product_issues", [])
                    fulfilment_issues = verified_result.get("fulfilment_issues", [])
                    
                    if not product_issues and not fulfilment_issues:
                        st.info("No significant issues detected.")
                    
                    if product_issues:
                        st.markdown("#### Product Issues")
                        for t in product_issues:
                            sev = t.get("severity", "medium").lower()
                            st.markdown(f"""
                                <div class="theme-card">
                                    <div>
                                        <span class="severity-pill severity-{sev}">{sev}</span>
                                        <span class="theme-title">{t['theme']}</span>
                                    </div>
                                    <div class="theme-stats">
                                        👥 <b>{t['count']} reviews</b> ({t['pct']}%) • Citations: <i>{', '.join(t['review_ids'])}</i>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                    if fulfilment_issues:
                        st.markdown("#### Fulfilment Issues")
                        for t in fulfilment_issues:
                            sev = t.get("severity", "medium").lower()
                            st.markdown(f"""
                                <div class="theme-card">
                                    <div>
                                        <span class="severity-pill severity-{sev}">{sev}</span>
                                        <span class="theme-title">{t['theme']}</span>
                                    </div>
                                    <div class="theme-stats">
                                        👥 <b>{t['count']} reviews</b> ({t['pct']}%) • Citations: <i>{', '.join(t['review_ids'])}</i>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                with col_strengths:
                    st.markdown("### ✨ Product Strengths")
                    strengths = verified_result.get("strengths", [])
                    
                    if not strengths:
                        st.info("No major strengths identified.")
                    else:
                        for t in strengths:
                            st.markdown(f"""
                                <div class="theme-card" style="border-left: 5px solid #10B981;">
                                    <div class="theme-title" style="color: #065F46;">👍 {t['theme']}</div>
                                    <div class="theme-stats">
                                        👥 <b>{t['count']} reviews</b> ({t['pct']}%) • Citations: <i>{', '.join(t['review_ids'])}</i>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                
                # Hallucinated IDs Warning
                if meta.get("hallucinated_ids"):
                    st.markdown("---")
                    st.markdown("""
                        <div class="hallucination-warning">
                            <h4 style="margin: 0 0 0.5rem 0; font-weight: 600;">⚠️ Verification Notice: Hallucinated Citations Detected</h4>
                            <p style="margin: 0; font-size: 0.95rem; line-height: 1.5;">
                                The AI cited review IDs that do not exist in the source dataset. The Python verification layer successfully flagged and filtered out these hallucinated citations:
                            </p>
                            <ul style="margin-top: 0.5rem; margin-bottom: 0;">
                    """, unsafe_allow_html=True)
                    for theme, bad in meta["hallucinated_ids"]:
                        st.markdown(f"<li><b>{theme}</b>: cited invalid IDs {bad}</li>", unsafe_allow_html=True)
                    st.markdown("""
                            </ul>
                        </div>
                    """, unsafe_allow_html=True)
                    
            except Exception as e:
                st.error(f"An error occurred during summarization: {e}")
                st.exception(e)
else:
    st.info("Please upload a product reviews JSON file or check 'Use Sample Reviews' in the sidebar to get started.")
