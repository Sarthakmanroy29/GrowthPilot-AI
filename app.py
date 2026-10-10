import json
import io
from typing import Any

import pandas as pd
import streamlit as st
import requests
from google import genai
from google.genai import types

st.set_page_config(
    page_title="GrowthPilot AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_CAMPAIGNS = pd.DataFrame([
    {"channel": "Meta Ads", "spend": 80000, "attributed_revenue": 176000, "orders": 110, "new_customers": 75, "sessions": 6000},
    {"channel": "Google Ads", "spend": 50000, "attributed_revenue": 150000, "orders": 80, "new_customers": 55, "sessions": 3200},
])

SYSTEM_INSTRUCTIONS = """
You are GrowthPilot AI, a marketing analytics manager and growth strategy consultant
for Indian D2C e-commerce businesses. Give clear, professional advice suitable for
an MBA/PGDM student and business manager.

Rules:
- Use the supplied data and calculated metrics. Never invent facts, business results,
  data, or actions. Do not silently ignore supplied metrics.
- Separate facts, assumptions, hypotheses, and recommendations.
- Definitions: ROAS = attributed revenue / advertising spend; CAC = acquisition spend /
  new customers; conversion rate = conversions / sessions; AOV = revenue / orders.
- Do not assume orders equal conversions unless explicitly stated. If orders are used
  as a proxy, label that assumption. Calculate only when required inputs are present.
- Check that periods, attribution scope, currency, and units are consistent.
- ROAS is not profit. Mention missing product margin, fulfilment, discounts, refunds,
  taxes, and other variable costs where relevant.
- Explain causes as hypotheses unless evidence supports causation.
- Prioritize actions by expected impact, effort, confidence, and risk.
- Budget recommendations are scenarios, not guarantees. Never claim to have changed
  campaigns, spent money, sent messages, or performed actions outside this app.
- For experiments include hypothesis, segment, control, variant, primary KPI,
  guardrail metric, duration/sample-size considerations, and success criteria.
- Ask focused questions when essential information is missing, while still helping
  with available data.
- Structure answers when relevant: Executive summary; key findings; calculations;
  prioritized recommendations; experiment; KPIs; risks and assumptions; missing data.
"""

def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        if value:
            return str(value)
    except Exception:
        pass
    return default

def safe_float(value: Any):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    numeric_cols = ["spend", "attributed_revenue", "orders", "new_customers", "sessions", "conversions"]
    for col in numeric_cols:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")
    if "spend" in result and "attributed_revenue" in result:
        result["roas"] = result.apply(
            lambda r: r["attributed_revenue"] / r["spend"]
            if pd.notna(r["spend"]) and r["spend"] > 0 and pd.notna(r["attributed_revenue"])
            else None, axis=1
        )
    if "spend" in result and "new_customers" in result:
        result["cac"] = result.apply(
            lambda r: r["spend"] / r["new_customers"]
            if pd.notna(r["new_customers"]) and r["new_customers"] > 0 and pd.notna(r["spend"])
            else None, axis=1
        )
    if "attributed_revenue" in result and "orders" in result:
        result["aov"] = result.apply(
            lambda r: r["attributed_revenue"] / r["orders"]
            if pd.notna(r["orders"]) and r["orders"] > 0 and pd.notna(r["attributed_revenue"])
            else None, axis=1
        )
    if "sessions" in result and "conversions" in result:
        result["conversion_rate_pct"] = result.apply(
            lambda r: (r["conversions"] / r["sessions"] * 100)
            if pd.notna(r["sessions"]) and r["sessions"] > 0 and pd.notna(r["conversions"])
            else None, axis=1
        )
    return result

def fmt_inr(value):
    if value is None or pd.isna(value):
        return "—"
    return f"₹{value:,.0f}"

def fmt_num(value, suffix=""):
    if value is None or pd.isna(value):
        return "—"
    return f"{value:,.2f}{suffix}"

def make_context(business, currency, period, df, extra_metrics):
    calculated = calculate_metrics(df)
    context = {
        "business": business,
        "currency": currency,
        "period": period,
        "campaign_rows": calculated.where(pd.notna(calculated), None).to_dict(orient="records"),
        "user_supplied_metrics": extra_metrics or {},
        "metric_notes": [
            "ROAS = attributed_revenue / spend; ROAS is not profit.",
            "CAC here uses spend / new_customers as a channel-level proxy; the user should confirm whether all acquisition costs are included.",
            "Conversion rate is calculated only if a conversions column is provided; orders are not automatically assumed to be conversions.",
            "AOV here uses attributed_revenue / orders and is attribution-dependent."
        ]
    }
    return calculated, context

def call_gemini(api_key, model, prompt, context):
    client = genai.Client(api_key=api_key)
    full_prompt = (
        SYSTEM_INSTRUCTIONS
        + "\n\nBUSINESS DATA AND CALCULATED METRICS (JSON):\n"
        + json.dumps(context, ensure_ascii=False, default=str)
        + "\n\nUSER QUESTION:\n"
        + prompt
    )
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2200,
        ),
    )
    answer = getattr(response, "text", None)
    if not answer:
        raise RuntimeError("Gemini returned no text. Check the model, API quota, or safety response.")
    return answer

def call_n8n(webhook_url, message, business, currency, period, data_records, metrics):
    payload = {
        "message": message,
        "business": business,
        "currency": currency,
        "data": {"period": period, "campaigns": data_records},
        "metrics": metrics or {},
    }
    response = requests.post(webhook_url, json=payload, timeout=90)
    response.raise_for_status()
    return response.json()

st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 2rem; max-width: 1400px;}
.hero {padding: 1.25rem 1.4rem; border-radius: 18px; background: linear-gradient(120deg, #12243a, #234d69); color: white; margin-bottom: 1rem;}
.hero h1 {color: white; margin: 0; font-size: 2.1rem;}
.hero p {color: #e2edf5; margin: .4rem 0 0 0;}
.small-muted {color: #64748b; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>🚀 GrowthPilot AI</h1>
  <p>Marketing Analytics & Growth Strategy Agent · Indian D2C e-commerce</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Business setup")
    business = st.text_input("Business name / type", "Indian D2C skincare brand")
    currency = st.selectbox("Currency", ["INR", "USD", "GBP", "EUR"], index=0)
    period = st.text_input("Reporting period", "Last 30 days")
    st.divider()
    st.header("AI settings")
    api_key = get_secret("GEMINI_API_KEY")
    if not api_key:
        api_key = st.text_input("Gemini API key", type="password", help="For local testing only. Prefer .streamlit/secrets.toml.")
    model = get_secret("GEMINI_MODEL", "gemini-2.5-flash")
    model = st.text_input("Gemini model", value=model, help="Use a model currently available to your Gemini API key.")
    st.divider()
    use_n8n = st.toggle("Route questions through my n8n workflow", value=False)
    n8n_url = get_secret("N8N_WEBHOOK_URL", "")
    if use_n8n:
        n8n_url = st.text_input("n8n production webhook URL", value=n8n_url, help="For local testing: http://localhost:5678/webhook/growthpilot-chat")
        st.caption("A deployed website cannot reach localhost on your laptop. For cloud deployment, n8n must be reachable through a secure public HTTPS URL.")
    st.caption("Never commit API keys or secrets.toml to GitHub.")

st.subheader("1. Campaign data")
st.write("Use the sample campaigns, edit the table, or upload a CSV with campaign metrics.")

uploaded = st.file_uploader("Upload campaign CSV (optional)", type=["csv"])
if uploaded:
    try:
        source_df = pd.read_csv(uploaded)
        st.success(f"Loaded {len(source_df)} rows from {uploaded.name}.")
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        source_df = DEFAULT_CAMPAIGNS.copy()
else:
    if "campaign_editor" not in st.session_state:
        st.session_state.campaign_editor = DEFAULT_CAMPAIGNS.copy()
    source_df = st.session_state.campaign_editor.copy()

required_cols = ["channel", "spend", "attributed_revenue", "orders", "new_customers", "sessions"]
missing_cols = [c for c in required_cols if c not in source_df.columns]
if missing_cols:
    st.warning("Your CSV is missing these expected columns: " + ", ".join(missing_cols) + ". Add them or use the sample table. Extra columns are retained.")
    for col in required_cols:
        if col not in source_df.columns:
            source_df[col] = None

edited_df = st.data_editor(
    source_df,
    num_rows="dynamic",
    use_container_width=True,
    key="data_editor",
    column_config={
        "spend": st.column_config.NumberColumn("Spend", min_value=0, format="%.2f"),
        "attributed_revenue": st.column_config.NumberColumn("Attributed revenue", min_value=0, format="%.2f"),
        "orders": st.column_config.NumberColumn("Orders", min_value=0, format="%.0f"),
        "new_customers": st.column_config.NumberColumn("New customers", min_value=0, format="%.0f"),
        "sessions": st.column_config.NumberColumn("Sessions", min_value=0, format="%.0f"),
        "conversions": st.column_config.NumberColumn("Conversions (optional)", min_value=0, format="%.0f"),
    },
)

extra_metrics_text = st.text_area(
    "Additional metrics / definitions (optional)",
    placeholder='Example: "Revenue excludes refunds; new customers are first-time purchasers."',
    height=75,
)
extra_metrics = {"notes": extra_metrics_text.strip()} if extra_metrics_text.strip() else {}

calculated_df, context = make_context(business, currency, period, edited_df, extra_metrics)
st.subheader("2. Performance overview")
spend_total = pd.to_numeric(edited_df.get("spend", pd.Series(dtype=float)), errors="coerce").sum(min_count=1)
revenue_total = pd.to_numeric(edited_df.get("attributed_revenue", pd.Series(dtype=float)), errors="coerce").sum(min_count=1)
orders_total = pd.to_numeric(edited_df.get("orders", pd.Series(dtype=float)), errors="coerce").sum(min_count=1)
new_cust_total = pd.to_numeric(edited_df.get("new_customers", pd.Series(dtype=float)), errors="coerce").sum(min_count=1)
sessions_total = pd.to_numeric(edited_df.get("sessions", pd.Series(dtype=float)), errors="coerce").sum(min_count=1)
conversions_series = pd.to_numeric(edited_df.get("conversions", pd.Series(dtype=float)), errors="coerce")
conversions_total = conversions_series.sum(min_count=1) if "conversions" in edited_df.columns else None
roas_total = revenue_total / spend_total if pd.notna(revenue_total) and pd.notna(spend_total) and spend_total > 0 else None
cac_total = spend_total / new_cust_total if pd.notna(spend_total) and pd.notna(new_cust_total) and new_cust_total > 0 else None
aov_total = revenue_total / orders_total if pd.notna(revenue_total) and pd.notna(orders_total) and orders_total > 0 else None
cvr_total = conversions_total / sessions_total * 100 if conversions_total is not None and pd.notna(conversions_total) and pd.notna(sessions_total) and sessions_total > 0 else None

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ad spend", fmt_inr(spend_total) if currency == "INR" else f"{currency} {spend_total:,.0f}" if pd.notna(spend_total) else "—")
c2.metric("Attributed revenue", fmt_inr(revenue_total) if currency == "INR" else f"{currency} {revenue_total:,.0f}" if pd.notna(revenue_total) else "—")
c3.metric("ROAS", fmt_num(roas_total, "×"))
c4.metric("CAC proxy", fmt_inr(cac_total) if currency == "INR" else f"{currency} {cac_total:,.2f}" if cac_total is not None else "—")
c5.metric("AOV", fmt_inr(aov_total) if currency == "INR" else f"{currency} {aov_total:,.2f}" if aov_total is not None else "—")
if cvr_total is None:
    st.info("Conversion rate is not calculated because the data does not include a conversions column. Orders are not automatically treated as conversions.")
else:
    st.metric("Conversion rate", f"{cvr_total:.2f}%")
st.caption("These are derived from the rows currently shown. ROAS is not profit. CAC uses ad spend as a proxy and may exclude other acquisition costs.")

st.subheader("3. Channel comparison")
if "channel" in calculated_df.columns and "roas" in calculated_df.columns:
    chart_df = calculated_df[["channel", "roas"]].dropna().set_index("channel")
    if not chart_df.empty:
        st.bar_chart(chart_df)
st.dataframe(calculated_df, use_container_width=True, hide_index=True)

st.subheader("4. Ask GrowthPilot AI")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
for entry in st.session_state.chat_history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])

question = st.chat_input("Ask about campaign performance, growth strategy, retention, or experiments...")
if question:
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Analyzing campaign data..."):
            try:
                if use_n8n:
                    if not n8n_url:
                        raise ValueError("Enter the n8n webhook URL in the sidebar, or turn off n8n routing.")
                    records = calculated_df.where(pd.notna(calculated_df), None).to_dict(orient="records")
                    answer_json = call_n8n(n8n_url, question, business, currency, period, records, extra_metrics)
                    answer = answer_json.get("reply") or answer_json.get("output") or json.dumps(answer_json, ensure_ascii=False, indent=2)
                    if answer_json.get("success") is False:
                        st.warning("The n8n workflow returned success=false.")
                else:
                    if not api_key:
                        raise ValueError("Add your Gemini API key in .streamlit/secrets.toml or the sidebar.")
                    answer = call_gemini(api_key, model, question, context)
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
            except Exception as exc:
                error_message = str(exc)
                st.error(f"Could not generate a response: {error_message}")
                st.caption("Check the API key, model availability, quota, internet connection, and n8n webhook URL if enabled.")

with st.expander("How metrics are calculated"):
    st.markdown("""
    - **ROAS** = attributed revenue ÷ advertising spend.
    - **CAC proxy** = advertising spend ÷ new customers. This may not include all acquisition costs.
    - **AOV** = attributed revenue ÷ orders.
    - **Conversion rate** = conversions ÷ sessions. It is only shown when a separate `conversions` column is supplied.
    - Use consistent periods, currencies, attribution rules and channel definitions before comparing results.
    """)

st.divider()
st.caption("GrowthPilot AI · AI-generated recommendations are advisory. Validate data and obtain human approval before consequential business actions.")
