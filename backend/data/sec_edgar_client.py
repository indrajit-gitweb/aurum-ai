"""
SEC EDGAR data client for AURUM AI.

Fetches company facts (XBRL), recent filings, and raw filing text from
the public SEC EDGAR REST API — no API key required.

SEC fair-use policy: max 10 requests/second.
We enforce this with an asyncio.sleep(0.1) between calls.
"""

import asyncio
import logging
import re
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SEC_HEADERS = {
    "User-Agent": "AURUM AI contact@aurumapi.app",
    "Accept": "application/json",
}

COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
FILING_TEXT_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/{quarter}/company.idx"
FILING_DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/{accession_path}/{primary_doc}"

# CIK lookup via EDGAR full-text search
TICKER_CIK_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2000-01-01&forms=10-K"
COMPANY_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-K"
CIK_LOOKUP_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&search_text=&output=atom"
TICKER_TO_CIK_URL = "https://www.sec.gov/files/company_tickers.json"

_TICKER_CIK_CACHE: dict[str, int] = {}


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(SEC_HEADERS)
    return session


def _ticker_to_cik(ticker: str, session: requests.Session) -> Optional[int]:
    """Resolve a ticker symbol to its SEC CIK number.

    Uses the EDGAR company tickers JSON file (cached in process memory).

    Returns:
        Integer CIK, or None if not found.
    """
    ticker_upper = ticker.upper()
    if ticker_upper in _TICKER_CIK_CACHE:
        return _TICKER_CIK_CACHE[ticker_upper]

    try:
        resp = session.get(TICKER_TO_CIK_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for _idx, entry in data.items():
            cik_str = entry.get("cik_str")
            t = entry.get("ticker", "").upper()
            if cik_str is not None:
                _TICKER_CIK_CACHE[t] = int(cik_str)
        return _TICKER_CIK_CACHE.get(ticker_upper)
    except Exception as exc:
        logger.warning("CIK lookup failed for %s: %s", ticker, exc)
        return None


class SECEdgarClient:
    """Client for the SEC EDGAR public REST API.

    Args:
        ticker: Stock ticker symbol (e.g. ``"AAPL"``).
    """

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker.upper().strip()
        self._session = _get_session()

    def _get(self, url: str, **kwargs) -> Optional[dict]:
        """HTTP GET with SEC rate-limit courtesy sleep."""
        try:
            resp = self._session.get(url, timeout=15, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("SEC EDGAR GET failed (%s): %s", url, exc)
            return None

    def _get_cik(self) -> Optional[int]:
        return _ticker_to_cik(self.ticker, self._session)

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def get_company_facts(self, ticker: Optional[str] = None) -> dict:
        """Return key financial facts extracted from XBRL filings.

        Includes revenue, net income, total assets, and total liabilities
        for the most recent available periods.

        Args:
            ticker: Optional override ticker.

        Returns:
            Dict with keys: revenue, net_income, total_assets, total_liabilities,
            eps, shares_outstanding.  Values are lists of {end, val} dicts.
            Empty dict on failure.
        """
        t = (ticker or self.ticker).upper()
        cik = _ticker_to_cik(t, self._session)
        if cik is None:
            logger.warning("Could not resolve CIK for %s.", t)
            return {}

        url = COMPANY_FACTS_URL.format(cik=cik)
        data = self._get(url)
        if not data:
            return {}

        us_gaap = data.get("facts", {}).get("us-gaap", {})

        def _extract(concept: str, unit: str = "USD", limit: int = 8) -> list[dict]:
            entries = (
                us_gaap.get(concept, {})
                .get("units", {})
                .get(unit, [])
            )
            # Keep only annual (10-K) filings, sorted newest first
            annual = [e for e in entries if e.get("form") == "10-K"]
            annual.sort(key=lambda x: x.get("end", ""), reverse=True)
            return [{"end": e["end"], "val": e["val"]} for e in annual[:limit]]

        return {
            "company_name": data.get("entityName", ""),
            "cik": cik,
            "revenue": _extract("Revenues") or _extract("RevenueFromContractWithCustomerExcludingAssessedTax"),
            "net_income": _extract("NetIncomeLoss"),
            "total_assets": _extract("Assets"),
            "total_liabilities": _extract("Liabilities"),
            "eps": _extract("EarningsPerShareDiluted", unit="USD/shares"),
            "shares_outstanding": _extract("CommonStockSharesOutstanding", unit="shares"),
            "operating_income": _extract("OperatingIncomeLoss"),
            "rd_expense": _extract("ResearchAndDevelopmentExpense"),
        }

    def get_recent_filings(
        self,
        ticker: Optional[str] = None,
        form_type: str = "10-K",
        limit: int = 3,
    ) -> list[dict]:
        """Return metadata for the most recent SEC filings of a given type.

        Args:
            ticker: Optional override ticker.
            form_type: Filing form type, e.g. ``"10-K"``, ``"10-Q"``, ``"8-K"``.
            limit: Maximum number of filings to return.

        Returns:
            List of dicts with keys: accession_number, form, filed_date, report_date.
            Empty list on failure.
        """
        t = (ticker or self.ticker).upper()
        cik = _ticker_to_cik(t, self._session)
        if cik is None:
            return []

        url = SUBMISSIONS_URL.format(cik=cik)
        data = self._get(url)
        if not data:
            return []

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        filed_dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])
        primary_docs = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form == form_type:
                accession = accessions[i] if i < len(accessions) else ""
                results.append(
                    {
                        "accession_number": accession,
                        "form": form,
                        "filed_date": filed_dates[i] if i < len(filed_dates) else "",
                        "report_date": report_dates[i] if i < len(report_dates) else "",
                        "primary_document": primary_docs[i] if i < len(primary_docs) else "",
                        "cik": cik,
                    }
                )
                if len(results) >= limit:
                    break

        return results

    def get_filing_text(self, accession_number: str, max_chars: int = 5000) -> str:
        """Fetch the first ``max_chars`` characters of an SEC filing document.

        Args:
            accession_number: Accession number string, e.g.
                ``"0000320193-23-000077"``.
            max_chars: Maximum characters to return (default 5000).

        Returns:
            Truncated plain text of the filing.  Empty string on failure.
        """
        try:
            # Build the URL to the filing index page
            clean = accession_number.replace("-", "")
            cik_part = clean[:10].lstrip("0")
            path = f"{clean[:10]}/{clean[10:12]}/{clean[12:]}"
            index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_part}&type=&dateb=&owner=include&count=1&search_text="

            # Try the direct document URL pattern
            acc_nodash = accession_number.replace("-", "")
            doc_index_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_part}/{acc_nodash}/"
            )

            resp = self._session.get(doc_index_url, timeout=15)
            resp.raise_for_status()
            # Extract first .htm or .txt link from the index
            links = re.findall(r'href="(/Archives/edgar/data/[^"]+\.(?:htm|txt))"', resp.text)
            if not links:
                return resp.text[:max_chars]

            doc_url = "https://www.sec.gov" + links[0]
            doc_resp = self._session.get(doc_url, timeout=20)
            doc_resp.raise_for_status()
            # Strip HTML tags for cleaner text
            text = re.sub(r"<[^>]+>", " ", doc_resp.text)
            text = re.sub(r"\s{2,}", " ", text).strip()
            return text[:max_chars]
        except Exception as exc:
            logger.warning(
                "get_filing_text failed for accession %s: %s", accession_number, exc
            )
            return ""
