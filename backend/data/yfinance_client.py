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
                "forward_eps": info.get("forwardEps"),
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                "beta": info.get("beta"),
                "short_interest": info.get("shortPercentOfFloat"),   # e.g. 0.023 = 2.3%
                "short_ratio":    info.get("shortRatio"),
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
            # ── ROIC computation ──────────────────────────────────────────────
            # NOPAT ≈ EBITDA * (1 - 0.25) as a rough proxy for operating income
            # after a blended 25% tax rate.
            # Invested Capital = total_debt + book_equity - cash
            try:
                ebitda_r = info.get("ebitda")
                total_debt_r = info.get("totalDebt") or 0
                book_value_r = info.get("bookValue") or 0
                shares_r = info.get("sharesOutstanding") or 0
                total_cash_r = info.get("totalCash") or 0
                nopat = ebitda_r * 0.75 if ebitda_r else None
                book_equity = book_value_r * shares_r
                invested_capital = total_debt_r + book_equity - total_cash_r
                if nopat is not None and invested_capital > 0:
                    result["roic"] = round(nopat / invested_capital, 4)
                else:
                    result["roic"] = None
            except Exception:
                result["roic"] = None
            # Spread vs WACC — computed downstream when WACC is available
            result["roic_wacc_spread"] = None
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
            # Working-capital change vs prior year (two-period comparison)
            try:
                if bs.shape[1] >= 2:
                    prior_col = bs.iloc[:, 1]
                    prior_raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in prior_col.items()}
                    prior_data = _normalize_statement(prior_raw, _BALANCE_ALIASES)
                    ca_p = prior_data.get("current_assets")
                    cl_p = prior_data.get("current_liabilities")
                    wc_now   = (ca - cl) if ca and cl else None
                    wc_prior = (ca_p - cl_p) if ca_p and cl_p else None
                    if wc_now is not None and wc_prior is not None:
                        result["working_capital_change"] = round(wc_now - wc_prior, 0)
            except Exception:
                pass
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
    # Historical financial statements (historical analysis mode)
    # ─────────────────────────────────────────────────────────────────────────

    def _col_on_or_before(self, df: pd.DataFrame, end_date: str) -> "Optional[pd.Series]":
        """Return the most recent DataFrame column with timestamp ≤ end_date."""
        if df is None or df.empty:
            return None
        end_ts = pd.Timestamp(end_date)
        valid = [c for c in df.columns if pd.Timestamp(c) <= end_ts]
        if not valid:
            valid = list(df.columns)          # fallback: use oldest available
        if not valid:
            return None
        best = max(valid, key=lambda c: pd.Timestamp(c))
        return df[best]

    def get_historical_income_statement(self, end_date: str) -> dict:
        """Return the annual income statement for the period ending on or before end_date."""
        try:
            df = self._yf.income_stmt
            if df is None or df.empty:
                return {}
            series = self._col_on_or_before(df, end_date)
            if series is None:
                return {}
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in series.items()}
            result = _normalize_statement(raw, _INCOME_ALIASES)
            rev = result.get("revenue") or result.get("total_revenue")
            if rev and rev != 0:
                gp = result.get("gross_profit")
                oi = result.get("operating_income")
                ni = result.get("net_income")
                if gp is not None:
                    result.setdefault("gross_margin", round(gp / rev, 4))
                if oi is not None:
                    result.setdefault("operating_margin", round(oi / rev, 4))
                if ni is not None:
                    result.setdefault("net_margin", round(ni / rev, 4))
            return result
        except Exception as exc:
            logger.warning("[%s] get_historical_income_statement failed: %s", self.ticker, exc)
            return {}

    def get_historical_balance_sheet(self, end_date: str) -> dict:
        """Return the annual balance sheet for the period ending on or before end_date."""
        try:
            df = self._yf.balance_sheet
            if df is None or df.empty:
                return {}
            series = self._col_on_or_before(df, end_date)
            if series is None:
                return {}
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in series.items()}
            result = _normalize_statement(raw, _BALANCE_ALIASES)
            ca = result.get("current_assets")
            cl = result.get("current_liabilities")
            td = result.get("total_debt")
            eq = (result.get("stockholders_equity") or result.get("total_equity")
                  or result.get("common_stock_equity"))
            if ca and cl and cl != 0:
                result["current_ratio"] = round(ca / cl, 2)
            if td is not None and eq and eq != 0:
                result["debt_equity"] = round(td / eq, 2)
            return result
        except Exception as exc:
            logger.warning("[%s] get_historical_balance_sheet failed: %s", self.ticker, exc)
            return {}

    def get_historical_cashflow(self, end_date: str) -> dict:
        """Return the annual cash-flow statement for the period ending on or before end_date."""
        try:
            df = self._yf.cashflow
            if df is None or df.empty:
                return {}
            series = self._col_on_or_before(df, end_date)
            if series is None:
                return {}
            raw = {str(k): (None if pd.isna(v) else float(v)) for k, v in series.items()}
            return _normalize_statement(raw, _CASHFLOW_ALIASES)
        except Exception as exc:
            logger.warning("[%s] get_historical_cashflow failed: %s", self.ticker, exc)
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # News
    # ─────────────────────────────────────────────────────────────────────────

    def get_news(self, ticker: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Return recent news headlines for the ticker.

        Args:
            ticker: Optional override ticker.
            limit: Maximum number of articles to return (default raised to 20).

        Returns:
            List of dicts with normalised keys including ``headline`` and ``date``
            aliases so all persona agents can access them uniformly.
            Empty list on failure.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            raw = client.news or []
            result = []
            for article in raw[:limit]:
                # Convert Unix timestamp → ISO date string "YYYY-MM-DD"
                ts = article.get("providerPublishTime")
                try:
                    date_str = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d") if ts else "N/A"
                except Exception:
                    date_str = "N/A"

                title = article.get("title", "")
                result.append(
                    {
                        # Primary fields
                        "title":        title,
                        "headline":     title,          # alias — News Sentiment uses "headline"
                        "date":         date_str,       # alias — News Sentiment uses "date"
                        "publisher":    article.get("publisher", ""),
                        "link":         article.get("link", ""),
                        "published_at": date_str,
                        "summary":      article.get("summary", ""),
                    }
                )
            return result
        except Exception as exc:
            logger.warning("[%s] get_news failed: %s", self.ticker, exc)
            return []

    def get_insider_transactions(self, ticker: Optional[str] = None) -> list[dict]:
        """Return recent insider buy/sell transactions.

        Uses yfinance's ``insider_transactions`` DataFrame.  Normalises column
        names across yfinance versions and classifies each transaction as
        buy / sell / other based on the description text.

        Returns:
            List of dicts with keys: name, role, date, transaction_type,
            shares, value, description.  Empty list on failure or no data.
        """
        client = yf.Ticker(ticker.upper()) if ticker else self._yf
        try:
            df = client.insider_transactions
            if df is None or (hasattr(df, "empty") and df.empty):
                return []

            result = []
            for _, row in df.iterrows():
                # Column names vary across yfinance versions
                name  = str(row.get("Insider",   row.get("Name",     "Unknown")))
                role  = str(row.get("Position",  row.get("Title",    "N/A")))
                date_raw = row.get("Start Date", row.get("Date",     None))
                try:
                    date_str = str(date_raw)[:10] if date_raw is not None else "N/A"
                except Exception:
                    date_str = "N/A"

                text   = str(row.get("Text", row.get("Transaction", "")))
                shares = row.get("Shares", 0) or 0
                value  = row.get("Value",  0) or 0

                text_lower = text.lower()
                if any(k in text_lower for k in ["purchase", "buy", "bought", "automatic buy", "direct purchase"]):
                    txn_type = "buy"
                elif any(k in text_lower for k in ["sale", "sell", "sold", "automatic sell", "direct sale"]):
                    txn_type = "sell"
                else:
                    txn_type = "other"

                result.append(
                    {
                        "name":             name,
                        "role":             role,
                        "date":             date_str,
                        "transaction_type": txn_type,
                        "action":           txn_type,       # alias
                        "shares":           int(abs(shares)) if shares else 0,
                        "value":            abs(float(value)) if value else 0,
                        "total_value":      abs(float(value)) if value else 0,  # alias
                        "description":      text,
                    }
                )
            return result[:15]   # most recent 15 transactions
        except Exception as exc:
            logger.warning("[%s] get_insider_transactions failed: %s", self.ticker, exc)
            return []

    def get_earnings_calendar(self) -> dict:
        """Return the next earnings date and any forward estimates from yfinance.

        Returns:
            Dict with keys: next_earnings_date, earnings_avg, earnings_low,
            earnings_high, revenue_avg.  Empty dict on failure.
        """
        try:
            cal = self._yf.calendar
            if cal is None:
                return {}
            result: dict = {}
            if isinstance(cal, dict):
                for raw_key, val in cal.items():
                    key = _to_snake(str(raw_key))
                    # Lists (e.g. date ranges) → take the first element
                    if hasattr(val, "__iter__") and not isinstance(val, str):
                        items = list(val)
                        val = items[0] if items else None
                    if val is not None:
                        result[key] = str(val)[:10] if hasattr(val, "strftime") else val
            elif hasattr(cal, "to_dict"):
                # Some yfinance versions return a DataFrame
                for col in cal.columns:
                    v = cal[col].iloc[0]
                    if v is not None:
                        result[_to_snake(str(col))] = str(v)[:10] if hasattr(v, "strftime") else v
            return result
        except Exception as exc:
            logger.warning("[%s] get_earnings_calendar failed: %s", self.ticker, exc)
            return {}

    def get_analyst_recommendations(self) -> dict:
        """Return a summary of analyst buy/hold/sell ratings.

        Uses yfinance's ``recommendations_summary`` (most recent period only).

        Returns:
            Dict with keys: strong_buy, buy, hold, sell, strong_sell, total,
            consensus (string label), consensus_score (0-4).
            Empty dict on failure.
        """
        try:
            recs = self._yf.recommendations_summary
            if recs is None or (hasattr(recs, "empty") and recs.empty):
                return {}
            row = recs.iloc[0]  # most recent period
            sb  = int(row.get("strongBuy",   0) or 0)
            b   = int(row.get("buy",         0) or 0)
            h   = int(row.get("hold",        0) or 0)
            s   = int(row.get("sell",        0) or 0)
            ss  = int(row.get("strongSell",  0) or 0)
            total = sb + b + h + s + ss
            # Consensus score 0-4 (higher = more bullish)
            score = (sb * 4 + b * 3 + h * 2 + s * 1 + ss * 0) / total if total else 2.0
            if score >= 3.5:   label = "Strong Buy"
            elif score >= 2.8: label = "Buy"
            elif score >= 2.2: label = "Hold"
            elif score >= 1.5: label = "Sell"
            else:              label = "Strong Sell"
            return {
                "strong_buy":      sb,
                "buy":             b,
                "hold":            h,
                "sell":            s,
                "strong_sell":     ss,
                "total_analysts":  total,
                "consensus":       label,
                "consensus_score": round(score, 2),
            }
        except Exception as exc:
            logger.warning("[%s] get_analyst_recommendations failed: %s", self.ticker, exc)
            return {}

    def get_institutional_ownership(self) -> dict:
        """Return institutional ownership percentage and top-5 holders.

        Returns:
            Dict with keys: pct_institutionally_held, top_holders (list of
            {name, pct_held}).  Empty dict on failure.
        """
        try:
            holders = self._yf.institutional_holders
            if holders is None or (hasattr(holders, "empty") and holders.empty):
                return {}

            # Try to derive overall % held from top-holders table
            pct_col = next(
                (c for c in holders.columns if "%" in c or "out" in c.lower() or "pct" in c.lower()),
                None,
            )
            pct_total: Optional[float] = None
            try:
                if pct_col:
                    pct_total = holders[pct_col].sum() * 100
            except Exception:
                pass

            top: list[dict] = []
            for _, row in holders.head(5).iterrows():
                name = str(row.get("Holder", row.get("holder", "")))
                pct  = row.get(pct_col) if pct_col else None
                top.append({
                    "name":     name,
                    "pct_held": f"{float(pct) * 100:.1f}%" if pct is not None else "N/A",
                })

            return {
                "pct_institutionally_held": f"{pct_total:.1f}%" if pct_total else "N/A",
                "top_holders": top,
            }
        except Exception as exc:
            logger.warning("[%s] get_institutional_ownership failed: %s", self.ticker, exc)
            return {}

    def get_shares_outstanding_change(self) -> dict:
        """Return % change in shares outstanding over ~3 years.

        Reads the balance sheet's "Ordinary Shares Number" (or equivalent) row
        across multiple annual periods and computes the percentage change from
        the earliest available period (~3 years ago) to the most recent.

        A negative value means the company has been buying back shares (good for
        per-share metrics).  A positive value signals dilution.

        Returns:
            Dict with keys: shares_current, shares_prior, shares_change_3yr.
            Empty dict on failure or insufficient history.
        """
        try:
            bs = self._yf.balance_sheet
            if bs is None or bs.empty or bs.shape[1] < 2:
                return {}
            # yfinance uses "Ordinary Shares Number" for common share count
            share_row = next(
                (r for r in bs.index
                 if "ordinary" in str(r).lower()
                 or ("share" in str(r).lower() and "number" in str(r).lower())),
                None,
            )
            if share_row is None:
                return {}
            vals = bs.loc[share_row].dropna()
            if len(vals) < 2:
                return {}
            current = float(vals.iloc[0])
            prior   = float(vals.iloc[min(3, len(vals) - 1)])  # ~3 years ago
            if prior == 0:
                return {}
            pct_change = (current - prior) / abs(prior)
            return {
                "shares_current":    int(current),
                "shares_prior":      int(prior),
                "shares_change_3yr": f"{pct_change:+.1%}",
            }
        except Exception as exc:
            logger.warning("[%s] get_shares_outstanding_change failed: %s", self.ticker, exc)
            return {}

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

            # Trend direction from price vs 200-day SMA
            trend_direction = None
            if sma200:
                trend_direction = "uptrend" if current_price > sma200 else "downtrend"

            # Relative strength vs S&P 500 over the same period (Druckenmiller uses this)
            relative_strength_vs_spy: Optional[str] = None
            stock_return_1yr: Optional[str] = None
            spy_return_1yr: Optional[str] = None
            try:
                spy_df = yf.Ticker("SPY").history(start=start, end=end, interval="1d")
                if not spy_df.empty and not df.empty:
                    stk_ret = (current_price / float(close.iloc[0]) - 1)
                    spy_ret = (float(spy_df["Close"].iloc[-1]) / float(spy_df["Close"].iloc[0]) - 1)
                    relative_strength_vs_spy = f"{(stk_ret - spy_ret):+.1%}"
                    stock_return_1yr = f"{stk_ret:+.1%}"
                    spy_return_1yr   = f"{spy_ret:+.1%}"
            except Exception:
                pass

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
                "trend_direction":           trend_direction,
                "relative_strength_vs_spy":  relative_strength_vs_spy,
                "stock_return_1yr":          stock_return_1yr,
                "spy_return_1yr":            spy_return_1yr,
            }
        except Exception as exc:
            logger.warning("[%s] get_technical_indicators failed: %s", self.ticker, exc)
            return {}

    def get_peer_comparison(
        self,
        industry: str = "",
        sector: str = "",
        max_peers: int = 3,
    ) -> list[dict]:
        """Fetch key valuation/profitability metrics for sector peers.

        Looks up 2-3 well-known comparable tickers from a curated
        industry/sector mapping, then fetches P/E, P/B, P/S, profit
        margin, revenue growth and market cap for each.

        Args:
            industry: yfinance industry string (``ticker.info["industry"]``).
            sector:   yfinance sector string (fallback when industry not mapped).
            max_peers: Maximum number of peers to return (default 3).

        Returns:
            List of dicts with: ticker, name, price, pe_ratio, pb_ratio,
            ps_ratio, profit_margin, revenue_growth, market_cap.
            Empty list on failure.
        """
        # ── Industry-level peer candidates ────────────────────────────────────
        _PEER_MAP: dict[str, list[str]] = {
            # Technology
            "Semiconductors":                     ["NVDA", "AMD", "INTC", "QCOM", "AVGO"],
            "Software—Application":               ["MSFT", "ADBE", "CRM", "NOW"],
            "Software—Infrastructure":            ["MSFT", "ORCL", "IBM", "CSCO"],
            "Internet Content & Information":     ["GOOGL", "META", "SNAP"],
            "Consumer Electronics":               ["AAPL", "MSFT", "SONY"],
            "Electronic Components":              ["TXN", "AMAT", "KLAC"],
            "Computer Hardware":                  ["DELL", "HPQ", "NTAP"],
            "Communication Equipment":            ["CSCO", "JNPR", "ANET"],
            # Finance
            "Banks—Regional":                     ["JPM", "BAC", "WFC", "USB"],
            "Banks—Diversified":                  ["JPM", "BAC", "C", "WFC"],
            "Financial Services":                 ["V", "MA", "AXP", "PYPL"],
            "Insurance—Life":                     ["MET", "PRU", "AFL"],
            "Insurance—Property & Casualty":      ["PGR", "TRV", "CB"],
            "Asset Management":                   ["BLK", "SCHW", "MS"],
            "Capital Markets":                    ["GS", "MS", "JPM"],
            # Healthcare
            "Drug Manufacturers—General":         ["JNJ", "PFE", "LLY", "MRK", "ABBV"],
            "Drug Manufacturers—Specialty & Generic": ["BMY", "AMGN", "GILD"],
            "Biotechnology":                      ["AMGN", "GILD", "BIIB", "REGN", "VRTX"],
            "Medical Devices":                    ["ABT", "MDT", "SYK", "BSX"],
            "Healthcare Plans":                   ["UNH", "CVS", "ELV", "CI"],
            # Consumer Cyclical
            "Internet Retail":                    ["AMZN", "SHOP", "ETSY", "EBAY"],
            "Specialty Retail":                   ["TGT", "COST", "WMT", "HD"],
            "Apparel Retail":                     ["NKE", "GAP", "PVH"],
            "Restaurants":                        ["MCD", "SBUX", "YUM", "CMG"],
            "Auto Manufacturers":                 ["TSLA", "GM", "F", "TM"],
            "Auto Parts":                         ["MGA", "APTV", "BWA"],
            # Consumer Defensive
            "Food Distribution":                  ["WMT", "COST", "KR"],
            "Beverages—Non-Alcoholic":            ["KO", "PEP", "MNST"],
            "Tobacco":                            ["MO", "PM", "BTI"],
            # Industrials
            "Aerospace & Defense":                ["BA", "LMT", "RTX", "NOC", "GD"],
            "Industrial Conglomerates":           ["GE", "HON", "MMM"],
            "Specialty Chemicals":                ["LIN", "APD", "SHW"],
            "Oil & Gas E&P":                      ["XOM", "CVX", "COP", "EOG"],
            "Oil & Gas Integrated":               ["XOM", "CVX", "BP"],
            "Oil & Gas Refining & Marketing":     ["VLO", "PSX", "MPC"],
            # Real Estate
            "REIT—Retail":                        ["SPG", "O", "NNN"],
            "REIT—Industrial":                    ["PLD", "EGP", "STAG"],
            "REIT—Residential":                   ["AVB", "EQR", "MAA"],
            # Utilities
            "Utilities—Regulated Electric":       ["NEE", "DUK", "SO", "AEP"],
            "Utilities—Regulated Gas":            ["SRE", "ATO", "NI"],
            # Telecom
            "Telecom Services":                   ["T", "VZ", "TMUS"],
            # Materials
            "Steel":                              ["NUE", "STLD", "CLF"],
            "Gold":                               ["NEM", "GOLD", "AEM"],
            "Copper":                             ["FCX", "SCCO"],
        }
        # ── Sector-level fallbacks ────────────────────────────────────────────
        _SECTOR_PEERS: dict[str, list[str]] = {
            "Technology":             ["AAPL", "MSFT", "GOOGL", "NVDA"],
            "Financial Services":     ["JPM", "BAC", "V", "MA"],
            "Healthcare":             ["JNJ", "UNH", "PFE", "LLY"],
            "Consumer Cyclical":      ["AMZN", "TSLA", "HD", "NKE"],
            "Consumer Defensive":     ["WMT", "PG", "KO", "COST"],
            "Industrials":            ["HON", "GE", "CAT", "BA"],
            "Energy":                 ["XOM", "CVX", "COP", "SLB"],
            "Real Estate":            ["AMT", "PLD", "EQIX", "SPG"],
            "Utilities":              ["NEE", "DUK", "SO", "AEP"],
            "Basic Materials":        ["LIN", "FCX", "NEM", "NUE"],
            "Communication Services": ["GOOGL", "META", "NFLX", "DIS"],
        }

        candidates: list[str] = _PEER_MAP.get(industry, [])
        if not candidates:
            candidates = _SECTOR_PEERS.get(sector, [])
        if not candidates:
            return []

        exclude_upper = self.ticker.upper()
        peers = [t for t in candidates if t.upper() != exclude_upper][:max_peers]

        results: list[dict] = []
        for peer_ticker in peers:
            try:
                info: dict = yf.Ticker(peer_ticker).info or {}
                results.append({
                    "ticker":         peer_ticker,
                    "name":           info.get("shortName") or info.get("longName") or peer_ticker,
                    "price":          info.get("currentPrice") or info.get("regularMarketPrice"),
                    "pe_ratio":       info.get("trailingPE"),
                    "pb_ratio":       info.get("priceToBook"),
                    "ps_ratio":       info.get("priceToSalesTrailing12Months"),
                    "profit_margin":  info.get("profitMargins"),
                    "revenue_growth": info.get("revenueGrowth"),
                    "market_cap":     info.get("marketCap"),
                })
            except Exception as exc:
                logger.warning("[peer] %s fetch failed: %s", peer_ticker, exc)
        return results

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
