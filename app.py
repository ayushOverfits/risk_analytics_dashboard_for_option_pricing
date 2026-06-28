import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# Import your custom modules
from models.option import Option
from models.pricer import PricingEngine
from models.market_data import MarketData

st.set_page_config(page_title="Quantitative Options Engine", layout="wide", initial_sidebar_state="collapsed")
st.title("Quantitative Options Risk Engine")
st.markdown("A full-stack institutional options dashboard blending theoretical Greek sensitivities with live market data.")

engine = PricingEngine()

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs([
    "1. Theoretical Engine (Simulation)", 
    "2. Live Market Data (Real Greeks)", 
    "3. Economic Insight"
])

# ==============================================================================
# TAB 1: THEORETICAL ENGINE
# ==============================================================================
with tab1:
    st.header("Theoretical Parameter Controls")
    st.markdown("Adjust the sliders below to simulate how option Greeks behave as the **Underlying Stock Price** changes.")
    
    # Inputs localized to Tab 1
    col1, col2, col3, col4 = st.columns(4)
    sim_K = col1.number_input("Strike Price (K)", value=100.0, step=5.0)
    sim_T = col2.slider("Time to Expiry (T) in Years", min_value=0.01, max_value=2.0, value=0.50, step=0.05)
    sim_sigma = col3.slider("Volatility (σ)", min_value=0.05, max_value=1.0, value=0.20, step=0.05)
    sim_r = col4.slider("Risk-Free Rate (r)", min_value=0.0, max_value=0.15, value=0.05, step=0.01)

    st.divider()

    # Pre-calculate theoretical arrays
    S_values = np.linspace(sim_K * 0.5, sim_K * 1.5, 100)
    call_deltas, put_deltas, gammas, vegas, call_thetas, put_thetas, call_rhos, put_rhos = [], [], [], [], [], [], [], []

    # Handle method name dynamically just in case pricer.py uses the older or newer naming convention
    greeks_method = getattr(engine, 'greeks', getattr(engine, 'calculate_greeks', None))

    for S in S_values:
        call_opt = Option(S, sim_K, sim_T, sim_r, sim_sigma, 0.0, "call")
        put_opt = Option(S, sim_K, sim_T, sim_r, sim_sigma, 0.0, "put")
        
        cg = greeks_method(call_opt)
        pg = greeks_method(put_opt)
        
        call_deltas.append(cg['delta'])
        put_deltas.append(pg['delta'])
        gammas.append(cg['gamma']) 
        vegas.append(cg['vega'])   
        call_thetas.append(cg['theta'])
        put_thetas.append(pg['theta'])
        call_rhos.append(cg.get('rho', 0))
        put_rhos.append(pg.get('rho', 0))

    # 2D Plots
    st.subheader("2D Greek Curves (vs. Stock Price)")
    plot_col1, plot_col2 = st.columns(2)
    
    with plot_col1:
        fig_delta = go.Figure()
        fig_delta.add_trace(go.Scatter(x=S_values, y=call_deltas, mode='lines', name='Call Delta', line=dict(color='blue')))
        fig_delta.add_trace(go.Scatter(x=S_values, y=put_deltas, mode='lines', name='Put Delta', line=dict(color='red')))
        fig_delta.add_vline(x=sim_K, line_dash="dash", line_color="gray", annotation_text="Strike Price")
        fig_delta.update_layout(title="Delta (Δ)", xaxis_title="Stock Price", yaxis_title="Delta", hovermode="x unified")
        st.plotly_chart(fig_delta, use_container_width=True)
        
        fig_vega = go.Figure()
        fig_vega.add_trace(go.Scatter(x=S_values, y=vegas, mode='lines', name='Call/Put Vega', line=dict(color='green')))
        fig_vega.add_vline(x=sim_K, line_dash="dash", line_color="gray", annotation_text="Strike Price")
        fig_vega.update_layout(title="Vega (ν)", xaxis_title="Stock Price", yaxis_title="Vega", hovermode="x unified")
        st.plotly_chart(fig_vega, use_container_width=True)

        fig_rho = go.Figure()
        fig_rho.add_trace(go.Scatter(x=S_values, y=call_rhos, mode='lines', name='Call Rho', line=dict(color='orange')))
        fig_rho.add_trace(go.Scatter(x=S_values, y=put_rhos, mode='lines', name='Put Rho', line=dict(color='brown')))
        fig_rho.add_vline(x=sim_K, line_dash="dash", line_color="gray", annotation_text="Strike Price")
        fig_rho.update_layout(title="Rho (ρ)", xaxis_title="Stock Price", yaxis_title="Rho", hovermode="x unified")
        st.plotly_chart(fig_rho, use_container_width=True)

    with plot_col2:
        fig_gamma = go.Figure()
        fig_gamma.add_trace(go.Scatter(x=S_values, y=gammas, mode='lines', name='Call/Put Gamma', line=dict(color='purple')))
        fig_gamma.add_vline(x=sim_K, line_dash="dash", line_color="gray", annotation_text="Strike Price")
        fig_gamma.update_layout(title="Gamma (Γ)", xaxis_title="Stock Price", yaxis_title="Gamma", hovermode="x unified")
        st.plotly_chart(fig_gamma, use_container_width=True)
        
        fig_theta = go.Figure()
        fig_theta.add_trace(go.Scatter(x=S_values, y=call_thetas, mode='lines', name='Call Theta', line=dict(color='blue')))
        fig_theta.add_trace(go.Scatter(x=S_values, y=put_thetas, mode='lines', name='Put Theta', line=dict(color='red')))
        fig_theta.add_vline(x=sim_K, line_dash="dash", line_color="gray", annotation_text="Strike Price")
        fig_theta.update_layout(title="Theta (Θ) [Daily Decay]", xaxis_title="Stock Price", yaxis_title="Theta", hovermode="x unified")
        st.plotly_chart(fig_theta, use_container_width=True)
        
    # 3D Plots
    st.subheader("3D Risk Surfaces (Time vs. Stock Price vs. Risk)")
    T_values = np.linspace(0.01, 1.0, 50) 
    S_mesh, T_mesh = np.meshgrid(S_values, T_values)
    Gamma_surf, Theta_surf = np.zeros_like(S_mesh), np.zeros_like(S_mesh)
    
    for i in range(len(T_values)):
        for j in range(len(S_values)):
            opt = Option(S_mesh[i, j], sim_K, T_mesh[i, j], sim_r, sim_sigma, 0.0, "call")
            greeks = greeks_method(opt)
            Gamma_surf[i, j] = greeks['gamma']
            Theta_surf[i, j] = greeks['theta']

    surf_col1, surf_col2 = st.columns(2)
    with surf_col1:
        fig_surf_gamma = go.Figure(data=[go.Surface(z=Gamma_surf, x=S_values, y=T_values, colorscale='Purples')])
        fig_surf_gamma.update_layout(title='3D Gamma Surface', scene=dict(xaxis_title='Stock Price', yaxis_title='Time to Expiry', zaxis_title='Gamma'), margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig_surf_gamma, use_container_width=True)

    with surf_col2:
        fig_surf_theta = go.Figure(data=[go.Surface(z=Theta_surf, x=S_values, y=T_values, colorscale='Reds_r')])
        fig_surf_theta.update_layout(title='3D Theta Surface', scene=dict(xaxis_title='Stock Price', yaxis_title='Time to Expiry', zaxis_title='Theta'), margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig_surf_theta, use_container_width=True)

# ==============================================================================
# TAB 2: LIVE MARKET DATA
# ==============================================================================
with tab2:
    st.header("Live Market Data & Options Chain Greeks")
    st.markdown("Pull live data for any stock and plot the true Greek sensitivities across the current **Strike Prices**.")
    
    live_col1, live_col2, live_col3 = st.columns([1, 1, 2])
    live_ticker = live_col1.text_input("Ticker Symbol", "QQQ").upper()
    
    try:
        with st.spinner(f"Fetching {live_ticker} data..."):
            md = MarketData(live_ticker)
            live_price = md.get_current_stock_price()
            expirations = md.get_expirations()
            
            live_col3.info(f"**Live {live_ticker} Price: ${live_price:.2f}**")
            
            default_idx = min(4, len(expirations) - 1) if expirations else 0
            selected_expiry = live_col2.selectbox("Expiration Date", expirations, index=default_idx)
            
            if selected_expiry:
                calls, puts = md.get_options_chain(selected_expiry)
                expiry_date = datetime.strptime(selected_expiry, "%Y-%m-%d")
                T_live = max((expiry_date - datetime.now()).days / 365.0, 0.001)
                
                # Compute Greeks for the Live Calls
                c_strikes, c_deltas, c_gammas, c_vegas, c_thetas, c_rhos = [], [], [], [], [], []
                for _, row in calls.iterrows():
                    opt = Option(S=live_price, K=row['strike'], T=T_live, r=0.05, sigma=row['impliedVolatility'], q=0.0, option_type="call")
                    g = greeks_method(opt)
                    c_strikes.append(row['strike'])
                    c_deltas.append(g['delta'])
                    c_gammas.append(g['gamma'])
                    c_vegas.append(g['vega'])
                    c_thetas.append(g['theta'])
                    c_rhos.append(g.get('rho', 0))
                
                # Compute Greeks for the Live Puts
                p_strikes, p_deltas, p_gammas, p_vegas, p_thetas, p_rhos = [], [], [], [], [], []
                for _, row in puts.iterrows():
                    opt = Option(S=live_price, K=row['strike'], T=T_live, r=0.05, sigma=row['impliedVolatility'], q=0.0, option_type="put")
                    g = greeks_method(opt)
                    p_strikes.append(row['strike'])
                    p_deltas.append(g['delta'])
                    p_gammas.append(g['gamma'])
                    p_vegas.append(g['vega'])
                    p_thetas.append(g['theta'])
                    p_rhos.append(g.get('rho', 0))

                st.divider()
                st.subheader(f"Real-World Sensitivities across Strike Prices ({selected_expiry})")
                
                # Plot Live Greeks vs Strike
                l_col1, l_col2 = st.columns(2)
                
                with l_col1:
                    fig_ld = go.Figure()
                    fig_ld.add_trace(go.Scatter(x=c_strikes, y=c_deltas, mode='lines+markers', name='Call Delta', line=dict(color='blue')))
                    fig_ld.add_trace(go.Scatter(x=p_strikes, y=p_deltas, mode='lines+markers', name='Put Delta', line=dict(color='red')))
                    fig_ld.add_vline(x=live_price, line_dash="dash", line_color="black", annotation_text="Current Stock Price")
                    fig_ld.update_layout(title="Live Delta vs. Strike", xaxis_title="Strike Price", yaxis_title="Delta", hovermode="x unified")
                    st.plotly_chart(fig_ld, use_container_width=True)
                    
                    fig_lv = go.Figure()
                    fig_lv.add_trace(go.Scatter(x=c_strikes, y=c_vegas, mode='lines+markers', name='Call Vega', line=dict(color='green')))
                    fig_lv.add_trace(go.Scatter(x=p_strikes, y=p_vegas, mode='lines+markers', name='Put Vega', line=dict(color='lightgreen')))
                    fig_lv.add_vline(x=live_price, line_dash="dash", line_color="black", annotation_text="Current Stock Price")
                    fig_lv.update_layout(title="Live Vega vs. Strike", xaxis_title="Strike Price", yaxis_title="Vega", hovermode="x unified")
                    st.plotly_chart(fig_lv, use_container_width=True)

                    fig_lr = go.Figure()
                    fig_lr.add_trace(go.Scatter(x=c_strikes, y=c_rhos, mode='lines+markers', name='Call Rho', line=dict(color='orange')))
                    fig_lr.add_trace(go.Scatter(x=p_strikes, y=p_rhos, mode='lines+markers', name='Put Rho', line=dict(color='brown')))
                    fig_lr.add_vline(x=live_price, line_dash="dash", line_color="black", annotation_text="Current Stock Price")
                    fig_lr.update_layout(title="Live Rho vs. Strike", xaxis_title="Strike Price", yaxis_title="Rho", hovermode="x unified")
                    st.plotly_chart(fig_lr, use_container_width=True)

                with l_col2:
                    fig_lg = go.Figure()
                    fig_lg.add_trace(go.Scatter(x=c_strikes, y=c_gammas, mode='lines+markers', name='Call Gamma', line=dict(color='purple')))
                    fig_lg.add_trace(go.Scatter(x=p_strikes, y=p_gammas, mode='lines+markers', name='Put Gamma', line=dict(color='violet')))
                    fig_lg.add_vline(x=live_price, line_dash="dash", line_color="black", annotation_text="Current Stock Price")
                    fig_lg.update_layout(title="Live Gamma vs. Strike", xaxis_title="Strike Price", yaxis_title="Gamma", hovermode="x unified")
                    st.plotly_chart(fig_lg, use_container_width=True)

                    fig_lt = go.Figure()
                    fig_lt.add_trace(go.Scatter(x=c_strikes, y=c_thetas, mode='lines+markers', name='Call Theta', line=dict(color='blue')))
                    fig_lt.add_trace(go.Scatter(x=p_strikes, y=p_thetas, mode='lines+markers', name='Put Theta', line=dict(color='red')))
                    fig_lt.add_vline(x=live_price, line_dash="dash", line_color="black", annotation_text="Current Stock Price")
                    fig_lt.update_layout(title="Live Theta vs. Strike", xaxis_title="Strike Price", yaxis_title="Theta (Daily)", hovermode="x unified")
                    st.plotly_chart(fig_lt, use_container_width=True)
                    
    except Exception as e:
        st.error(f"Could not load data for {live_ticker}. Please check the ticker symbol or your internet connection. Error: {e}")

# ==============================================================================
# TAB 3: ECONOMIC INSIGHT
# ==============================================================================
with tab3:
    st.header("Economic Interpretation & Institutional Insights")

    st.markdown("""
    ### 1. The Core Sensitivities
    * **Delta (Δ) [Directional Risk]:** The rate of change of the option's price relative to the underlying asset. A Call Delta of 0.50 means the option gains $0.50 for every $1.00 the stock rises.
    * **Gamma (Γ) [Acceleration Risk]:** The rate of change of Delta. High Gamma means your Delta will swing violently with small stock movements. It peaks At-The-Money and explodes as expiration nears.
    * **Vega (ν) [Volatility Risk]:** The sensitivity to a 1% change in Implied Volatility. Options furthest from expiration carry the highest Vega.
    * **Theta (Θ) [Time Decay]:** The daily depreciation in option value. It is the "rent" paid by option buyers.
    * **Rho (ρ) [Interest Rate Risk]:** The sensitivity of an option's price to a 1% change in the risk-free interest rate. Calls generally have positive Rho (increase in value as rates rise), while puts have negative Rho (decrease in value as rates rise).
    
    ### 2. The Gamma-Theta Tradeoff
    In quantitative finance, there is no free lunch. If you want to hold high **Gamma** (the explosive upside potential of a fast-moving stock), you must pay for it with heavy **Theta** (your position bleeds cash every day). Conversely, if you want to collect positive **Theta** by selling options, you must absorb the risk of short **Gamma** (a sudden stock crash will compound your losses exponentially).
    """)