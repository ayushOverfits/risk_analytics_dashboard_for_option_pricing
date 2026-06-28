class Option:
    def __init__(self, S , K , T , r , sigma ,q = 0.0, option_type = "call", style  = "european"):
        self.S = float(S)          # Current stock price
        self.K = float(K)          # Strike price
        self.T = float(T)          # Time to expiration (in years)
        self.r = float(r)          # Risk-free interest rate
        self.sigma = float(sigma)  # Implied Volatility
        self.q = float(q)          # Dividend yield


        self.option_type = option_type.lower()  # 'call' or 'put'
        self.style = style.lower()              # 'european' (BSM) or 'american' (Tree)


        if self.option_type not in ['call', 'put']:
            raise ValueError("option_type must be 'call' or 'put'")






