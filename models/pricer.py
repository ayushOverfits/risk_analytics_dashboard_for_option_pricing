import numpy as np
import math
from scipy.stats import norm
from scipy.optimize import brentq

class PricingEngine:
    def _calculate_d1_d2(self , option):
        S = option.S
        K = option.K
        T = option.T
        sigma = option.sigma
        r = option.r
        q = option.q

        if T<= 0:
            return 0.0 , 0.0

        d1 = (np.log(S/K) + (r - q + sigma**2 * 0.5)*T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        return d1, d2


    def calculate_bsm_price(self, option):
        S = option.S
        K = option.K
        T = option.T
        sigma = option.sigma
        r = option.r
        q = option.q

        if T <= 0:
            if option.option_type == "call":
                return max(0.0 , S - K)
            else:
                return max(0.0 , K - S)
            
        d1 , d2 = self._calculate_d1_d2(option)

        if option.option_type == "call":
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option.option_type == "put":
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

        return price





    def calculate_binomial_tree(self, option, steps = 100):
        S = option.S
        K = option.K
        r = option.r
        T = option.T
        sigma = option.sigma
        q = option.q

        if T<=0:
            if option.option_type == "call":
                return max(0.0, S - K)
            else:
                return max(0.0 , K- S)
            
        #CRR Tree Parameters
        dt = T / steps
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp((r - q)*dt) - d)/ (u - d)
        discount = np.exp(-r * dt)
        #Forward propogation and finding the possible states that the stock can take
        prices = np.zeros(steps + 1)
        for i in range(steps + 1):
            prices[i] = S * (u ** (steps - i) * (d**i))

        option_value = np.zeros(steps + 1)

        for i in range(steps + 1):
            if option.option_type == "call":
                option_value[i] = max( 0 , prices[i] - K)
            else:
                option_value[i] = max(0 , K - prices[i])

        
        #Backward Propogation to find the option value in case of both American and European "call" and "put"
        for step in range(steps - 1 , -1 , -1):
            for i in range(step + 1):
                hold_value = discount * (p * option_value[i] + (1-p) * option_value[i+1])

                if option.style == "american":
                    current_stock_price = S * (u ** (step - i)) * (d ** i)
                    if option.option_type == "call":
                        exercise_value = max(0.0 , current_stock_price - K)
                    else:
                        exercise_value = max(0.0 , K - current_stock_price)
                    # Taking the decision whether we should hold or exercise
                    option_value[i] = max(hold_value , exercise_value)
                else:                               
                    option_value[i] = hold_value        #If the option is European, we cannot fold early
        
        return option_value[0]


    def calculate_greeks(self, option):
        S = option.S
        T = option.T
        K = option.K
        r = option.r
        sigma = option.sigma
        q = option.q


        if T < 0.0:  #If option is expired, greeks should be zero
            return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
        

        d1, d2 = self._calculate_d1_d2(option)

        #We need pdf(Probability density function) for gamma and vega
        pdf_d1 = norm.pdf(d1)


        # Pre-calculate CDFs
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)
        cdf_neg_d1 = norm.cdf(-d1)
        cdf_neg_d2 = norm.cdf(-d2)


        #Gamma and Vega are identical for call and puts
        gamma = (np.exp(-q * T) * pdf_d1) / (S * sigma * np.sqrt(T))
        # We divide Vega by 100 so it shows the dollar change for a 1% move in Volatility
        vega  = (S * np.exp(-q * T) * pdf_d1 * np.sqrt(T))/100


        if option.option_type == "call":
            delta = np.exp(-q * T) * cdf_d1
            theta = (- (S * sigma * np.exp(-q * T) * pdf_d1) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * cdf_d2 + q * S * np.exp(-q * T) * cdf_d1) / 365


            rho = (K * T * np.exp(-r * T) * cdf_d2) / 100    #divided by 100 to get 1% change in interest rates

        elif option.option_type == "put":
            delta = np.exp(-q * T) * (cdf_d1 - 1)
            theta = (- (S * sigma * np.exp(-q * T) * pdf_d1) / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * cdf_neg_d2 - q * S * np.exp(-q * T) * cdf_neg_d1) / 365

            rho = (-K * T * np.exp(-r * T) * cdf_neg_d2) / 100


        return { 
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "rho": rho,
        }
    
    def calculate_implied_volatility(self, option, market_price: float, max_iterations: int = 100, tolerance: float = 1e-6) -> float:
        S = option.S
        T = option.T
        K = option.K
        r = option.r
        sigma = option.sigma
        q = option.q
        #Arbitrage check
        if option.option_type == "call":
            intrinsic = max(0.0 , S - K)
        else:
            intrinsic = max(0.0 , K - S)

        if market_price <= intrinsic:    #Price below intrinsic, no IV exist
            return float('nan')
        

        #Brenner Subramanyam guess (highly educated guess, instead of random 50% guess)
        vol_guess = (market_price/S) * np.sqrt(2 * math.pi / T)
        vol_guess = max(0.01, min(vol_guess, 5.0))   # clamp between 1% and 500%

        #one temp option outside the loop so that it protects the original option (option data remains unharmed)
        import copy
        temp_option = copy.copy(option)

        #Newton Raphson loop
        for _ in range(max_iterations):
            temp_option.sigma = vol_guess

            price_guess = self.calculate_bsm_price(temp_option)
            diff = price_guess - market_price

            if abs(diff) < tolerance:
                return vol_guess

            #calculating vega
            d1, _ = self._calculate_d1_d2(temp_option)
            raw_vega = temp_option.S * norm.pdf(d1) * np.sqrt(temp_option.T)

            if raw_vega < 1e-10:        #If vega too small, Newton raphson will explode (since we divide by vega in the iterative formula)
                break

            # NR update step
            vol_guess = vol_guess - (diff / raw_vega)

            if not (0.0 < vol_guess < 5.0):   # shot out of bounds, hand off to Brent's
                break

        # Brent's fallback
        def price_error(sigma_guess: float) -> float:
            # We reuse that exact same temp object for Brent's method
            temp_option.sigma = sigma_guess
            return self.calculate_bsm_price(temp_option) - market_price

        try:
            return brentq(price_error, a=1e-5, b=5.0, xtol=tolerance, maxiter=1000)
        except ValueError:
            return float('nan')   # No valid IV in bracket (bad data or arbitrage)