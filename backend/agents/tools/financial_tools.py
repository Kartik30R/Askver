import logging
from typing import Dict, Any, Optional
import yfinance as yf

logger = logging.getLogger(__name__)


def get_company_financials(ticker_symbol: str) -> Dict[str, Any]:
    """
    Fetches financial metrics, market cap, revenue, and balance sheet highlights
    from Yahoo Finance using a ticker symbol (e.g., 'AAPL', 'INFY.NS', 'TCS.NS').
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        # Extract core financial metrics safely
        financial_summary = {
            "symbol": ticker_symbol,
            "company_name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "total_revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "gross_margins": info.get("grossMargins"),
            "operating_margins": info.get("operatingMargins"),
            "ebitda": info.get("ebitda"),
            "free_cashflow": info.get("freeCashflow"),
            "total_debt": info.get("totalDebt"),
            "currency": info.get("currency", "USD"),
            "business_summary": info.get("longBusinessSummary")
        }

        return {k: v for k, v in financial_summary.items() if v is not None}

    except Exception as e:
        logger.error(f"Error fetching financial data for symbol '{ticker_symbol}': {str(e)}")
        return {
            "error": f"Could not retrieve financials for ticker {ticker_symbol}",
            "details": str(e)
        }