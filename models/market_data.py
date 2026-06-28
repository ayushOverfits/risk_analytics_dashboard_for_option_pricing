import yfinance as yf

class MarketData:

    #Handles fetching real-time stock and options data from Yahoo Finance.
    def __init__(self, ticker_symbol: str):
        self.ticker_symbol = ticker_symbol.upper()
        self.ticker = yf.Ticker(self.ticker_symbol)
        
    def get_current_stock_price(self) -> float:
        #Fetches the last traded price of the stock.
        # fast_info is the most efficient way to grab live prices in yfinance
        return self.ticker.fast_info['lastPrice']
        
    def get_expirations(self) -> tuple:
        #Returns a tuple of all available expiration dates (YYYY-MM-DD).
        return self.ticker.options
        
    def get_options_chain(self, expiration_date: str):
        #Fetches the complete options chain for a specific date.
        #Returns a tuple containing two Pandas DataFrames: (calls, puts)
        chain = self.ticker.option_chain(expiration_date)
        
        # Explicitly return just the calls and puts DataFrames
        return chain.calls, chain.puts