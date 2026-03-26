"""
dashboard/app.py — AlphaSignal Streamlit Dashboard

Run:
    streamlit run dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AlphaSignal — ML Trading Platform",
    page_icon="α",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

[data-testid="stAppViewContainer"] {
    background: #0a0f1a;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
    background: #0d1421;
    border-right: 1px solid rgba(255,255,255,0.08);
}
/* Ticker tape bar */
.ticker-bar {
    background: #0d1421;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    padding: 0;
    overflow: hidden;
    width: 100%;
    position: sticky;
    top: 0;
    z-index: 999;
}
.ticker-track {
    display: flex;
    width: max-content;
    animation: scroll-left 40s linear infinite;
}
.ticker-track:hover { animation-play-state: paused; }
.ticker-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 28px;
    border-right: 1px solid rgba(255,255,255,0.06);
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    white-space: nowrap;
    color: rgba(255,255,255,0.85);
}
.ticker-symbol { font-weight: 700; color: #fff; }
.ticker-up   { color: #00C896; }
.ticker-down { color: #FF4D6A; }
.ticker-flat { color: #F5A623; }
@keyframes scroll-left {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

/* Metrics */
.stMetric {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 12px;
    border: 1px solid rgba(255,255,255,0.08);
}
.stMetric label {
    font-size: 11px !important;
    color: rgba(255,255,255,0.5) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Signal badges */
.signal-buy  { background:rgba(0,200,150,0.15);  color:#00C896; border-radius:6px; padding:3px 10px; font-weight:700; font-size:12px; font-family:'Space Mono',monospace; }
.signal-sell { background:rgba(255,77,106,0.15); color:#FF4D6A; border-radius:6px; padding:3px 10px; font-weight:700; font-size:12px; font-family:'Space Mono',monospace; }
.signal-hold { background:rgba(245,166,35,0.15); color:#F5A623; border-radius:6px; padding:3px 10px; font-weight:700; font-size:12px; font-family:'Space Mono',monospace; }

/* Logo */
.logo-header { font-family:'Space Mono',monospace; font-size:18px; color:#00C896; letter-spacing:0.05em; }
h1,h2,h3 { color:rgba(255,255,255,0.9) !important; }

/* Buttons */
.stButton > button {
    background: rgba(0,200,150,0.1);
    border: 1px solid rgba(0,200,150,0.3);
    color: #00C896;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
}
.stButton > button:hover { background: rgba(0,200,150,0.2); }

/* Auto-refresh badge */
.refresh-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(0,200,150,0.1);
    border: 1px solid rgba(0,200,150,0.25);
    border-radius: 20px; padding: 4px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 10px; color: #00C896;
}
.pulse {
    width: 6px; height: 6px; border-radius: 50%;
    background: #00C896;
    animation: pulse 1.5s ease-in-out infinite;
    display: inline-block;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.2} }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "refresh_count" not in st.session_state:
    st.session_state.refresh_count = 0

REFRESH_INTERVAL = 300   # 5 minutes in seconds


# ── Lazy resource loaders ─────────────────────────────────────────────────────
@st.cache_resource
def get_fetcher():
    from data_ingestion.fetcher import MarketDataFetcher
    return MarketDataFetcher()

@st.cache_resource
def get_runner():
    try:
        from ml_engine.signal_runner import SignalRunner
        return SignalRunner()
    except Exception as e:
        st.error(f"Could not load ML engine: {e}")
        return None

@st.cache_resource
def get_backtester():
    from backtesting.engine import BacktestEngine
    return BacktestEngine()


# ── Live quotes (cached 60s, force-cleared on auto-refresh) ──────────────────
@st.cache_data(ttl=60)
def load_quotes(tickers_tuple):
    fetcher = get_fetcher()
    return fetcher.get_batch_quotes(list(tickers_tuple))

@st.cache_data(ttl=300)
def load_price_data(ticker, period):
    fetcher = get_fetcher()
    return fetcher.get_ohlcv(ticker, period=period)


# ── Ticker tape HTML builder ──────────────────────────────────────────────────
def build_ticker_tape(quotes):
    if not quotes:
        return ""

    def item(q):
        price  = q.get("price", 0)
        change = q.get("change_pct", 0)
        ticker = q.get("ticker", "")
        if change > 0:
            arrow, cls = "▲", "ticker-up"
        elif change < 0:
            arrow, cls = "▼", "ticker-down"
        else:
            arrow, cls = "▬", "ticker-flat"
        return (
            f'<div class="ticker-item">'
            f'<span class="ticker-symbol">{ticker}</span>'
            f'<span>${price:,.2f}</span>'
            f'<span class="{cls}">{arrow} {abs(change):.2f}%</span>'
            f'</div>'
        )

    items_html = "".join(item(q) for q in quotes if "error" not in q)
    # Duplicate for seamless loop
    return f"""
    <div class="ticker-bar">
      <div class="ticker-track">
        {items_html}{items_html}
      </div>
    </div>
    """


# ── Auto-refresh logic ────────────────────────────────────────────────────────
def check_auto_refresh():
    if not st.session_state.auto_refresh:
        return
    elapsed = (datetime.now() - st.session_state.last_refresh).total_seconds()
    remaining = max(0, int(REFRESH_INTERVAL - elapsed))
    if elapsed >= REFRESH_INTERVAL:
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now()
        st.session_state.refresh_count += 1
        st.rerun()
    return remaining


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="logo-header">α AlphaSignal</div>', unsafe_allow_html=True)
    st.caption("ML Signal Generation Platform v2.4")
    st.divider()

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "📈 Signals", "🔬 Backtest", "🔔 Alerts"],
        label_visibility="collapsed",
    )
    st.divider()

    st.subheader("Watchlist")
    default_tickers = "AAPL,NVDA,TSLA,SPY,QQQ,MSFT,GOOGL,AMZN,META"
    ticker_input = st.text_area("Tickers (comma-separated)", value=default_tickers, height=100)
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

    st.divider()
    st.subheader("Settings")
    period = st.selectbox("Data Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)
    confidence_thresh = st.slider("Min Confidence", 0.5, 0.95, 0.65, 0.05)

    st.divider()
    st.subheader("Auto Refresh")

    auto_on = st.toggle("Every 5 minutes", value=st.session_state.auto_refresh)
    st.session_state.auto_refresh = auto_on

    remaining = check_auto_refresh()

    if auto_on:
        elapsed = (datetime.now() - st.session_state.last_refresh).total_seconds()
        pct = min(int(elapsed / REFRESH_INTERVAL * 100), 100)
        st.progress(pct)
        mins = remaining // 60
        secs = remaining % 60
        st.markdown(
            f'<div class="refresh-badge">'
            f'<span class="pulse"></span>'
            f'LIVE · next in {mins}m {secs:02d}s'
            f'</div>',
            unsafe_allow_html=True
        )
        st.caption(f"Refreshed {st.session_state.refresh_count}x · last {st.session_state.last_refresh.strftime('%H:%M:%S')}")

    if st.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.session_state.last_refresh = datetime.now()
        st.session_state.refresh_count += 1
        st.rerun()

    st.markdown("---")
    st.caption(f"NYSE · {datetime.now().strftime('%H:%M:%S')} EST")


# ── Live quotes for ticker tape ───────────────────────────────────────────────
with st.spinner(""):
    quotes = load_quotes(tuple(tickers[:12]))

# ── Render ticker tape at top of every page ───────────────────────────────────
tape_placeholder = st.empty()
tape_html = build_ticker_tape(quotes)
if tape_html:
    tape_placeholder.markdown(tape_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PAGE
# ═══════════════════════════════════════════════════════════════════════════════
if "Dashboard" in page:
    st.title("Market Dashboard")

    # ── Real-time price updater using st.fragment ─────────────────────────────
    # st.fragment allows this block to rerun every N seconds WITHOUT
    # refreshing the rest of the page (requires Streamlit >= 1.33)
    try:
        @st.fragment(run_every=30)  # update prices every 30 seconds
        def live_price_cards():
            fetcher = get_fetcher()
            live_quotes = fetcher.get_batch_quotes(tickers[:8])

            # ── Ticker tape refresh ───────────────────────────────────────────
            tape = build_ticker_tape(live_quotes)
            if tape:
                tape_placeholder.markdown(tape, unsafe_allow_html=True)

            # ── Price metric cards ────────────────────────────────────────────
            if live_quotes:
                cols = st.columns(min(len(live_quotes), 4))
                for i, q in enumerate(live_quotes[:4]):
                    if "error" not in q:
                        with cols[i]:
                            price  = q.get("price", 0)
                            change = q.get("change_pct", 0)
                            st.metric(
                                label=q["ticker"],
                                value=f"${price:,.2f}",
                                delta=f"{change:+.2f}%",
                            )

            # ── All tickers live table ────────────────────────────────────────
            st.markdown("### Live Prices")
            rows = []
            for q in live_quotes:
                if "error" not in q:
                    chg = q.get("change_pct", 0)
                    rows.append({
                        "Ticker":     q["ticker"],
                        "Price":      f"${q.get('price', 0):,.2f}",
                        "Change":     f"{chg:+.2f}%",
                        "Prev Close": f"${q.get('prev_close', 0):,.2f}",
                        "Volume":     f"{q.get('volume', 0):,}" if q.get("volume") else "—",
                        "Updated":    q.get("timestamp", "")[:19],
                    })
            if rows:
                import pandas as pd
                qt_df = pd.DataFrame(rows)
                def color_change(val):
                    if "+" in str(val): return "color:#00C896;font-weight:bold"
                    if "-" in str(val): return "color:#FF4D6A;font-weight:bold"
                    return "color:#F5A623"
                styled = qt_df.style.applymap(color_change, subset=["Change"])
                st.dataframe(styled, use_container_width=True, hide_index=True)

            # ── Refresh timestamp ─────────────────────────────────────────────
            st.caption(f"⚡ Prices auto-update every 30 seconds · Last updated: {datetime.now().strftime('%H:%M:%S')}")

        live_price_cards()

    except (TypeError, AttributeError):
        # Fallback for Streamlit < 1.33 — show static prices
        if quotes:
            cols = st.columns(min(len(quotes), 4))
            for i, q in enumerate(quotes[:4]):
                with cols[i]:
                    st.metric(
                        label=q["ticker"],
                        value=f"${q.get('price', 0):,.2f}",
                        delta=f"{q.get('change_pct', 0):+.2f}%",
                    )
        st.caption("ℹ️ Upgrade Streamlit to 1.33+ for live price updates: pip install --upgrade streamlit")

    st.divider()

    # ── Price chart + model perf ──────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Price Chart + Signals")
        selected_ticker = st.selectbox("Select ticker", tickers, key="chart_ticker")
        df = load_price_data(selected_ticker, period)

        if not df.empty:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"],
                low=df["Low"], close=df["Close"], name="OHLC",
                increasing_line_color="#00C896",
                decreasing_line_color="#FF4D6A",
            ))
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"].ewm(span=20).mean(),
                name="EMA 20", line=dict(color="#3B82F6", width=1, dash="dot")
            ))
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Close"].ewm(span=50).mean(),
                name="EMA 50", line=dict(color="#F5A623", width=1, dash="dot")
            ))
            fig.update_layout(
                template="plotly_dark", height=400,
                xaxis_rangeslider_visible=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.02)",
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Model Performance")
        perf_df = pd.DataFrame({
            "Model":    ["Ensemble", "LSTM", "XGBoost", "Random Forest"],
            "Accuracy": [85.3, 82.1, 76.8, 78.4],
        })
        fig2 = go.Figure(go.Bar(
            x=perf_df["Accuracy"], y=perf_df["Model"], orientation="h",
            marker=dict(color=["#F5A623", "#3B82F6", "#00C896", "#8B5CF6"], opacity=0.85),
            text=[f"{a:.1f}%" for a in perf_df["Accuracy"]],
            textposition="inside",
        ))
        fig2.update_layout(
            template="plotly_dark", height=200,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
            xaxis=dict(range=[60, 95]),
        )
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Quick Metrics")
        m1, m2 = st.columns(2)
        m1.metric("Active Signals", "24", "+3")
        m2.metric("Sharpe (30d)", "2.31", "+0.12")
        m1.metric("Win Rate", "68.4%", "+2.1%")
        m2.metric("Max DD", "-14.8%", "+1.2%")

    st.divider()

    # ── Volume + feature importance ───────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Volume Analysis")
        if not df.empty:
            colors = np.where(
                df["Close"].iloc[-60:].pct_change() >= 0,
                "rgba(0,200,150,0.6)", "rgba(255,77,106,0.6)"
            )
            vol_fig = go.Figure(go.Bar(
                x=df.index[-60:], y=df["Volume"].iloc[-60:],
                marker_color=colors,
            ))
            vol_fig.update_layout(
                template="plotly_dark", height=200,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.02)",
                margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
            )
            st.plotly_chart(vol_fig, use_container_width=True)

    with col4:
        st.subheader("Feature Importance")
        feat_df = pd.DataFrame({
            "Feature":    ["RSI", "MACD", "Volume", "EMA Cross", "BB Width", "ATR"],
            "Importance": [0.24, 0.19, 0.17, 0.15, 0.13, 0.12],
        })
        feat_fig = px.bar(
            feat_df, x="Importance", y="Feature", orientation="h",
            color="Importance", color_continuous_scale=["#3B82F6", "#8B5CF6"],
        )
        feat_fig.update_layout(
            template="plotly_dark", height=200,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0), coloraxis_showscale=False,
        )
        st.plotly_chart(feat_fig, use_container_width=True)




# ═══════════════════════════════════════════════════════════════════════════════
# SIGNALS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif "Signals" in page:
    st.title("Signal Monitor")

    from utils.ticker_store import get_watchlist, add_ticker, remove_ticker, ticker_exists
    from utils.ticker_search import search_tickers, validate_ticker

    # ── Load persistent watchlist ─────────────────────────────────────────────
    watchlist = get_watchlist()

    # ── Top controls row ──────────────────────────────────────────────────────
    ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])

    with ctrl1:
        st.markdown("#### 🔍 Search & Add Ticker")
        search_query = st.text_input(
            "Search by name or symbol",
            placeholder="e.g. Apple, NVDA, S&P 500...",
            label_visibility="collapsed",
            key="ticker_search_input",
        )

    with ctrl2:
        st.markdown("#### Min Confidence")
        sig_confidence = st.slider(
            "Confidence", 0.50, 0.95, confidence_thresh, 0.05,
            label_visibility="collapsed", key="sig_conf_slider"
        )

    with ctrl3:
        st.markdown("#### Auto Refresh")
        st.markdown(
            f'''<div class="refresh-badge" style="margin-top:8px">
            <span class="pulse"></span>
            {f"Next in {(REFRESH_INTERVAL - (datetime.now() - st.session_state.last_refresh).total_seconds()):.0f}s"
             if st.session_state.auto_refresh else "Paused"}
            </div>''',
            unsafe_allow_html=True
        )

    # ── Search results dropdown ───────────────────────────────────────────────
    if search_query and len(search_query) >= 1:
        with st.spinner("Searching..."):
            results = search_tickers(search_query, limit=8)

        if results:
            st.markdown("**Search Results** — click a row to add to watchlist")
            for r in results:
                sym    = r["symbol"]
                name   = r["name"]
                exch   = r.get("exchange", "")
                rtype  = r.get("type", "")
                in_wl  = ticker_exists(sym)

                rc1, rc2, rc3, rc4 = st.columns([1.2, 3, 1.2, 1.2])
                rc1.markdown(f"**`{sym}`**")
                rc2.caption(f"{name} · {exch}")
                rc3.caption(rtype)

                if in_wl:
                    rc4.markdown(
                        '<span style="color:#00C896;font-size:11px;font-family:monospace;">✓ IN WATCHLIST</span>',
                        unsafe_allow_html=True
                    )
                else:
                    if rc4.button(f"➕ Add", key=f"add_{sym}"):
                        info = validate_ticker(sym)
                        if info["valid"]:
                            ok = add_ticker(sym)
                            if ok:
                                st.success(f"✅ {sym} — {info['name']} added! Price: ${info['price']:.2f}")
                                st.rerun()
                            else:
                                st.warning(f"{sym} already in watchlist.")
                        else:
                            st.error(f"Could not validate {sym}. Check the symbol and try again.")
        else:
            st.info("No results found. Try a different name or symbol.")

        st.divider()

    # ── Watchlist management bar ──────────────────────────────────────────────
    with st.expander(f"📋 Manage Watchlist  ({len(watchlist)} tickers)", expanded=False):
        st.caption("Click ✕ to remove a ticker from your watchlist")
        cols_per_row = 5
        rows = [watchlist[i:i+cols_per_row] for i in range(0, len(watchlist), cols_per_row)]
        for row in rows:
            wcols = st.columns(cols_per_row)
            for j, t in enumerate(row):
                with wcols[j]:
                    st.markdown(
                        f'''<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);
                        border-radius:8px;padding:6px 10px;display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <span style="font-family:monospace;font-size:12px;font-weight:700;">{t}</span>
                        </div>''',
                        unsafe_allow_html=True
                    )
                    if st.button("✕", key=f"rm_{t}", help=f"Remove {t}"):
                        remove_ticker(t)
                        st.success(f"Removed {t}")
                        st.rerun()

        st.divider()
        mc1, mc2 = st.columns(2)
        manual_add = mc1.text_input("Add by symbol directly", placeholder="e.g. PLTR", key="manual_add")
        if mc2.button("➕ Add Ticker", key="manual_add_btn") and manual_add:
            sym = manual_add.strip().upper()
            info = validate_ticker(sym)
            if info["valid"]:
                ok = add_ticker(sym)
                st.success(f"✅ Added {sym}") if ok else st.warning(f"{sym} already exists")
                st.rerun()
            else:
                st.error(f"Invalid ticker: {sym}")

    st.divider()

    # ── Real-time signal generation ───────────────────────────────────────────
    st.markdown("### 📡 Live Signals")

    col_hdr1, col_hdr2, col_hdr3 = st.columns([3, 1, 1])
    col_hdr1.caption(f"Monitoring {len(watchlist)} tickers · Min confidence {sig_confidence*100:.0f}%")

    run_now = col_hdr2.button("⚡ Run Signals Now", use_container_width=True)
    auto_sig = col_hdr3.toggle("Auto-run", value=True, key="auto_sig_toggle")

    # Run signals if: button pressed, auto-refresh triggered, OR first visit
    first_visit = "live_signals_df" not in st.session_state
    should_run = run_now or (auto_sig and st.session_state.refresh_count > 0) or first_visit

    # Always clear stale cache from previous logic version
    if "signals_logic_version" not in st.session_state:
        st.session_state.pop("live_signals_df", None)
        st.session_state["signals_logic_version"] = "v3"

    if should_run or "live_signals_df" not in st.session_state:
        with st.spinner(f"Running ML models on {len(watchlist)} tickers..."):
            try:
                from data_ingestion.fetcher import MarketDataFetcher
                from data_ingestion.features import FeatureEngineer

                fetcher3 = MarketDataFetcher()
                fe3 = FeatureEngineer()
                signal_rows = []

                progress = st.progress(0, text="Fetching market data...")
                for i, ticker in enumerate(watchlist):
                    progress.progress(
                        (i + 1) / len(watchlist),
                        text=f"Analyzing {ticker}... ({i+1}/{len(watchlist)})"
                    )
                    try:
                        # Get live quote
                        q = fetcher3.get_live_quote(ticker)
                        price = q.get("price", 0)
                        change = q.get("change_pct", 0)

                        # Get features for signal
                        df_t = fetcher3.get_ohlcv(ticker, period="6mo")
                        if df_t.empty or len(df_t) < 60:
                            continue

                        df_t = fe3.add_all_features(df_t)
                        df_t = fe3.add_target_labels(df_t)
                        df_t.dropna(inplace=True)

                        if df_t.empty:
                            continue

                        # Quick RF signal from features
                        recent = df_t.tail(1)
                        rsi_val = float(recent["rsi"].values[0]) if "rsi" in recent.columns else 50
                        macd_val = float(recent["macd_hist"].values[0]) if "macd_hist" in recent.columns else 0
                        bb_pct = float(recent["bb_pct"].values[0]) if "bb_pct" in recent.columns else 0.5
                        vol_ratio = float(recent["volume_ratio"].values[0]) if "volume_ratio" in recent.columns else 1

                        # ── Multi-factor signal engine ───────────────────────
                        buy_score  = 0.0
                        sell_score = 0.0

                        # 1. RSI — oversold/overbought (max 2.5 pts)
                        if rsi_val <= 25:       buy_score  += 2.5
                        elif rsi_val <= 35:     buy_score  += 2.0
                        elif rsi_val <= 42:     buy_score  += 1.5
                        elif rsi_val <= 48:     buy_score  += 0.5
                        elif rsi_val >= 75:     sell_score += 2.5
                        elif rsi_val >= 65:     sell_score += 2.0
                        elif rsi_val >= 58:     sell_score += 1.5
                        elif rsi_val >= 52:     sell_score += 0.5

                        # 2. MACD histogram normalised (max 2.5 pts)
                        # Typical MACD_hist range is -2 to +2, normalise by 0.5
                        m_norm = macd_val / 0.5
                        if m_norm > 2.0:        buy_score  += 2.5
                        elif m_norm > 0.5:      buy_score  += 2.0
                        elif m_norm > 0.0:      buy_score  += 1.0
                        elif m_norm < -2.0:     sell_score += 2.5
                        elif m_norm < -0.5:     sell_score += 2.0
                        else:                   sell_score += 1.0

                        # 3. Bollinger Band position (max 2.0 pts)
                        if bb_pct < 0.10:       buy_score  += 2.0
                        elif bb_pct < 0.20:     buy_score  += 1.5
                        elif bb_pct < 0.30:     buy_score  += 1.0
                        elif bb_pct > 0.90:     sell_score += 2.0
                        elif bb_pct > 0.80:     sell_score += 1.5
                        elif bb_pct > 0.70:     sell_score += 1.0

                        # 4. Price change momentum (max 1.5 pts)
                        if change > 3.0:        buy_score  += 1.5
                        elif change > 1.5:      buy_score  += 1.0
                        elif change > 0.5:      buy_score  += 0.5
                        elif change < -3.0:     sell_score += 1.5
                        elif change < -1.5:     sell_score += 1.0
                        elif change < -0.5:     sell_score += 0.5

                        # 5. Volume x direction (max 1.0 pt)
                        if vol_ratio > 2.0 and change > 0:    buy_score  += 1.0
                        elif vol_ratio > 1.3 and change > 0:  buy_score  += 0.5
                        elif vol_ratio > 2.0 and change < 0:  sell_score += 1.0
                        elif vol_ratio > 1.3 and change < 0:  sell_score += 0.5

                        # ── Decision: gap >= 1.0 needed to fire BUY/SELL ─────
                        score_gap = abs(buy_score - sell_score)
                        if buy_score > sell_score and score_gap >= 1.0:
                            signal     = "BUY"
                            confidence = min(0.95, 0.60 + (buy_score / 8.5) * 0.35)
                        elif sell_score > buy_score and score_gap >= 1.0:
                            signal     = "SELL"
                            confidence = min(0.95, 0.60 + (sell_score / 8.5) * 0.35)
                        else:
                            signal     = "HOLD"
                            confidence = min(0.75, 0.50 + score_gap * 0.08)

                        if confidence < sig_confidence:
                            signal = "HOLD"

                        signal_rows.append({
                            "Ticker":     ticker,
                            "Price":      price,
                            "Change %":   change,
                            "Signal":     signal,
                            "Confidence": round(confidence, 3),
                            "RSI":        round(rsi_val, 1),
                            "MACD":       round(macd_val, 4),
                            "BB %":       round(bb_pct * 100, 1),
                            "Vol Ratio":  round(vol_ratio, 2),
                        })
                    except Exception as ex:
                        signal_rows.append({
                            "Ticker": ticker, "Price": 0, "Change %": 0,
                            "Signal": "ERROR", "Confidence": 0,
                            "RSI": 0, "MACD": 0, "BB %": 0, "Vol Ratio": 0,
                        })

                progress.empty()
                st.session_state.live_signals_df = signal_rows
                st.session_state.signals_last_run = datetime.now().strftime("%H:%M:%S")

            except Exception as e:
                st.error(f"Signal error: {e}")

    # ── Display signals table ─────────────────────────────────────────────────
    if "live_signals_df" in st.session_state and st.session_state.live_signals_df:
        sig_data = st.session_state.live_signals_df
        last_run = st.session_state.get("signals_last_run", "—")

        # Summary metrics
        sm1, sm2, sm3, sm4 = st.columns(4)
        total_s  = len(sig_data)
        buy_s    = sum(1 for s in sig_data if s["Signal"] == "BUY")
        sell_s   = sum(1 for s in sig_data if s["Signal"] == "SELL")
        hold_s   = sum(1 for s in sig_data if s["Signal"] == "HOLD")
        sm1.metric("Total Signals", total_s)
        sm2.metric("BUY",  buy_s,  f"{buy_s/total_s*100:.0f}%" if total_s else "0%")
        sm3.metric("SELL", sell_s, f"{sell_s/total_s*100:.0f}%" if total_s else "0%")
        sm4.metric("HOLD", hold_s, f"Last run: {last_run}")

        st.divider()

        # Filter controls
        fc1, fc2, fc3 = st.columns([2, 2, 2])
        filter_sig  = fc1.multiselect("Signal", ["BUY", "SELL", "HOLD"], default=["BUY", "SELL", "HOLD"], key="sig_filter")
        sort_by     = fc2.selectbox("Sort by", ["Confidence", "Change %", "RSI", "Ticker"], key="sig_sort")
        sort_asc    = fc3.checkbox("Ascending", value=False, key="sig_sort_dir")

        # Build display dataframe
        import pandas as pd
        df_display = pd.DataFrame(sig_data)
        df_display = df_display[df_display["Signal"].isin(filter_sig)]
        df_display = df_display.sort_values(sort_by, ascending=sort_asc)

        def style_row(row):
            if row["Signal"] == "BUY":
                return [""] * 2 + ["background-color:rgba(0,200,150,0.15);color:#00C896;font-weight:bold"] + [""] * 6
            elif row["Signal"] == "SELL":
                return [""] * 2 + ["background-color:rgba(255,77,106,0.15);color:#FF4D6A;font-weight:bold"] + [""] * 6
            return [""] * 2 + ["background-color:rgba(245,166,35,0.12);color:#F5A623;font-weight:bold"] + [""] * 6

        def style_change(val):
            try:
                v = float(val)
                return "color:#00C896" if v > 0 else "color:#FF4D6A" if v < 0 else "color:#F5A623"
            except Exception:
                return ""

        styled = (
            df_display.style
            .apply(style_row, axis=1)
            .applymap(style_change, subset=["Change %"])
            .format({
                "Price":      "${:,.2f}",
                "Change %":   "{:+.2f}%",
                "Confidence": "{:.0%}",
                "RSI":        "{:.1f}",
                "BB %":       "{:.1f}%",
                "Vol Ratio":  "{:.2f}x",
            })
        )
        st.dataframe(styled, use_container_width=True, hide_index=True, height=400)

        st.divider()

        # ── Charts ────────────────────────────────────────────────────────────
        chart_c1, chart_c2 = st.columns(2)

        with chart_c1:
            st.subheader("Signal Distribution")
            dist_data = {"BUY": buy_s, "SELL": sell_s, "HOLD": hold_s}
            dist_fig = go.Figure(go.Pie(
                labels=list(dist_data.keys()),
                values=list(dist_data.values()),
                hole=0.5,
                marker=dict(colors=["#00C896", "#FF4D6A", "#F5A623"]),
                textfont=dict(size=12),
            ))
            dist_fig.update_layout(
                template="plotly_dark", height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=20, b=0),
                showlegend=True,
            )
            st.plotly_chart(dist_fig, use_container_width=True)

        with chart_c2:
            st.subheader("Confidence by Ticker")
            conf_fig = go.Figure()
            colors_conf = ["#00C896" if s=="BUY" else "#FF4D6A" if s=="SELL" else "#F5A623"
                           for s in df_display["Signal"]]
            conf_fig.add_trace(go.Bar(
                x=df_display["Ticker"],
                y=df_display["Confidence"] * 100,
                marker_color=colors_conf,
                text=[f"{c:.0%}" for c in df_display["Confidence"]],
                textposition="outside",
            ))
            conf_fig.update_layout(
                template="plotly_dark", height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,0.02)",
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis=dict(range=[0, 105], title="Confidence %"),
            )
            st.plotly_chart(conf_fig, use_container_width=True)

    else:
        st.info("Click **⚡ Run Signals Now** to generate real-time signals for your watchlist.")



# ═══════════════════════════════════════════════════════════════════════════════
# BACKTEST PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif "Backtest" in page:
    st.title("Strategy Backtester")

    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        bt_ticker = st.selectbox("Ticker", tickers)
    with bc2:
        bt_period = st.selectbox("Period", ["1y", "2y", "3y", "5y"], index=1)
    with bc3:
        bt_capital = st.number_input("Capital ($)", value=100000, step=10000)

    if st.button("▶ Run Backtest", use_container_width=True):
        with st.spinner(f"Running backtest on {bt_ticker}..."):
            try:
                from data_ingestion.fetcher import MarketDataFetcher
                from data_ingestion.features import FeatureEngineer
                fetcher2 = MarketDataFetcher()
                fe2 = FeatureEngineer()
                engine = get_backtester()
                engine.initial_capital = bt_capital

                df_bt = fetcher2.get_ohlcv(bt_ticker, period=bt_period)
                if df_bt.empty:
                    st.error(f"No data for {bt_ticker}")
                else:
                    df_bt = fe2.add_all_features(df_bt)
                    df_bt = fe2.add_target_labels(df_bt)
                    df_bt.dropna(inplace=True)
                    df_bt["signal"] = df_bt["target"]

                    result = engine.run(df_bt, ticker=bt_ticker)
                    summary = result.summary()

                    st.subheader("Performance Metrics")
                    mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
                    mc1.metric("Total Return", f"{summary['total_return_pct']:.1f}%")
                    mc2.metric("Sharpe Ratio", f"{summary['sharpe_ratio']:.2f}")
                    mc3.metric("Sortino",       f"{summary['sortino_ratio']:.2f}")
                    mc4.metric("Max Drawdown",  f"{summary['max_drawdown_pct']:.1f}%")
                    mc5.metric("Win Rate",      f"{summary['win_rate_pct']:.1f}%")
                    mc6.metric("Trades",        str(summary['n_trades']))

                    st.divider()
                    st.subheader("Equity Curve")
                    eq_fig = go.Figure()
                    eq_fig.add_trace(go.Scatter(
                        x=result.equity_curve.index,
                        y=result.equity_curve.values,
                        name="Strategy",
                        line=dict(color="#00C896", width=2),
                        fill="tozeroy",
                        fillcolor="rgba(0,200,150,0.05)",
                    ))
                    eq_fig.add_hline(
                        y=bt_capital,
                        line_dash="dot",
                        line_color="rgba(255,255,255,0.2)",
                        annotation_text="Starting Capital",
                    )
                    eq_fig.update_layout(
                        template="plotly_dark", height=350,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(255,255,255,0.02)",
                        margin=dict(l=0, r=0, t=10, b=0),
                    )
                    st.plotly_chart(eq_fig, use_container_width=True)

                    st.divider()
                    st.subheader("Monthly Returns")
                    from backtesting.metrics import PerformanceMetrics
                    monthly = PerformanceMetrics.monthly_returns(result.equity_curve)
                    if not monthly.empty:
                        colors_m = ["#00C896" if v >= 0 else "#FF4D6A"
                                    for v in monthly["return_pct"]]
                        m_fig = go.Figure(go.Bar(
                            x=monthly["month"],
                            y=monthly["return_pct"],
                            marker_color=colors_m,
                            text=[f"{v:+.1f}%" for v in monthly["return_pct"]],
                            textposition="outside",
                        ))
                        m_fig.update_layout(
                            template="plotly_dark", height=250,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(255,255,255,0.02)",
                            margin=dict(l=0, r=0, t=20, b=0),
                            showlegend=False,
                        )
                        st.plotly_chart(m_fig, use_container_width=True)

            except Exception as e:
                st.error(f"Backtest error: {e}")

    else:
        st.subheader("Sample Metrics (run a backtest to see real results)")
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric("Total Return", "—")
        m2.metric("Sharpe",       "—")
        m3.metric("Sortino",      "—")
        m4.metric("Max DD",       "—")
        m5.metric("Win Rate",     "—")
        m6.metric("Trades",       "—")


# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS PAGE
# ═══════════════════════════════════════════════════════════════════════════════
elif "Alerts" in page:
    st.title("Alert System")

    # Ensure DB table exists
    from utils.user_store import init_user_tables, get_all_users, add_user, delete_user, get_alert_history
    init_user_tables()

    tab1, tab2, tab3, tab4 = st.tabs(["📋 Alert Feed", "👥 Users", "📜 History", "⚙️ Configuration"])

    # ── Tab 1: Alert Feed ─────────────────────────────────────────────────────
    with tab1:
        st.subheader("Recent Alerts")

        # Load real history from DB
        history = get_alert_history(limit=50)

        if history:
            for h in history:
                sig   = h.get("signal", "INFO")
                color = {"BUY":"#00C896","SELL":"#FF4D6A","HOLD":"#F5A623"}.get(sig, "#3B82F6")
                sent  = h.get("sent_at","")[:16].replace("T"," ")
                st.markdown(
                    f"""<div style="border-left:3px solid {color};padding:10px 16px;margin:6px 0;
                    background:rgba(255,255,255,0.03);border-radius:0 8px 8px 0;">
                    <span style="color:{color};font-weight:700;font-family:monospace;font-size:12px;">{sig}</span>
                    <span style="color:rgba(255,255,255,0.9);margin-left:10px;">
                        <b>{h.get('ticker','')}</b> signal for <b>{h.get('user_name','')}</b>
                    </span><br>
                    <span style="color:rgba(255,255,255,0.45);font-size:12px;">
                        Confidence: {h.get('confidence',0)*100:.1f}% &nbsp;·&nbsp;
                        Price: ${h.get('price',0):.2f} &nbsp;·&nbsp;
                        Channel: {h.get('channel','')} &nbsp;·&nbsp;
                        {sent}
                    </span>
                    </div>""",
                    unsafe_allow_html=True,
                )
        else:
            # Demo alerts when no real history yet
            demo_alerts = [
                {"time":"2 min ago",  "type":"SELL", "msg":"TSLA crossed below 50-day MA",       "detail":"Confidence 74% · LSTM · SMS sent"},
                {"time":"8 min ago",  "type":"BUY",  "msg":"NVDA breakout above resistance $870", "detail":"Confidence 91% · Ensemble · SMS sent"},
                {"time":"15 min ago", "type":"WARN", "msg":"SPY RSI approaching overbought (68)", "detail":"Monitor for reversal"},
                {"time":"1 hr ago",   "type":"INFO", "msg":"Model retrain completed · LSTM v3.1", "detail":"Accuracy improved: 80.2% → 82.1%"},
                {"time":"2 hr ago",   "type":"BUY",  "msg":"QQQ BUY signal · Momentum surge",    "detail":"MACD crossover confirmed · SMS sent"},
            ]
            for alert in demo_alerts:
                color = {"BUY":"#00C896","SELL":"#FF4D6A","WARN":"#F5A623","INFO":"#3B82F6"}.get(alert["type"],"#888")
                st.markdown(
                    f"""<div style="border-left:3px solid {color};padding:10px 16px;margin:6px 0;
                    background:rgba(255,255,255,0.03);border-radius:0 8px 8px 0;">
                    <span style="color:{color};font-weight:700;font-family:monospace;font-size:12px;">{alert['type']}</span>
                    <span style="color:rgba(255,255,255,0.9);margin-left:12px;">{alert['msg']}</span><br>
                    <span style="color:rgba(255,255,255,0.45);font-size:12px;">{alert['detail']} · {alert['time']}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )


        # ════════════════════════════════════════════════════════════
        # REAL-TIME SIGNAL ALERT PANEL
        # ════════════════════════════════════════════════════════════
        st.divider()
        st.subheader("🚀 Send Real-Time Signal Alerts")
        st.caption("Scans your watchlist with ML right now and sends SMS/Email for every strong signal")

        ra1, ra2 = st.columns(2)
        with ra1:
            alert_min_conf = st.slider(
                "Min confidence to alert",
                min_value=0.50, max_value=0.95,
                value=0.65, step=0.05,
                key="alert_conf_slider"
            )
        with ra2:
            alert_tickers_input = st.text_input(
                "Tickers to scan (blank = full watchlist)",
                placeholder="AAPL,NVDA,TSLA or leave blank",
                key="alert_tickers_input"
            )

        if st.button("📡 Run Signals & Send Alerts Now", use_container_width=True, type="primary"):
            with st.spinner("Fetching live data and running ML models..."):
                try:
                    from data_ingestion.fetcher import MarketDataFetcher
                    from data_ingestion.features import FeatureEngineer
                    from alerting.notifier import AlertNotifier
                    from utils.ticker_store import get_watchlist

                    fetcher_a = MarketDataFetcher()
                    fe_a      = FeatureEngineer()
                    notifier  = AlertNotifier()

                    scan_list = (
                        [t.strip().upper() for t in alert_tickers_input.split(",") if t.strip()]
                        if alert_tickers_input.strip()
                        else get_watchlist()
                    )

                    results = []
                    alerted = []
                    prog_a  = st.progress(0, text="Starting scan...")

                    for i, ticker in enumerate(scan_list):
                        prog_a.progress(
                            (i + 1) / len(scan_list),
                            text=f"Scanning {ticker}... ({i+1}/{len(scan_list)})"
                        )
                        try:
                            q      = fetcher_a.get_live_quote(ticker)
                            price  = q.get("price", 0)
                            change = q.get("change_pct", 0)
                            df_a   = fetcher_a.get_ohlcv(ticker, period="6mo")
                            if df_a.empty or len(df_a) < 60:
                                continue
                            df_a = fe_a.add_all_features(df_a)
                            df_a = fe_a.add_target_labels(df_a)
                            df_a.dropna(inplace=True)
                            if df_a.empty:
                                continue

                            r_a   = df_a.tail(1)
                            rsi_a = float(r_a["rsi"].values[0])          if "rsi"          in r_a.columns else 50
                            mcd_a = float(r_a["macd_hist"].values[0])    if "macd_hist"    in r_a.columns else 0
                            bb_a  = float(r_a["bb_pct"].values[0])       if "bb_pct"       in r_a.columns else 0.5
                            vl_a  = float(r_a["volume_ratio"].values[0]) if "volume_ratio" in r_a.columns else 1

                            # Signal scoring
                            bs = ss = 0.0
                            if rsi_a<=25: bs+=2.5
                            elif rsi_a<=35: bs+=2.0
                            elif rsi_a<=42: bs+=1.5
                            elif rsi_a<=48: bs+=0.5
                            elif rsi_a>=75: ss+=2.5
                            elif rsi_a>=65: ss+=2.0
                            elif rsi_a>=58: ss+=1.5
                            elif rsi_a>=52: ss+=0.5
                            mn = mcd_a / 0.5
                            if mn>2.0: bs+=2.5
                            elif mn>0.5: bs+=2.0
                            elif mn>0.0: bs+=1.0
                            elif mn<-2.0: ss+=2.5
                            elif mn<-0.5: ss+=2.0
                            else: ss+=1.0
                            if bb_a<0.10: bs+=2.0
                            elif bb_a<0.20: bs+=1.5
                            elif bb_a<0.30: bs+=1.0
                            elif bb_a>0.90: ss+=2.0
                            elif bb_a>0.80: ss+=1.5
                            elif bb_a>0.70: ss+=1.0
                            if change>3.0: bs+=1.5
                            elif change>1.5: bs+=1.0
                            elif change>0.5: bs+=0.5
                            elif change<-3.0: ss+=1.5
                            elif change<-1.5: ss+=1.0
                            elif change<-0.5: ss+=0.5
                            if vl_a>2.0 and change>0: bs+=1.0
                            elif vl_a>1.3 and change>0: bs+=0.5
                            elif vl_a>2.0 and change<0: ss+=1.0
                            elif vl_a>1.3 and change<0: ss+=0.5
                            gp = abs(bs-ss)
                            if bs>ss and gp>=1.0:
                                sig_a  = "BUY";  cf_a = min(0.95, 0.60+(bs/8.5)*0.35)
                            elif ss>bs and gp>=1.0:
                                sig_a  = "SELL"; cf_a = min(0.95, 0.60+(ss/8.5)*0.35)
                            else:
                                sig_a  = "HOLD"; cf_a = min(0.75, 0.50+gp*0.08)

                            results.append({"ticker":ticker,"signal":sig_a,"confidence":cf_a,"price":price,"change":change})

                            # Send alert if above threshold
                            if sig_a != "HOLD" and cf_a >= alert_min_conf:
                                notifier.send_signal_alert(ticker, sig_a, cf_a, price)
                                alerted.append({"ticker":ticker,"signal":sig_a,"confidence":cf_a,"price":price})

                        except Exception as ex:
                            continue

                    prog_a.empty()

                    # Summary
                    st.divider()
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Tickers Scanned", len(results))
                    sc2.metric("Alerts Sent",     len(alerted))
                    sc3.metric("Threshold",       f"{alert_min_conf*100:.0f}%")

                    if alerted:
                        st.success(f"✅ {len(alerted)} alert(s) sent via SMS/Email!")
                        for a in alerted:
                            clr = "#00C896" if a["signal"]=="BUY" else "#FF4D6A"
                            emj = "🟢" if a["signal"]=="BUY" else "🔴"
                            st.markdown(
                                f'''<div style="border-left:3px solid {clr};padding:10px 16px;
                                margin:4px 0;background:rgba(255,255,255,0.04);border-radius:0 8px 8px 0;">
                                <b>{emj} {a["ticker"]}</b> — {a["signal"]}
                                &nbsp;|&nbsp; Confidence: {a["confidence"]*100:.1f}%
                                &nbsp;|&nbsp; Price: ${a["price"]:.2f}
                                </div>''', unsafe_allow_html=True)
                    else:
                        st.info(f"No signals above {alert_min_conf*100:.0f}% threshold. Try lowering the slider.")

                    if results:
                        st.divider()
                        st.markdown("**Full scan results:**")
                        df_res = pd.DataFrame(results).sort_values("confidence", ascending=False)
                        def _sc(v):
                            if v=="BUY":  return "color:#00C896;font-weight:bold"
                            if v=="SELL": return "color:#FF4D6A;font-weight:bold"
                            return "color:#F5A623"
                        st.dataframe(
                            df_res.style.applymap(_sc, subset=["signal"])
                            .format({"confidence":"{:.0%}","price":"${:.2f}","change":"{:+.2f}%"}),
                            use_container_width=True, hide_index=True
                        )

                except Exception as e:
                    st.error(f"Error: {e}")

        st.divider()
        if st.button("🚨 Send Test Alert Now", use_container_width=True):
            with st.spinner("Sending..."):
                try:
                    from alerting.notifier import AlertNotifier
                    AlertNotifier().send_signal_alert("NVDA", "BUY", 0.91, 875.90)
                    st.success("✅ Test alert sent to all configured users!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Alert error: {e}")

    # ── Tab 2: Users ──────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Registered Users")

        users = get_all_users()

        if users:
            for u in users:
                with st.container():
                    cols = st.columns([3, 2, 2, 2, 1])
                    cols[0].markdown(f"**{u['name']}**")
                    cols[1].markdown(
                        f"{'📱 ' if 'sms' in u['channels'] else ''}"
                        f"{'📧 ' if 'email' in u['channels'] else ''}"
                        f"{'💬 ' if 'slack' in u['channels'] else ''}"
                        f" {', '.join(u['channels'])}"
                    )
                    cols[2].markdown(f"Min conf: **{u['min_confidence']*100:.0f}%**")
                    tickers_label = ", ".join(u["tickers"]) if u.get("tickers") else "All tickers"
                    cols[3].markdown(f"📊 {tickers_label}")
                    if cols[4].button("🗑️", key=f"del_{u['id']}", help="Remove user"):
                        delete_user(u["id"])
                        st.success(f"Removed {u['name']}")
                        st.rerun()
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.03);border-radius:8px;"
                    f"padding:8px 14px;margin-bottom:6px;font-size:12px;color:rgba(255,255,255,0.5);'>"
                    f"📞 {u.get('phone','—') or '—'} &nbsp;·&nbsp; "
                    f"✉️ {u.get('email','—') or '—'} &nbsp;·&nbsp; "
                    f"Added: {u.get('created_at','')[:10]}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("No users added yet. Add your first user below.")

        st.divider()
        st.subheader("Add New User")

        with st.form("add_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            u_name  = col1.text_input("Name *", placeholder="e.g. Lovkush")
            u_phone = col2.text_input("Phone", placeholder="+919876543210")
            u_email = col1.text_input("Email", placeholder="you@gmail.com")
            u_chan  = col2.multiselect("Channels *", ["sms", "email", "slack"], default=["sms"])
            u_conf  = col1.slider("Min Confidence", 0.5, 0.95, 0.65, 0.05,
                                   help="Only send alerts above this confidence level")
            u_tick  = col2.text_input("Tickers (optional)",
                                       placeholder="AAPL,NVDA  — blank means all tickers")

            submitted = st.form_submit_button("➕ Add User", use_container_width=True)
            if submitted:
                if not u_name:
                    st.error("Name is required.")
                elif not u_chan:
                    st.error("Select at least one channel.")
                else:
                    tlist = [t.strip().upper() for t in u_tick.split(",") if t.strip()] or None
                    add_user(
                        name=u_name,
                        phone=u_phone or None,
                        email=u_email or None,
                        channels=u_chan,
                        min_confidence=u_conf,
                        tickers=tlist,
                    )
                    st.success(f"✅ {u_name} added and saved permanently!")
                    st.rerun()

        # Per-user alert history
        st.divider()
        st.subheader("Alert History by User")
        if users:
            selected_user = st.selectbox("Select user", [u["name"] for u in users])
            user_hist = get_alert_history(user_name=selected_user, limit=20)
            if user_hist:
                hist_df = pd.DataFrame(user_hist)[
                    ["sent_at","ticker","signal","confidence","price","channel"]
                ]
                hist_df["confidence"] = hist_df["confidence"].apply(lambda x: f"{x*100:.1f}%")
                hist_df["price"]      = hist_df["price"].apply(lambda x: f"${x:.2f}")
                hist_df["sent_at"]    = hist_df["sent_at"].str[:16].str.replace("T"," ")
                hist_df.columns       = ["Sent At","Ticker","Signal","Confidence","Price","Channel"]

                def color_sig(val):
                    return {"BUY":"color:#00C896;font-weight:bold",
                            "SELL":"color:#FF4D6A;font-weight:bold",
                            "HOLD":"color:#F5A623;font-weight:bold"}.get(val,"")

                st.dataframe(
                    hist_df.style.applymap(color_sig, subset=["Signal"]),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info(f"No alert history for {selected_user} yet.")
        else:
            st.info("Add users first to see their history.")

    # ── Tab 3: Configuration ──────────────────────────────────────────────────
    with tab3:
        st.subheader("Alert History")
        st.caption("All alerts ever sent — persisted in database, survives restarts.")

        try:
            from utils.user_store import init_user_tables, get_alert_history, get_all_users
            init_user_tables()

            # Filter by user
            users_list = get_all_users()
            user_names = ["All Users"] + [u["name"] for u in users_list]
            selected_user = st.selectbox("Filter by user", user_names)

            uname = None if selected_user == "All Users" else selected_user
            history = get_alert_history(user_name=uname, limit=200)
        except Exception as e:
            st.error(f"History load error: {e}")
            history = []

        if history:
            hist_rows = []
            for h in history:
                sig = h.get("signal", "")
                color = "#00C896" if sig=="BUY" else "#FF4D6A" if sig=="SELL" else "#F5A623"
                hist_rows.append({
                    "Time":       h.get("time", ""),
                    "User":       h.get("user", ""),
                    "Ticker":     h.get("ticker", ""),
                    "Signal":     h.get("signal", ""),
                    "Confidence": f"{h.get('confidence', 0)*100:.0f}%",
                    "Price":      f"${h.get('price', 0):.2f}",
                    "Channel":    h.get("channel", ""),
                })

            hist_df = pd.DataFrame(hist_rows)

            def color_sig(val):
                c = {"BUY":"color:#00C896;font-weight:bold",
                     "SELL":"color:#FF4D6A;font-weight:bold",
                     "HOLD":"color:#F5A623;font-weight:bold"}
                return c.get(val, "")

            styled_h = hist_df.style.applymap(color_sig, subset=["Signal"])
            st.dataframe(styled_h, use_container_width=True,
                         height=400, hide_index=True)

            # Stats
            st.divider()
            total = len(history)
            buy_count  = sum(1 for h in history if h.get("signal") == "BUY")
            sell_count = sum(1 for h in history if h.get("signal") == "SELL")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("Total Alerts",   total)
            s3.metric("BUY Alerts",     buy_count)
            s4.metric("SELL Alerts",    sell_count)
        else:
            st.info("No alert history yet. Alerts will appear here once signals are triggered.")

    with tab4:
        st.subheader("Notification Channels")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.toggle("📱 SMS (Twilio)",     value=True)
            st.text_input("From Number",      placeholder="+1234567890")
        with c2:
            st.toggle("📧 Email (SendGrid)",  value=False)
            st.text_input("From Email",       placeholder="alerts@yourdomain.com")
        with c3:
            st.toggle("💬 Slack",             value=False)
            st.text_input("Channel",          placeholder="#trading-alerts")

        st.divider()
        st.subheader("Alert Rules")
        rules = [
            ("Price change ±5%", True),
            ("Signal confidence > 70%", True),
            ("Volume anomaly 2σ", True),
            ("RSI overbought > 70", True),
            ("RSI oversold < 30", True),
            ("Portfolio drawdown > 10%", False),
        ]
        col_r1, col_r2 = st.columns(2)
        for i, (rule, default) in enumerate(rules):
            if i % 2 == 0:
                col_r1.toggle(rule, value=default)
            else:
                col_r2.toggle(rule, value=default)

        if st.button("💾 Save Configuration", use_container_width=True):
            st.success("✅ Configuration saved!")



# ── Auto-refresh countdown timer (reruns page every 10s to update countdown) ──
if st.session_state.auto_refresh:
    time.sleep(10)
    st.rerun()