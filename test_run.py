# Import the blueprints we just built
from models.option import Option
from models.pricer import PricingEngine
from models.market_data import MarketData
import matplotlib.pyplot as plt
from datetime import datetime
import math

# 1. Build an Apple Call Option Object
# Dividend yield is 1%
apple_call = Option(S=150, K=155, T=0.5, r=0.05, sigma=0.20, q=0.01, option_type="call")

# 2. Build an Apple Put Option Object (same stats, betting down)
apple_put = Option(S=150, K=155, T=0.5, r=0.05, sigma=0.20, q=0.01, option_type="put")

# 3. Turn on the Calculator
engine = PricingEngine()

# 4. Feed the options into the engine
call_price = engine.calculate_bsm_price(apple_call)
put_price = engine.calculate_bsm_price(apple_put)

# 5. Print the results!
print(f"--- Black-Scholes-Merton Pricing ---")
print(f"Fair Value of Apple Call: ${call_price:.2f}")
print(f"Fair Value of Apple Put:  ${put_price:.2f}")


# Calculate the Greeks for the Call Option
call_greeks = engine.calculate_greeks(apple_call)

print(f"\n--- Apple Call Option Greeks ---")
print(f"Delta: {call_greeks['delta']:.4f}  (Price changes this much for every $1 stock move)")
print(f"Gamma: {call_greeks['gamma']:.4f}  (Delta changes this much for every $1 stock move)")
print(f"Theta: {call_greeks['theta']:.4f}  (Option loses this much value every single day)")
print(f"Vega:  {call_greeks['vega']:.4f}  (Price changes this much if Volatility jumps 1%)")
print(f"Rho:   {call_greeks['rho']:.4f}  (Price changes this much if Interest Rates jump 1%)")




# LIVE MARKET DATA INTEGRATION
print("\n--- Phase 3: Live Market Data Integration ---")
# 1. Initialize the data fetcher for Apple
aapl_data = MarketData("AAPL")
live_S = aapl_data.get_current_stock_price()
print(f"Live AAPL Stock Price: ${live_S:.2f}")

# 2. Get the nearest expiration date
expirations = aapl_data.get_expirations()
nearest_expiry = expirations[0]
print(f"Analyzing Options Expiring on: {nearest_expiry}")

# 3. Fetch the options chain for that date
calls, puts = aapl_data.get_options_chain(nearest_expiry)

# 4. Pick a specific option (Let's grab the first call option in the DataFrame)
# In a real app, you would filter this DataFrame by Strike Price
sample_call_data = calls.iloc[0] 
strike_price = sample_call_data['strike']
market_price = sample_call_data['lastPrice'] # The last traded price of the option

print(f"Target Call Option Strike: ${strike_price}")
print(f"Live Option Market Price:  ${market_price}")

# 5. Construct our Option Object
# Note: For live data, Time to Expiration (T) requires calculating the exact days 
# between today and the expiry date, divided by 365. For this quick test, we will 
# assume a rough T of 0.05 (about 18 days). We also assume standard 5% interest (r=0.05).
live_option = Option(
    S=live_S, 
    K=strike_price, 
    T=0.05, 
    r=0.05, 
    q=0.0, 
    sigma=0.20, # Placeholder, the solver will replace this!
    option_type="call",
    style="european"
)

# 6. Run the Implied Volatility Solver!
calculated_iv = engine.calculate_implied_volatility(live_option, market_price)

print(f"--> Engine Calculated Implied Volatility: {calculated_iv * 100:.2f}%")








print("\n--- Phase 4: Generating The Volatility Smile ---")

# 1. Calculate precise Time to Expiration (T)
expiry_date = datetime.strptime(nearest_expiry, "%Y-%m-%d")
today = datetime.now()
T = max((expiry_date - today).days / 365.0, 0.001) # One-liner safety check

print(f"Precise Time to Expiration (T): {T:.4f} years")
print("Stitching OTM Puts and OTM Calls together...")

# We will store our results as tuples: (Strike, IV) so we can sort them later
skew_data = []

# 2. Process the Left Side: Out-Of-The-Money Puts (Strike < Current Price)
for index, row in puts.iterrows():
    strike = row['strike']
    market_price = row['lastPrice']
    volume = row['volume']
    
    # Filter out ITM options and illiquid garbage
    if strike >= live_S or volume is None or volume == 0 or math.isnan(market_price):
        continue
        
    opt = Option(S=live_S, K=strike, T=T, r=0.05, q=0.0, sigma=0.5, option_type="put")
    iv = engine.calculate_implied_volatility(opt, market_price)
    
    if not math.isnan(iv):
        skew_data.append((strike, iv))

# 3. Process the Right Side: Out-Of-The-Money Calls (Strike > Current Price)
for index, row in calls.iterrows():
    strike = row['strike']
    market_price = row['lastPrice']
    volume = row['volume']
    
    # Filter out ITM options and illiquid garbage
    if strike <= live_S or volume is None or volume == 0 or math.isnan(market_price):
        continue
        
    opt = Option(S=live_S, K=strike, T=T, r=0.05, q=0.0, sigma=0.5, option_type="call")
    iv = engine.calculate_implied_volatility(opt, market_price)
    
    if not math.isnan(iv):
        skew_data.append((strike, iv))

# 4. Sort the data from lowest strike to highest strike
skew_data.sort(key=lambda x: x[0])

# Unpack the sorted tuples into two separate lists for matplotlib
final_strikes = [item[0] for item in skew_data]
final_ivs = [item[1] for item in skew_data]

# 5. Plot the Institutional Volatility Skew
plt.figure(figsize=(10, 6))

# Plot the combined skew line
plt.plot(final_strikes, final_ivs, marker='o', linestyle='-', color='purple', linewidth=2)

# Mark the current stock price
plt.axvline(x=live_S, color='black', linestyle='--', label=f'Current Stock Price (${live_S:.2f})')

plt.title(f"Institutional Volatility Skew: {aapl_data.ticker_symbol} expiring {nearest_expiry}")
plt.xlabel("Strike Price ($)")
plt.ylabel("Implied Volatility (Decimal)")
plt.grid(True, alpha=0.3)
plt.legend()

# Show the true market!
plt.show()





import pandas as pd

print("\n--- Phase 5: Portfolio Risk Dashboard ---")

# 1. Define a hypothetical portfolio using our live AAPL data
# Let's say we have a bullish position:
# We BOUGHT 10 At-The-Money Calls (Qty: +10)
# We SOLD 5 Out-Of-The-Money Puts (Qty: -5)

# Find an ATM Call (Closest strike to current live_S)
atm_call_row = calls.iloc[(calls['strike'] - live_S).abs().argsort()[:1]].iloc[0]

# Find an OTM Put (Roughly 5% below current stock price)
otm_put_row = puts.iloc[(puts['strike'] - (live_S * 0.95)).abs().argsort()[:1]].iloc[0]

positions = [
    {"name": "Long ATM Call", "row": atm_call_row, "opt_type": "call", "qty": 10},
    {"name": "Short OTM Put", "row": otm_put_row, "opt_type": "put", "qty": -5}
]

portfolio_risk = []
total_delta = total_gamma = total_theta = total_vega = 0.0

# 2. Loop through the portfolio and calculate aggregate risk
for pos in positions:
    row = pos["row"]
    qty = pos["qty"]
    
    # Create the base option object
    opt = Option(
        S=live_S, K=row['strike'], T=T, r=0.05, q=0.0, 
        sigma=0.5, # Dummy sigma, we will solve for the real one next
        option_type=pos["opt_type"]
    )
    
    # Solve for the exact Implied Volatility using our engine
    iv = engine.calculate_implied_volatility(opt, row['lastPrice'])
    
    # Update the option with the true market IV so the Greeks are accurate
    if not math.isnan(iv):
        opt.sigma = iv 
    else:
        opt.sigma = 0.20 # Fallback just in case
        
    # Calculate the Greeks
    greeks = engine.calculate_greeks(opt)
    
    # Scale by quantity AND the standard 100-shares-per-contract multiplier
    multiplier = qty * 100 
    
    pos_delta = greeks["delta"] * multiplier
    pos_gamma = greeks["gamma"] * multiplier
    pos_theta = greeks["theta"] * multiplier
    pos_vega = greeks["vega"] * multiplier
    
    # Add to running totals
    total_delta += pos_delta
    total_gamma += pos_gamma
    total_theta += pos_theta
    total_vega += pos_vega
    
    # Store the row for our display table
    portfolio_risk.append({
        "Position": pos["name"],
        "Strike": f"${row['strike']:.2f}",
        "Qty": qty,
        "IV": f"{opt.sigma*100:.1f}%",
        "Net Delta": round(pos_delta, 2),
        "Net Gamma": round(pos_gamma, 2),
        "Net Theta": round(pos_theta, 2),
        "Net Vega": round(pos_vega, 2)
    })

# 3. Add the Final Totals Row
portfolio_risk.append({
    "Position": "TOTAL PORTFOLIO",
    "Strike": "-",
    "Qty": "-",
    "IV": "-",
    "Net Delta": round(total_delta, 2),
    "Net Gamma": round(total_gamma, 2),
    "Net Theta": round(total_theta, 2),
    "Net Vega": round(total_vega, 2)
})

# 4. Display the Dashboard
risk_df = pd.DataFrame(portfolio_risk)
print("\n" + risk_df.to_string(index=False) + "\n")