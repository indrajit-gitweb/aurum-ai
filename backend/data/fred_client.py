"""
Federal Reserve Economic Data (FRED) client for AURUM AI.

Fetches macro indicators: fed funds rate, CPI inflation, GDP growth,
unemployment, and the yield curve.

Strategy:
- If FRED_API_KEY is set, use the ``fredapi`` library for full access.
- Otherwise, pull public CSV endpoints from fred.stlouisfed.org (no key needed
  for the most common series).
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

# Common FRED series IDs
SERIES = {
    "fed_funds": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "gdp": "GDPC1",              # Real GDP (billions)
    "unemployment": "UNRATE",
    "t2y": "DGS2",               # 2-Year Treasury
    "t5y": "DGS5",               # 5-Year Treasury
    "t10y": "DGS10",             # 10-Year Treasury
    "t30y": "DGS30",             # 30-Year Treasury
}


def _fetch_fred_series_csv(series_id: str) -> Optional[list[tuple[str, float]]]:
    """Fetch a FRED series as a list of (date, value) tuples via public CSV.

    Returns None on failure.
    """
    url = FRED_CSV_BASE.format(series_id=series_id)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        results = []
        for line in lines[1:]:  # skip header
            parts = line.split(",")
            if len(parts) < 2:
                continue
            date_str, val_str = parts[0].strip(), parts[1].strip()
            if val_str in ("", ".", "NA"):
                continue
            try:
                results.append((date_str, float(val_str)))
            except ValueError:
                continue
        return results if results else None
    except Exception as exc:
        logger.warning("FRED CSV fetch failed for series %s: %s", series_id, exc)
        return None


def _latest_value(series_id: str) -> Optional[float]:
    """Return the most recent non-null value for a FRED series."""
    data = _fetch_fred_series_csv(series_id)
    if not data:
        return None
    return data[-1][1]


def _yoy_growth(series_id: str) -> Optional[float]:
    """Compute year-over-year percentage change using the last two available
    annual observations (12 observations apart in monthly data).
    """
    data = _fetch_fred_series_csv(series_id)
    if not data or len(data) < 13:
        return None
    current = data[-1][1]
    year_ago = data[-13][1]
    if year_ago == 0:
        return None
    return round((current / year_ago - 1) * 100, 2)


class FREDClient:
    """Macro-economic data client using FRED.

    Prefers the ``fredapi`` library when ``FRED_API_KEY`` is set in the
    environment; falls back to public CSV endpoints otherwise.
    """

    def __init__(self) -> None:
        self._api_key = os.getenv("FRED_API_KEY", "").strip()
        self._fred = None

        if self._api_key:
            try:
                from fredapi import Fred  # type: ignore
                self._fred = Fred(api_key=self._api_key)
                logger.debug("FREDClient: using fredapi library.")
            except ImportError:
                logger.warning(
                    "fredapi package not installed.  Falling back to public CSV API."
                )
            except Exception as exc:
                logger.warning("Failed to init fredapi: %s.  Using CSV fallback.", exc)

    def _get_latest(self, series_id: str) -> Optional[float]:
        if self._fred is not None:
            try:
                series = self._fred.get_series(series_id)
                series = series.dropna()
                return float(series.iloc[-1]) if not series.empty else None
            except Exception as exc:
                logger.warning("fredapi get_series(%s) failed: %s", series_id, exc)
        return _latest_value(series_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Individual indicators
    # ─────────────────────────────────────────────────────────────────────────

    def get_fed_funds_rate(self) -> Optional[float]:
        """Return the most recent Federal Funds Effective Rate (%).

        Returns:
            Rate as a float (e.g. 5.33), or None on failure.
        """
        return self._get_latest(SERIES["fed_funds"])

    def get_inflation_rate(self) -> Optional[float]:
        """Return the latest CPI year-over-year inflation rate (%).

        Returns:
            YoY CPI change as a float, or None on failure.
        """
        if self._fred is not None:
            try:
                series = self._fred.get_series(SERIES["cpi"]).dropna()
                if len(series) >= 13:
                    return round((series.iloc[-1] / series.iloc[-13] - 1) * 100, 2)
            except Exception as exc:
                logger.warning("fredapi CPI YoY failed: %s", exc)
        return _yoy_growth(SERIES["cpi"])

    def get_gdp_growth(self) -> Optional[float]:
        """Return the most recent real GDP quarter-over-quarter annualised growth (%).

        Returns:
            GDP QoQ annualised growth rate as a float, or None on failure.
        """
        if self._fred is not None:
            try:
                series = self._fred.get_series(SERIES["gdp"]).dropna()
                if len(series) >= 2:
                    q_change = (series.iloc[-1] / series.iloc[-2]) ** 4 - 1
                    return round(q_change * 100, 2)
            except Exception as exc:
                logger.warning("fredapi GDP QoQ failed: %s", exc)

        data = _fetch_fred_series_csv(SERIES["gdp"])
        if data and len(data) >= 2:
            prev, curr = data[-2][1], data[-1][1]
            return round(((curr / prev) ** 4 - 1) * 100, 2)
        return None

    def get_unemployment_rate(self) -> Optional[float]:
        """Return the most recent US unemployment rate (%).

        Returns:
            Unemployment rate as a float (e.g. 3.9), or None on failure.
        """
        return self._get_latest(SERIES["unemployment"])

    def get_yield_curve(self) -> dict:
        """Return the current US Treasury yield curve.

        Returns:
            Dict with keys ``2y``, ``5y``, ``10y``, ``30y`` — each a float (%)
            or None if unavailable.
        """
        return {
            "2y": self._get_latest(SERIES["t2y"]),
            "5y": self._get_latest(SERIES["t5y"]),
            "10y": self._get_latest(SERIES["t10y"]),
            "30y": self._get_latest(SERIES["t30y"]),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Composite summary
    # ─────────────────────────────────────────────────────────────────────────

    def get_macro_summary(self) -> str:
        """Return a formatted paragraph describing the current macro environment.

        Returns:
            Human-readable macro summary string.
        """
        fed = self.get_fed_funds_rate()
        cpi = self.get_inflation_rate()
        gdp = self.get_gdp_growth()
        unemp = self.get_unemployment_rate()
        yc = self.get_yield_curve()

        parts = []

        if fed is not None:
            parts.append(f"The Federal Funds Rate currently stands at {fed:.2f}%.")

        if cpi is not None:
            tone = "elevated" if cpi > 3 else ("moderate" if cpi > 2 else "subdued")
            parts.append(f"Inflation (CPI YoY) is {tone} at {cpi:.2f}%.")

        if gdp is not None:
            tone = "strong" if gdp > 3 else ("moderate" if gdp > 1 else "weak")
            parts.append(f"Real GDP growth is {tone} at {gdp:.2f}% annualised.")

        if unemp is not None:
            tone = "tight" if unemp < 4.5 else ("loosening" if unemp < 6 else "elevated")
            parts.append(f"The labour market is {tone} with unemployment at {unemp:.1f}%.")

        # Yield curve shape
        t2 = yc.get("2y")
        t10 = yc.get("10y")
        t30 = yc.get("30y")
        if t10 is not None:
            parts.append(f"The 10-year Treasury yields {t10:.2f}%.")
        if t2 is not None and t10 is not None:
            spread = t10 - t2
            if spread < 0:
                parts.append(
                    f"The yield curve is inverted (2Y–10Y spread: {spread:.2f}%), "
                    "historically a recession warning signal."
                )
            else:
                parts.append(
                    f"The yield curve is normal (2Y–10Y spread: +{spread:.2f}%)."
                )
        if t30 is not None:
            parts.append(f"The 30-year Treasury yields {t30:.2f}%.")

        if not parts:
            return "Macro data is currently unavailable."

        return "  ".join(parts)
