import json
import os
import sys
import importlib
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Page Configuration for modern premium feel
st.set_page_config(
    page_title="AI Support Ticket Router Portal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium design (fonts, cards, glassmorphism, glowing badges)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

/* Main font and styling */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Glassmorphic card styling */
.ticket-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 20px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(8px);
    transition: all 0.3s ease;
}

.ticket-card:hover {
    border-color: rgba(255, 255, 255, 0.25);
    transform: translateY(-2px);
    box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.3);
}

/* Color-coded glowing badges for actions */
.badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

.badge-auto {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.4);
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}

.badge-confirm {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.4);
    box-shadow: 0 0 12px rgba(245, 158, 11, 0.2);
}

.badge-human {
    background: rgba(107, 114, 128, 0.15);
    color: #9ca3af;
    border: 1px solid rgba(107, 114, 128, 0.4);
}

.badge-escalate {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.5);
    box-shadow: 0 0 15px rgba(239, 68, 68, 0.45);
    animation: pulse 2.5s infinite;
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
    70% { box-shadow: 0 0 0 12px rgba(239, 68, 68, 0); }
    100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

/* Metric card styling */
.metric-box {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.metric-value {
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 4px;
}

.metric-label {
    font-size: 0.9rem;
    color: #a1a1aa;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Channel badge */
.channel-badge {
    background: rgba(255, 255, 255, 0.08);
    color: #e4e4e7;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# Dynamic import of agent.py
agent_module = importlib.import_module("agent")
importlib.reload(agent_module)
classify = agent_module.classify
Classification = agent_module.Classification
Category = agent_module.Category

# Local Custom routing function accepting dynamic thresholds
def route_dynamic(c: Classification, auto_route_min: float, review_band_min: float) -> dict:
    if c.urgency >= 5:
        return {
            "action": "ESCALATE — urgent human",
            "badge_class": "badge-escalate",
            "queue": "priority",
            "reason": "high stakes regardless of category"
        }
    if c.confidence >= auto_route_min:
        return {
            "action": "auto-route",
            "badge_class": "badge-auto",
            "queue": c.primary.value,
            "reason": "confident"
        }
    if c.confidence >= review_band_min:
        return {
            "action": "human confirms suggested route",
            "badge_class": "badge-confirm",
            "queue": c.primary.value,
            "reason": "moderate confidence"
        }
    return {
        "action": "human triage from scratch",
        "badge_class": "badge-human",
        "queue": "unrouted",
        "reason": "low confidence — model abstained"
    }

# ----------------- SIDEBAR -----------------
st.sidebar.markdown(
    "<h1 style='text-align: center; color: #6366f1; margin-bottom: 0;'>🤖 Router Ops</h1>", 
    unsafe_allow_html=True
)
st.sidebar.markdown(
    "<p style='text-align: center; color: #a1a1aa; font-size: 0.9rem; margin-top: 0; margin-bottom: 25px;'>Day 3: Calibrated Routing Sim</p>", 
    unsafe_allow_html=True
)

st.sidebar.markdown("### ⚙️ Decision Thresholds")
auto_route_min = st.sidebar.slider(
    "Auto-Route Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.75,
    step=0.05,
    help="Tickets at or above this confidence score will route automatically without human intervention."
)

review_band_min = st.sidebar.slider(
    "Human Review Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.45,
    step=0.05,
    help="Tickets with confidence between this and Auto-Route will suggest routing for a human to confirm."
)

if review_band_min > auto_route_min:
    st.sidebar.warning("Note: Review threshold is higher than Auto-route. Review band is deactivated.")

st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Routing Policy Rules")
st.sidebar.markdown(r"""
- **Urgency Override**: Urgency $\ge$ 5 bypasses all confidence gates and escalates straight to humans.
- **Auto-route**: $\ge$ Auto-Route Threshold. High deflection, low touch.
- **Suggested Review**: Between Human Review & Auto-Route.
- **Scratch Triage**: $<$ Human Review. Model abstains due to low confidence.
""")

# ----------------- MAIN INTERFACE -----------------
st.markdown("<h1 style='margin-bottom: 0px;'>🤖 Calibrated Support Ticket Router</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 1.1rem; color: #8e94a0; margin-top: 5px; margin-bottom: 25px;'>Leverage Gemini 2.5 Flash to classify customer support queries, estimate confidence, and intelligently queue tasks based on calibrated risk boundaries.</p>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Batch Analysis & Simulation", "🎯 Try Custom Ticket"])

# Load batch tickets helper
def load_default_tickets():
    tickets_path = "tickets.json"
    if os.path.exists(tickets_path):
        with open(tickets_path) as f:
            return json.load(f)
    return []

# Initialize Session State for cached model calls
if "batch_classifications" not in st.session_state:
    st.session_state["batch_classifications"] = None
if "batch_tickets" not in st.session_state:
    st.session_state["batch_tickets"] = load_default_tickets()

# Tab 1: Batch Dashboard & Simulator
with tab1:
    col_ctrl, col_space = st.columns([2, 5])
    with col_ctrl:
        run_batch = st.button("🚀 Process Batch (Gemini API)", use_container_width=True)
    
    if run_batch:
        if not st.session_state["batch_tickets"]:
            st.error("No `tickets.json` found in workspace.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            classifications = []
            tickets = st.session_state["batch_tickets"]
            
            for idx, t in enumerate(tickets):
                status_text.text(f"Triaging ticket {idx+1}/{len(tickets)} (ID: {t['id']})...")
                # Run the model (which handles retries/rate-limits internally)
                try:
                    c = classify(t)
                    classifications.append(c)
                except Exception as e:
                    st.error(f"Error classifying {t['id']}: {e}")
                    break
                progress_bar.progress((idx + 1) / len(tickets))
            
            status_text.empty()
            progress_bar.empty()
            if len(classifications) == len(tickets):
                st.session_state["batch_classifications"] = classifications
                st.success("Successfully triaged entire batch using Gemini API!")

    # Render dashboard if batch classifications are ready
    if st.session_state["batch_classifications"] is not None:
        tickets = st.session_state["batch_tickets"]
        classifications = st.session_state["batch_classifications"]
        
        # Apply current slider thresholds instantly
        routed_results = []
        for t, c in zip(tickets, classifications):
            r = route_dynamic(c, auto_route_min, review_band_min)
            routed_results.append({
                "id": t["id"],
                "channel": t["channel"],
                "text": t["text"],
                "primary": c.primary.value,
                "secondary": [s.value for s in c.secondary],
                "confidence": c.confidence,
                "urgency": c.urgency,
                "reasoning": c.reasoning,
                "action": r["action"],
                "badge_class": r["badge_class"],
                "queue": r["queue"],
                "reason": r["reason"]
            })
            
        df = pd.DataFrame(routed_results)
        
        # Calculate dashboard metrics
        total = len(df)
        auto_count = sum(df["action"] == "auto-route")
        review_count = sum(df["action"] == "human confirms suggested route")
        human_scratch = sum(df["action"] == "human triage from scratch")
        escalate_count = sum(df["action"] == "ESCALATE — urgent human")
        
        deflection_pct = round(100 * auto_count / total) if total > 0 else 0
        avg_confidence = df["confidence"].mean()
        avg_urgency = df["urgency"].mean()
        
        # Metric display row
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value" style="color: #10b981;">{deflection_pct}%</div>
                <div class="metric-label">Deflection Rate</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{auto_count}</div>
                <div class="metric-label">Auto-Routed</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{review_count + human_scratch}</div>
                <div class="metric-label">Human Review / Triage</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value" style="color: #ef4444;">{escalate_count}</div>
                <div class="metric-label">Urgent Escapes</div>
            </div>
            """, unsafe_allow_html=True)
        with m5:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value">{avg_confidence:.2f}</div>
                <div class="metric-label">Avg Confidence</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Charts row
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("### 📂 Ticket Categories")
            cat_counts = df["primary"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig_cat = px.bar(
                cat_counts, 
                x="Count", 
                y="Category", 
                orientation="h",
                color="Category",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                template="plotly_dark"
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
                height=250
            )
            st.plotly_chart(fig_cat, use_container_width=True)
            
        with chart_col2:
            st.markdown("### 🚦 Action Routing Outcomes")
            action_counts = df["action"].value_counts().reset_index()
            action_counts.columns = ["Action", "Count"]
            
            # Map clean colors to actions
            color_map = {
                "auto-route": "#10b981",
                "human confirms suggested route": "#f59e0b",
                "human triage from scratch": "#9ca3af",
                "ESCALATE — urgent human": "#ef4444"
            }
            fig_action = px.pie(
                action_counts,
                values="Count",
                names="Action",
                color="Action",
                color_discrete_map=color_map,
                hole=0.4,
                template="plotly_dark"
            )
            fig_action.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                height=250,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_action, use_container_width=True)

        st.markdown("<br><h3>📋 Detailed Queue Router Log</h3>", unsafe_allow_html=True)
        
        # Queue Filtering
        queue_filter = st.multiselect(
            "Filter log by Routing Action",
            options=df["action"].unique(),
            default=df["action"].unique()
        )
        
        filtered_df = df[df["action"].isin(queue_filter)]
        
        # Display logs as custom elegant panels
        for index, row in filtered_df.iterrows():
            secondaries = f" | Also: {', '.join(row['secondary'])}" if row['secondary'] else ""
            
            # Visual progress indicators
            conf_bar = f"""
            <div style="background: rgba(255,255,255,0.1); border-radius: 99px; height: 6px; width: 100%; margin-top: 4px;">
                <div style="background: #6366f1; border-radius: 99px; height: 100%; width: {int(row['confidence'] * 100)}%;"></div>
            </div>
            """
            
            st.markdown(f"""
            <div class="ticket-card">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                    <div>
                        <span class="channel-badge">{row['channel'].upper()}</span>
                        <span style="font-weight: 700; font-size: 1.15rem; margin-left: 8px; color:#ffffff;">{row['id']}</span>
                    </div>
                    <span class="badge {row['badge_class']}">{row['action']}</span>
                </div>
                <blockquote style="border-left: 3px solid rgba(255,255,255,0.2); padding-left: 15px; margin: 10px 0; color: #e4e4e7; font-size: 0.95rem; font-style: italic;">
                    "{row['text']}"
                </blockquote>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem;">
                    <div>
                        <strong style="color: #a1a1aa;">Classification:</strong><br>
                        <span style="color: #ffffff; font-weight: 600;">{row['primary']}{secondaries}</span>
                    </div>
                    <div>
                        <strong style="color: #a1a1aa;">Confidence Score:</strong> <span style="color: #ffffff; font-weight: 600;">{row['confidence']:.2f}</span>
                        {conf_bar}
                    </div>
                    <div>
                        <strong style="color: #a1a1aa;">Urgency (1-5):</strong><br>
                        <span style="color: {'#ef4444' if row['urgency']>=5 else '#ffffff'}; font-weight: 700;">
                            {'🔥 ' if row['urgency']>=5 else ''}{row['urgency']} / 5
                        </span>
                    </div>
                    <div>
                        <strong style="color: #a1a1aa;">Downstream Action:</strong><br>
                        <span style="color: #ffffff; font-weight: 600;">Queue: <code>{row['queue']}</code></span><br>
                        <span style="font-size: 0.8rem; color: #a1a1aa;">{row['reason']}</span>
                    </div>
                </div>
                <div style="margin-top: 12px; padding: 10px; background: rgba(0,0,0,0.15); border-radius: 8px; font-size: 0.85rem; color: #a1a1aa; border-left: 2px solid #6366f1;">
                    <strong>Reasoning:</strong> {row['reasoning']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("Click 'Process Batch' to load tickets from `tickets.json` and run the simulation.")

# Tab 2: Test a Custom Ticket
with tab2:
    st.markdown("### 🎯 Real-Time Custom Ticket Triage")
    st.markdown("Compose a ticket or choose a sample template to watch the router classify, calibrate confidence, and decide the route in real-time.")
    
    # Samples helper
    sample_templates = {
        "Custom Blank": "",
        "Late Package Complaint": "My order #99281 has been stuck at the shipping facility for 5 days now. This was meant to be a birthday gift and I need it delivered by tomorrow or I want a full refund.",
        "Cracked screen (Defect)": "Hi, I just opened the package and the phone screen is completely cracked and damaged. Please send a replacement ASAP.",
        "Double Billing": "Hi, I checked my bank statement and I was charged twice for order INV-1002. Please check and refund the duplicate $55 charge.",
        "Short Vague Text": "hi",
        "Urgent Account Security": "My username is lock99. I received an email confirmation for a purchase of a $2000 graphics card, but I did not buy anything! Please lock my account, someone has hacked me!",
    }
    
    selected_sample = st.selectbox("Select a sample ticket template:", list(sample_templates.keys()))
    
    with st.form("custom_ticket_form"):
        col1, col2 = st.columns([1, 4])
        with col1:
            channel_input = st.selectbox("Channel", ["email", "chat", "whatsapp", "web_form"])
        with col2:
            ticket_id = st.text_input("Ticket ID Reference", value="T-CUSTOM-099")
            
        text_input = st.text_area("Ticket Message Content", value=sample_templates[selected_sample], height=120)
        
        submit_btn = st.form_submit_button("Run Ticket Triage", use_container_width=True)
        
    if submit_btn:
        if not text_input.strip():
            st.error("Please enter some ticket text.")
        else:
            with st.spinner("Calling Gemini API with Structured Output schema..."):
                t = {"id": ticket_id, "channel": channel_input, "text": text_input}
                try:
                    c = classify(t)
                    r = route_dynamic(c, auto_route_min, review_band_min)
                    
                    st.success("Triage Complete!")
                    
                    # Display nice card
                    secondaries = f" | Also: {', '.join(s.value for s in c.secondary)}" if c.secondary else ""
                    conf_bar = f"""
                    <div style="background: rgba(255,255,255,0.1); border-radius: 99px; height: 8px; width: 100%; margin-top: 4px;">
                        <div style="background: #6366f1; border-radius: 99px; height: 100%; width: {int(c.confidence * 100)}%;"></div>
                    </div>
                    """
                    
                    st.markdown(f"""
                    <div class="ticket-card" style="border-left: 4px solid #6366f1; background: rgba(99, 102, 241, 0.03);">
                        <h4 style="margin-top:0; color:#ffffff;">Triage Analysis Output</h4>
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                            <div>
                                <span class="channel-badge">{channel_input.upper()}</span>
                                <span style="font-weight: 700; font-size: 1.2rem; margin-left: 8px; color: #ffffff;">{ticket_id}</span>
                            </div>
                            <span class="badge {r['badge_class']}" style="font-size: 16px; padding: 8px 24px;">{r['action']}</span>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.02); border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                            <div>
                                <strong style="color: #a1a1aa; font-size: 0.85rem; text-transform: uppercase;">Primary Category</strong><br>
                                <span style="color: #ffffff; font-weight: 600; font-size: 1.1rem;">{c.primary.value}</span>
                                <div style="font-size: 0.85rem; color:#a1a1aa; margin-top: 2px;">{secondaries}</div>
                            </div>
                            <div>
                                <strong style="color: #a1a1aa; font-size: 0.85rem; text-transform: uppercase;">Confidence Score</strong><br>
                                <span style="color: #ffffff; font-weight: 600; font-size: 1.1rem;">{c.confidence:.2f} / 1.00</span>
                                {conf_bar}
                            </div>
                            <div>
                                <strong style="color: #a1a1aa; font-size: 0.85rem; text-transform: uppercase;">Urgency Level</strong><br>
                                <span style="color: {'#ef4444' if c.urgency>=5 else '#ffffff'}; font-weight: 700; font-size: 1.2rem;">
                                    {'🔥 ' if c.urgency>=5 else ''}{c.urgency} / 5
                                </span>
                            </div>
                            <div>
                                <strong style="color: #a1a1aa; font-size: 0.85rem; text-transform: uppercase;">Target Queue</strong><br>
                                <span style="color: #ffffff; font-weight: 600; font-size: 1.1rem;"><code>{r['queue']}</code></span><br>
                                <span style="font-size: 0.8rem; color: #a1a1aa;">{r['reason']}</span>
                            </div>
                        </div>
                        
                        <div style="margin-top: 15px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; font-size: 0.95rem; color: #e4e4e7; border-left: 3px solid #6366f1;">
                            <strong>AI Reasoning:</strong> {c.reasoning}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Failed to triage ticket: {e}")
