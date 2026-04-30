import os
from langchain_core.tools import tool
import yfinance as yf

@tool
def stock_api(query: str) -> str:
    '''Use this tool when you need the latest market price for Apple (AAPL) and Google (GOOGL) stocks.'''
    try:
        # Fetch ticker data
        apple = yf.Ticker("AAPL")
        google = yf.Ticker("GOOGL")
        apple_price = apple.info.get("regularMarketPrice")
        google_price = google.info.get("regularMarketPrice")
        if apple_price is None or google_price is None:
            raise ValueError("Could not retrieve market price data.")
        result = f"Apple (AAPL): ${apple_price:.2f}, Google (GOOGL): ${google_price:.2f}"
        return f"SUCCESS: {result}"
    except Exception as e:
        return f"ERROR: {str(e)}"