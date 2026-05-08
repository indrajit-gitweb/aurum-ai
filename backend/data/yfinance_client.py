"""
Yahoo Finance data client for AURUM AI.

All methods are synchronous but designed to be called from async code via
``asyncio.get_event_loop().run_in_executor`` or similar.  Each method catches
every exception and returns an empty structure so the pipeline never hard-fails
on missing market data.
"""

import logging
import re as _re
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Key normalisation helpers (BUG-07 fix)
# yfinance returns pandas index strings like "Total Revenue"; all agents expect
# snake_case keys like "total_revenue" / short aliases like "revenue".
# ─────────────────────────────────────────────────────────────────────────────

def _to_snake(key: str) -> str:
    """'Total Revenue' → 'total_revenue', 'EBITDA' → 'ebitda'."""
    return _re.sub(r'[^a-zA-Z0-9]+', '_', str(key)).lower().strip('_')


# Alias maps: snake key → shorter/conventional name (key is KEPT, alias is ADDED)
_INCOME_ALIASES: dict = {
    "total_revenue": "revenue",
    "basic_eps": "eps",
    "diluted_eps": "diluted_eps",
    "diluted_ni_availble_to_com_stockholders": "net_income_common",
    "reconciled_depreciation": "depreciation",
    "selling_general_and_administration": "sga",
    "research_and_development": "r_and_d",
}

_BALANCE_ALIASES: dict = {
    "total_liabilities_net_minority_interest": "total_liabilities",
    "total_equity_gross_minority_interest": "total_equity",
    "common_stock_equity": "stockholders_equity",
    "cash_and_cash_equivalents": "cash",
    "cash_cash_equivalents_and_short_term_investments": "cash_and_equivalents",
    "long_term_debt_and_capital_lease_obligation": "long_term_debt",
    "current_debt_and_capital_lease_obligation": "current_debt",
}

_CASHFLOW_ALIASES: dict = {
    "free_cash_flow": "fcf",
    "operating_cash_flow": "operating_cf",
    "capital_expenditure": "capex",
    "depreciation_amortization_depletion": "depreciation",
    "net_income_from_continuing_operations": "net_income_cf",
}


def _normalize_statement(raw: dict, alias_map: dict) -> dict:
    """Convert pandas financial statement keys to snake_case and apply aliases.

    For each original key → produces ``snake_key`` entry.
    If ``snake_key`` is in ``alias_map`` → also adds the alias key.
    Both the snake and the alias point to the same value so agents can use
    whichever convention they prefer.
    """
    result: dict = {}
    for k, v in raw.items():
        snake = _to_snake(str(k))
        result[snake] = v
        alias = alias_map.get(snake)
        if alias and alias != snake:
            result[alias] = v
    return result


class YFinanceClient:
    """Fetches price history, fundamentals, and news from Yahoo Finance.

    Args:
        ticker: Stock ticker symbol (e.g. ``"AAPL"``).
    """

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker.upper().strip()
        self._yf = yf.Ticker(self.ticker)

    # ─────────────────────────────────────────────────────────────────────────
    # Price history
    # ─────────────────────────────────────────────────────────────────────────

    def get_price_history(
        self,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return OHLCV price history as a DataFrame.

        Args:
            start: Start date as ``"YYYY-MM-DD"`` string.
            end: End date as ``"YYYY-MM-DD"`` string.
            interval: yfinance interval string (default ``"1d"``).

        Returns:
            DataFrame with columns Open, High, Low, Close, Volume.
            Empty DataFrame on failure.
        """
        try:
            df = self._yf.history(start=start, end=end, interval=interval)
            if df.empty:
                logger.warning("[%s] Empty price history for %s–%s.", self.ticker, start, end)
            return df
        except Exception as exc:
            logger.warning("[%s] get_price_history failed: %s", self.ticker, exc)
            return pd.DataFrame()

    # ─────────────────────────────────────────────────────────────────────────
    # Fundamentals
    # ─────────────────────────────────────────────────────────────────────────

    def get_fundamentals(self, ticker: Optional[str] = None) -> dict:
        """Return key fundamental metrics for the ticker.

        Args:
            ticker: Optional override ticker (uses instance ticker if omitted).

        Returns:
            Dict with keys: pe_ratio, pb_ratio, market_cap, revenue,
            earnings, total_debt, eps, dividend_yield, sector, industry.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            info = client.info
            ev     = info.get("enterpriseValue")
            ebitda_v = info.get("ebitda")
            mcap   = info.get("marketCap")
            fcf_v  = info.get("freeCashflow")
            result = {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "market_cap": mcap,
                "enterprise_value": ev,
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "revenue_growth_yoy": info.get("revenueGrowth"),   # alias
                "earnings": info.get("netIncomeToCommon"),
                "net_income": info.get("netIncomeToCommon"),        # alias
                "ebitda": ebitda_v,
                "total_debt": info.get("totalDebt"),
                "free_cashflow": fcf_v,
                "fcf": fcf_v,                                       # alias
                "eps": info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "name": info.get("longName"),
                "description": info.get("longBusinessSummary"),
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country"),
                "currency": info.get("currency"),
                # Profitability margins (direct from info — fast, no stmt needed)
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "net_margin": info.get("profitMargins"),
                # Return ratios
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                # Per-share data (for Graham Number etc.)
                "bvps": info.get("bookValue"),              # book value per share
                "shares_outstanding": info.get("sharesOutstanding"),
                # Derived multiples
                "ev_ebitda": (
                    round(ev / ebitda_v, 2)
                    if ev and ebitda_v and ebitda_v != 0 else None
                ),
                "fcf_yield": (
                    round(fcf_v / mcap * 100, 2)
                    if fcf_v and mcap and mcap != 0 else None
                ),
            }
            return result
        except Exception as exc:
            logger.warning("[%s] get_fundamentals failed: %s", self.ticker, exc)
            return {}

    def get_balance_sheet(self, ticker: Optional[str] = None) -> dict:
        """Return the most recent annual balance sheet as a normalised dict.

        Keys are snake_case (e.g. ``total_assets``, ``total_debt``, ``cash``).
        Derived ratios ``current_ratio`` and ``debt_equity`` are appended where
        the required inputs are available.

        Returns:
            Normalised dict.  Empty dict on failure.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            bs = client.balance_sheet
            if bs is None or bs.empty:
                return {}
            latest = bs.iloc[:, 0]
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in latest.items()}
            result = _normalize_statement(raw, _BALANCE_ALIASES)
            # Derived ratios
            ca = result.get("current_assets")
            cl = result.get("current_liabilities")
            td = result.get("total_debt")
            eq = result.get("stockholders_equity") or result.get("total_equity") or result.get("common_stock_equity")
            if ca and cl and cl != 0:
                result["current_ratio"] = round(ca / cl, 2)
            if td is not None and eq and eq != 0:
                result["debt_equity"] = round(td / eq, 2)
            return result
        except Exception as exc:
            logger.warning("[%s] get_balance_sheet failed: %s", self.ticker, exc)
            return {}

    def get_income_statement(self, ticker: Optional[str] = None) -> dict:
        """Return the most recent annual income statement as a normalised dict.

        Keys are snake_case with short aliases (e.g. ``total_revenue`` and ``revenue``).
        Derived margin ratios ``gross_margin``, ``operating_margin``, and ``net_margin``
        are appended where possible.

        Returns:
            Normalised dict.  Empty dict on failure.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            inc = client.income_stmt
            if inc is None or inc.empty:
                return {}
            latest = inc.iloc[:, 0]
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in latest.items()}
            result = _normalize_statement(raw, _INCOME_ALIASES)
            # Derived margin ratios (prefer the short "revenue" alias if already created)
            rev = result.get("revenue") or result.get("total_revenue")
            if rev and rev != 0:
                gp = result.get("gross_profit")
                oi = result.get("operating_income")
                ni = result.get("net_income")
                if gp is not None and "gross_margin" not in result:
                    result["gross_margin"] = round(gp / rev, 4)
                if oi is not None and "operating_margin" not in result:
                    result["operating_margin"] = round(oi / rev, 4)
                if ni is not None and "net_margin" not in result:
                    result["net_margin"] = round(ni / rev, 4)
                # R&D as % of revenue (yfinance reports R&D as a negative expense)
                rd = result.get("r_and_d") or result.get("research_and_development")
                if rd is not None:
                    result["rd_pct_revenue"] = round(abs(rd) / rev, 4)
            return result
        except Exception as exc:
            logger.warning("[%s] get_income_statement failed: %s", self.ticker, exc)
            return {}

    def get_cashflow(self, ticker: Optional[str] = None) -> dict:
        """Return the most recent annual cash-flow statement as a normalised dict.

        Keys are snake_case with short aliases:
          - ``free_cash_flow`` / ``fcf``
          - ``operating_cash_flow`` / ``operating_cf``
          - ``capital_expenditure`` / ``capex``

        Returns:
            Normalised dict.  Empty dict on failure.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            cf = client.cashflow
            if cf is None or cf.empty:
                return {}
            latest = cf.iloc[:, 0]
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in latest.items()}
            return _normalize_statement(raw, _CASHFLOW_ALIASES)
        except Exception as exc:
            logger.warning("[%s] get_cashflow failed: %s", self.ticker, exc)
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # News
    # ─────────────────────────────────────────────────────────────────────────

    def get_news(self, ticker: Optional[str] = None, limit: int = 10) -> list[dict]:
        """Return recent news headlines for the ticker.

        Args:
            ticker: Optional override ticker.
            limit: Maximum number of articles to return.

        Returns:
            List of dicts with keys: title, publisher, link, providerPublishTime.
            Empty list on failure.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            raw = client.news or []
            result = []
            for article in raw[:limit]:
                result.append(
                    {
                        "title": article.get("title", ""),
                        "publisher": article.get("publisher", ""),
                        "link": article.get("link", ""),
                        "published_at": article.get("providerPublishTime"),
                        "summary": article.get("summary", ""),
                    }
                )
            return result
        except Exception as exc:
            logger.warning("[%s] get_news failed: %s", self.ticker, exc)
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Technical indicators
    # ─────────────────────────────────────────────────────────────────────────

    def get_technical_indicators(
        self,
        ticker: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> dict:
        """Compute RSI, MACD, SMA20/50/200, Bollinger Bands, and average volume.

        Args:
            ticker: Optional override ticker.
            start: Start date string ``"YYYY-MM-DD"``.  Defaults to 1 year ago.
            end: End date string.  Defaults to today.

        Returns:
            Dict with technical indicator values.  Empty dict on failure.
        """
        if end is None:
            end = datetime.today().strftime("%Y-%m-%d")
        if start is None:
            start = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            df = client.history(start=start, end=end, interval="1d")
            if df.empty or len(df) < 20:
                logger.warning("[%s] Insufficient price data for technical indicators.", self.ticker)
                return {}

            close = df["Close"]
            volume = df["Volume"]

            # ── Simple Moving Averages ────────────────────────────────────────
            sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
            sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
            sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

            # ── Relative Strength Index (14-period) ───────────────────────────
            rsi = self._compute_rsi(close, period=14)

            # ── MACD (12, 26, 9) ─────────────────────────────────────────────
            macd_line, signal_line, macd_hist = self._compute_macd(close)

            # ── Bollinger Bands (20-period, 2σ) ───────────────────────────────
            bb_upper, bb_mid, bb_lower = self._compute_bollinger(close, period=20, std_dev=2)

            # ── Volume ────────────────────────────────────────────────────────
            avg_volume_20 = float(volume.tail(20).mean()) if len(volume) >= 20 else None
            latest_volume = float(volume.iloc[-1]) if not volume.empty else None

            current_price = float(close.iloc[-1])

            return {
                "current_price": current_price,
                "sma_20": _safe_float(sma20),
                "sma_50": _safe_float(sma50),
                "sma_200": _safe_float(sma200),
                "rsi_14": _safe_float(rsi),
                "macd_line": _safe_float(macd_line),
                "macd_signal": _safe_float(signal_line),
                "macd_histogram": _safe_float(macd_hist),
                "bb_upper": _safe_float(bb_upper),
                "bb_middle": _safe_float(bb_mid),
                "bb_lower": _safe_float(bb_lower),
                "avg_volume_20d": avg_volume_20,
                "latest_volume": latest_volume,
                "price_vs_sma50": (
                    round((current_price / sma50 - 1) * 100, 2) if sma50 else None
                ),
                "price_vs_sma200": (
                    round((current_price / sma200 - 1) * 100, 2) if sma200 else None
                ),
            }
        except Exception as exc:
            logger.warning("[%s] get_technical_indicators failed: %s", self.ticker, exc)
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_rsi(close: pd.Series, period: int = 14) -> Optional[float]:
        if len(close) < period + 1:
            return None
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else None

    @staticmethod
    def _compute_macd(
        close: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if len(close) < slow + signal:
            return None, None, None
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        sig = macd.ewm(span=signal, adjust=False).mean()
        hist = macd - sig
        return float(macd.iloc[-1]), float(sig.iloc[-1]), float(hist.iloc[-1])

    @staticmethod
    def _compute_bollinger(
        close: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        if len(close) < period:
            return None, None, None
        rolling = close.rolling(period)
        mid = rolling.mean()
        std = rolling.std()
        upper = mid + std_dev * std
        lower = mid - std_dev * std
        return float(upper.iloc[-1]), float(mid.iloc[-1]), float(lower.iloc[-1])


def _safe_float(value) -> Optional[float]:
    """Convert a value to float, returning None if not finite."""
    try:
        f = float(value)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None
