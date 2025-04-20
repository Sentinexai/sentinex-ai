
import streamlit as st
from sentinex import get_account_info, place_test_trade

st.set_page_config(page_title="Sentinex AI", layout="wide")

st.title("🚀 Sentinex AI Dashboard")
st.subheader("Real-time Market Sentiment & Auto Trading Bot")
st.markdown("---")

st.write("🔐 Connecting to Alpaca Paper Trading...")

try:
    account_info = get_account_info()
    st.success("✅ Connected to Alpaca")
    st.write("💰 Buying Power:", account_info["buying_power"])
    st.write("💵 Cash:", account_info["cash"])
    st.write("📊 Portfolio Value:", account_info["portfolio_value"])
    st.write("🟢 Status:", account_info["status"])
except Exception as e:
    st.error(f"❌ Failed to connect: {e}")

st.markdown("---")

if st.button("🚨 Run Test Trade (Buy 1 AAPL)"):
    result = place_test_trade()
    st.success(result

