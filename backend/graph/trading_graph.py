"""
AURUM AI — LangGraph trading analysis workflow.

Pipeline topology (arrows = data dependency, parallel branches run concurrently):

  data_fetch
      │
      ├── fundamentals_node ─┐
      ├── technical_node    ─┤
      ├── news_node          ─┤ → merge_data
      └── macro_node        ─┘
                                │
                        [persona nodes — parallel]
                                │
                        debate_bull_node
                        debate_bear_node
                        research_manager_node
                                │
                        [risk nodes — parallel]
                                │
                        portfolio_manager_node → FinalResult

The graph is implemented as a manual async pipeline (not using the full
LangGraph StateGraph API) so it works without a LangGraph server.  Each
"node" is an async function that reads from and writes to ``AurumState``.

IMPORTANT: All synchronous blocking I/O (yfinance, FRED, SEC EDGAR, LLM API
calls) is wrapped in ``asyncio.to_thread()`` so the event loop is never
blocked.  This enables genuine concurrency in the gather() calls and keeps
the WebSocket heartbeat alive throughout the analysis.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, Optional, TypedDict

from data.yfinance_client import YFinanceClient
from data.sec_edgar_client import SECEdgarClient
from data.fred_client import FREDClient
from llm.router import LLMRouter, AllProvidersExhaustedError
from agents import PERSONA_REGISTRY, PERSONA_INFO, DEBATE_REGISTRY, RISK_REGISTRY

# Import main's Pydantic models (avoid circular — import lazily inside methods)
# We re-define lightweight dataclasses here to keep the graph self-contained.
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TickerNotFoundError(Exception):
    """Raised when yfinance returns no price data for the requested ticker."""
    pass


def _ticker_not_found_message(ticker: str) -> str:
    """Return a human-readable error message with exchange-suffix hints."""
    base = ticker.upper().split(".")[0]   # strip any existing suffix
    return (
        f"No market data found for \"{ticker}\". "
        f"yfinance could not find this symbol on any US exchange.\n\n"
        f"If this is a non-US stock, add the exchange suffix:\n"
        f"  • Indian stocks (NSE): {base}.NS  — e.g. RELIANCE.NS, TCS.NS, INFY.NS\n"
        f"  • Indian stocks (BSE): {base}.BO  — e.g. RELIANCE.BO\n"
        f"  • UK stocks (LSE):     {base}.L   — e.g. BP.L, HSBA.L, VOD.L\n"
        f"  • German stocks:       {base}.DE  — e.g. BMW.DE, SAP.DE\n"
        f"  • Hong Kong:           {base}.HK  — e.g. 0700.HK\n\n"
        f"For US stocks verify the exact ticker at finance.yahoo.com"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Persona registry (minimal fallback for unknown personas)
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_PERSONAS = ["buffett", "burry"]


# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────

class AurumState(TypedDict, total=False):
    """Shared mutable state passed through the pipeline nodes."""

    # Inputs
    ticker: str
    start_date: str
    end_date: str
    personas: list[str]
    analysis_mode: str          # "current" | "historical"

    # Data layer
    price_history: Any          # pd.DataFrame
    fundamentals: dict
    balance_sheet: dict
    income_statement: dict
    cashflow: dict
    news: list[dict]
    insider_transactions: list[dict]
    earnings_calendar: dict
    analyst_recommendations: dict
    institutional_ownership: dict
    shares_history: dict
    technical_indicators: dict
    sec_facts: dict
    sec_filings: list[dict]     # 10-K filings (metadata + accession number)
    sec_filings_q: list[dict]   # 10-Q filings (metadata + accession number)
    filing_text_excerpt: str    # first ~3 000 chars of the most recent 10-K
    peer_comparison: list[dict] # key ratios for 2–3 sector peers
    macro_summary: str
    yield_curve: dict

    # Persona analysis
    persona_signals: list[dict]  # list of PersonaSignalDict

    # Debate
    bull_arguments: list[str]
    bear_arguments: list[str]
    research_synthesis: str

    # Research Manager signal (for risk agents)
    research_manager_signal: dict

    # Risk
    aggressive_view: str
    conservative_view: str
    neutral_view: str
    aggressive_signal: str
    aggressive_confidence: int
    aggressive_key_points: list
    conservative_signal: str
    conservative_confidence: int
    conservative_key_points: list
    neutral_signal: str
    neutral_confidence: int
    neutral_key_points: list

    # Final
    verdict: str
    confidence: int
    target_price: Optional[float]
    summary: str
    bull_case: str
    bear_case: str
    risk_assessment: str
    key_metrics: dict


@dataclass
class PersonaSignalDict:
    agent: str
    signal: str        # "bullish" | "bearish" | "neutral"
    confidence: int    # 0–100
    reasoning: str
    key_points: list = field(default_factory=list)  # 3-5 bullet points from the model


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass (mirrors main.FinalResult without the Pydantic dependency)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FinalResult:
    verdict: str
    confidence: int
    target_price: Optional[float]
    summary: str
    persona_signals: list
    bull_case: str
    bear_case: str
    risk_assessment: str
    key_metrics: dict
    research_synthesis: str = ""
    aggressive_risk: str = ""
    aggressive_risk_signal: str = ""
    aggressive_risk_confidence: int = 0
    aggressive_risk_key_points: list = field(default_factory=list)
    conservative_risk: str = ""
    conservative_risk_signal: str = ""
    conservative_risk_confidence: int = 0
    conservative_risk_key_points: list = field(default_factory=list)
    neutral_risk: str = ""
    neutral_risk_signal: str = ""
    neutral_risk_confidence: int = 0
    neutral_risk_key_points: list = field(default_factory=list)

    def dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "target_price": self.target_price,
            "summary": self.summary,
            "persona_signals": [
                (s.__dict__ if hasattr(s, "__dict__") else s)
                for s in self.persona_signals
            ],
            "bull_case": self.bull_case,
            "bear_case": self.bear_case,
            "risk_assessment": self.risk_assessment,
            "key_metrics": self.key_metrics,
            "research_synthesis": self.research_synthesis,
            "aggressive_risk": self.aggressive_risk,
            "aggressive_risk_signal": self.aggressive_risk_signal,
            "aggressive_risk_confidence": self.aggressive_risk_confidence,
            "aggressive_risk_key_points": self.aggressive_risk_key_points,
            "conservative_risk": self.conservative_risk,
            "conservative_risk_signal": self.conservative_risk_signal,
            "conservative_risk_confidence": self.conservative_risk_confidence,
            "conservative_risk_key_points": self.conservative_risk_key_points,
            "neutral_risk": self.neutral_risk,
            "neutral_risk_signal": self.neutral_risk_signal,
            "neutral_risk_confidence": self.neutral_risk_confidence,
            "neutral_risk_key_points": self.neutral_risk_key_points,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def _safe_llm_invoke(
    llm_router: LLMRouter,
    messages: list[dict],
    task_type: str = "quick",
    fallback: str = "Analysis unavailable.",
) -> str:
    """Call LLMRouter.invoke and return fallback string on any error.
    NOTE: This is a synchronous function — always call via _async_llm_invoke.
    """
    try:
        return llm_router.invoke(messages, task_type=task_type)
    except AllProvidersExhaustedError as exc:
        logger.error("All LLM providers exhausted: %s", exc)
        return fallback
    except Exception as exc:
        logger.error("LLM invoke error: %s", exc)
        return fallback


async def _async_llm_invoke(
    llm_router: LLMRouter,
    messages: list[dict],
    task_type: str = "quick",
    fallback: str = "Analysis unavailable.",
) -> str:
    """Async wrapper: runs the synchronous LLM call in a thread pool so
    the asyncio event loop is never blocked.
    """
    return await asyncio.to_thread(
        _safe_llm_invoke, llm_router, messages, task_type, fallback
    )


def _fmt_fundamentals(f: dict) -> str:
    """Format fundamentals dict into a readable string for LLM prompts."""
    if not f:
        return "Fundamentals data unavailable."
    lines = []
    for key, val in f.items():
        if val is None:
            continue
        if isinstance(val, float) and abs(val) > 1_000_000:
            lines.append(f"  {key}: ${val:,.0f}")
        elif isinstance(val, float):
            lines.append(f"  {key}: {val:.4f}")
        else:
            lines.append(f"  {key}: {val}")
    return "\n".join(lines) if lines else "No fundamental data."


def _fmt_technicals(t: dict) -> str:
    if not t:
        return "Technical data unavailable."
    lines = []
    for k, v in t.items():
        if v is None:
            continue
        lines.append(f"  {k}: {v:.2f}" if isinstance(v, float) else f"  {k}: {v}")
    return "\n".join(lines) if lines else "No technical data."


def _fmt_news(news: list[dict], limit: int = 5) -> str:
    if not news:
        return "No recent news."
    lines = [f"- {n['title']} ({n.get('publisher', '')})" for n in news[:limit]]
    return "\n".join(lines)


def _parse_signal_from_text(text: str) -> tuple[str, int]:
    """Extract signal and confidence from a freeform LLM response.

    Returns:
        (signal, confidence) where signal is "bullish" | "bearish" | "neutral"
        and confidence is 0–100.
    """
    lower = text.lower()

    if "strong buy" in lower or "strongly bullish" in lower:
        signal = "bullish"
        default_conf = 85
    elif "bullish" in lower or "buy" in lower:
        signal = "bullish"
        default_conf = 70
    elif "strong sell" in lower or "strongly bearish" in lower:
        signal = "bearish"
        default_conf = 85
    elif "bearish" in lower or "sell" in lower:
        signal = "bearish"
        default_conf = 70
    else:
        signal = "neutral"
        default_conf = 50

    # Try to extract an explicit percentage
    import re
    matches = re.findall(r"confidence[:\s]+(\d{1,3})\s*%", lower)
    if matches:
        try:
            return signal, min(100, max(0, int(matches[0])))
        except ValueError:
            pass
    # Also look for bare "XX%" pattern
    pct_matches = re.findall(r"\b(\d{1,3})\s*%", lower)
    if pct_matches:
        candidates = [int(p) for p in pct_matches if 30 <= int(p) <= 100]
        if candidates:
            return signal, candidates[0]

    return signal, default_conf


def _verdict_from_signals(signals: list[PersonaSignalDict]) -> tuple[str, int]:
    """Derive consensus verdict from persona signals.

    Returns (verdict_string, avg_confidence).
    """
    if not signals:
        return "HOLD", 50

    bull_scores = []
    bear_scores = []
    neutral_scores = []

    for s in signals:
        if s.signal == "bullish":
            bull_scores.append(s.confidence)
        elif s.signal == "bearish":
            bear_scores.append(s.confidence)
        else:
            neutral_scores.append(s.confidence)

    total = len(signals)
    bull_pct = len(bull_scores) / total
    bear_pct = len(bear_scores) / total

    avg_conf = int(
        sum(s.confidence for s in signals) / total
    )

    if bull_pct >= 0.7:
        verdict = "STRONG BUY" if avg_conf >= 75 else "BUY"
    elif bull_pct >= 0.5:
        verdict = "BUY"
    elif bear_pct >= 0.7:
        verdict = "STRONG SELL" if avg_conf >= 75 else "SELL"
    elif bear_pct >= 0.5:
        verdict = "SELL"
    else:
        verdict = "HOLD"

    return verdict, avg_conf


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline nodes — all blocking I/O runs in asyncio.to_thread()
# ─────────────────────────────────────────────────────────────────────────────

async def _node_data_fetch(state: AurumState, on_event: Callable) -> None:
    """Fetch all raw data (price history) — entry point of the graph."""
    await on_event(
        {
            "type": "agent_start",
            "agent": "data_fetcher",
            "message": f"Fetching price history for {state['ticker']}...",
        }
    )
    yf_client = YFinanceClient(state["ticker"])
    # Run blocking yfinance call in thread pool so event loop stays free
    df = await asyncio.to_thread(
        yf_client.get_price_history, state["start_date"], state["end_date"]
    )
    state["price_history"] = df

    if df.empty:
        raise TickerNotFoundError(_ticker_not_found_message(state["ticker"]))

    await on_event(
        {
            "type": "agent_complete",
            "agent": "data_fetcher",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": f"Retrieved {len(df)} trading days of price data.",
        }
    )


async def _node_fundamentals(state: AurumState, on_event: Callable) -> None:
    await on_event(
        {
            "type": "agent_start",
            "agent": "fundamentals_analyst",
            "message": "Fetching financial fundamentals, balance sheet, income statement, and cash flow...",
        }
    )
    yf = YFinanceClient(state["ticker"])
    historical = state.get("analysis_mode", "current") == "historical"
    end_date   = state.get("end_date", "")

    # Run all six yfinance fundamental calls concurrently in thread pool.
    # In historical mode the three financial-statement calls pull the annual
    # filing closest to end_date instead of always the latest.
    if historical:
        fundamentals, balance_sheet, income_statement, cashflow, inst_ownership, shares_history = await asyncio.gather(
            asyncio.to_thread(yf.get_fundamentals),
            asyncio.to_thread(yf.get_historical_balance_sheet, end_date),
            asyncio.to_thread(yf.get_historical_income_statement, end_date),
            asyncio.to_thread(yf.get_historical_cashflow, end_date),
            asyncio.to_thread(yf.get_institutional_ownership),
            asyncio.to_thread(yf.get_shares_outstanding_change),
        )
    else:
        fundamentals, balance_sheet, income_statement, cashflow, inst_ownership, shares_history = await asyncio.gather(
            asyncio.to_thread(yf.get_fundamentals),
            asyncio.to_thread(yf.get_balance_sheet),
            asyncio.to_thread(yf.get_income_statement),
            asyncio.to_thread(yf.get_cashflow),
            asyncio.to_thread(yf.get_institutional_ownership),
            asyncio.to_thread(yf.get_shares_outstanding_change),
        )
    state["fundamentals"] = fundamentals
    state["balance_sheet"] = balance_sheet
    state["income_statement"] = income_statement
    state["cashflow"] = cashflow
    state["institutional_ownership"] = inst_ownership
    state["shares_history"] = shares_history

    # SEC EDGAR facts — also in thread pool
    try:
        sec = SECEdgarClient(state["ticker"])
        # Sequential with a small delay to respect SEC EDGAR's rate limits
        sec_facts = await asyncio.to_thread(sec.get_company_facts)
        await asyncio.sleep(0.6)
        sec_filings = await asyncio.to_thread(
            functools.partial(sec.get_recent_filings, form_type="10-K", limit=3)
        )
        state["sec_facts"] = sec_facts
        state["sec_filings"] = sec_filings

        # Also grab the 4 most recent quarterly (10-Q) filings for the log
        await asyncio.sleep(0.4)
        try:
            sec_filings_q = await asyncio.to_thread(
                functools.partial(sec.get_recent_filings, form_type="10-Q", limit=4)
            )
            state["sec_filings_q"] = sec_filings_q
        except Exception as exc_q:
            logger.warning("10-Q filings fetch failed: %s", exc_q)
            state["sec_filings_q"] = []

        # Fetch up to 80 000 chars of the most recent 10-K.
        # This reliably covers Item 1 (Business) + Item 1A (Risk Factors) for
        # virtually all filers.  Each persona receives a targeted slice of this
        # text so no LLM is flooded with the full document.
        filing_text_excerpt = ""
        if sec_filings:
            await asyncio.sleep(0.6)   # SEC rate-limit courtesy
            try:
                filing_text_excerpt = await asyncio.to_thread(
                    functools.partial(
                        sec.get_filing_text,
                        accession_number=sec_filings[0]["accession_number"],
                        max_chars=80000,
                    )
                )
            except Exception as exc_ft:
                logger.warning("10-K filing text fetch failed: %s", exc_ft)
        state["filing_text_excerpt"] = filing_text_excerpt

    except Exception as exc:
        logger.warning("SEC EDGAR fetch failed: %s", exc)
        state["sec_facts"] = {}
        state["sec_filings"] = []
        state["sec_filings_q"] = []
        state["filing_text_excerpt"] = ""

    # Peer comparison — 2–3 sector peers with key valuation ratios.
    # Runs after fundamentals are stored so we have sector/industry available.
    try:
        industry = fundamentals.get("industry", "")
        sector   = fundamentals.get("sector", "")
        state["peer_comparison"] = await asyncio.to_thread(
            functools.partial(yf.get_peer_comparison, industry=industry, sector=sector)
        )
    except Exception as exc_p:
        logger.warning("Peer comparison fetch failed: %s", exc_p)
        state["peer_comparison"] = []

    await on_event(
        {
            "type": "agent_complete",
            "agent": "fundamentals_analyst",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": "Fundamental data collected.",
        }
    )


async def _node_technical(state: AurumState, on_event: Callable) -> None:
    await on_event(
        {
            "type": "agent_start",
            "agent": "technical_analyst",
            "message": "Computing RSI, MACD, Bollinger Bands, and moving averages...",
        }
    )
    yf = YFinanceClient(state["ticker"])
    state["technical_indicators"] = await asyncio.to_thread(
        functools.partial(
            yf.get_technical_indicators,
            start=state["start_date"],
            end=state["end_date"],
        )
    )
    await on_event(
        {
            "type": "agent_complete",
            "agent": "technical_analyst",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": "Technical indicators computed.",
        }
    )


async def _node_news(state: AurumState, on_event: Callable) -> None:
    await on_event(
        {
            "type": "agent_start",
            "agent": "news_analyst",
            "message": f"Fetching latest news and insider transactions for {state['ticker']}...",
        }
    )
    yf_client = YFinanceClient(state["ticker"])
    # Fetch news, insider transactions, earnings calendar, analyst recs — all concurrently
    news, insider_txns, cal, analyst_recs = await asyncio.gather(
        asyncio.to_thread(functools.partial(yf_client.get_news, limit=20)),
        asyncio.to_thread(yf_client.get_insider_transactions),
        asyncio.to_thread(yf_client.get_earnings_calendar),
        asyncio.to_thread(yf_client.get_analyst_recommendations),
    )
    state["news"] = news
    state["insider_transactions"] = insider_txns
    state["earnings_calendar"] = cal
    state["analyst_recommendations"] = analyst_recs

    await on_event(
        {
            "type": "agent_complete",
            "agent": "news_analyst",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": (
                f"Retrieved {len(state.get('news', []))} articles, "
                f"{len(state.get('insider_transactions', []))} insider txns, "
                f"analyst consensus: {analyst_recs.get('consensus', 'N/A')} "
                f"({analyst_recs.get('total_analysts', 0)} analysts)."
            ),
        }
    )


async def _node_macro(state: AurumState, on_event: Callable) -> None:
    await on_event(
        {
            "type": "agent_start",
            "agent": "macro_analyst",
            "message": "Fetching macro-economic indicators from FRED...",
        }
    )
    fred = FREDClient()
    # Run both FRED calls concurrently in thread pool
    macro_summary, yield_curve = await asyncio.gather(
        asyncio.to_thread(fred.get_macro_summary),
        asyncio.to_thread(fred.get_yield_curve),
    )
    state["macro_summary"] = macro_summary
    state["yield_curve"] = yield_curve
    await on_event(
        {
            "type": "agent_complete",
            "agent": "macro_analyst",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": "Macro snapshot complete.",
        }
    )


async def _node_persona(
    persona_id: str,
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> PersonaSignalDict:
    """Run a single investor persona's analysis using the full agent class."""
    persona_name = PERSONA_INFO.get(persona_id, {}).get("name", persona_id.title())

    await on_event(
        {
            "type": "agent_start",
            "agent": persona_id,
            "message": f"{persona_name} is analysing {state['ticker']}...",
        }
    )

    # Use the proper agent class from the registry for authentic, rich prompts
    AgentClass = PERSONA_REGISTRY.get(persona_id)
    if AgentClass is None:
        signal, confidence, reasoning = "neutral", 50, f"{persona_name} unavailable."
    else:
        try:
            agent = AgentClass(llm_router)
            fund  = state.get("fundamentals", {})
            tech  = state.get("technical_indicators", {})
            cf    = state.get("cashflow", {})
            inc   = state.get("income_statement", {})

            # Build price_data for technical_analyst (BUG-04 fix)
            current_price = tech.get("current_price")
            high_52w      = fund.get("52w_high")
            low_52w       = fund.get("52w_low")
            price_data = {
                "current_price":    current_price,
                "week_52_high":     high_52w,
                "week_52_low":      low_52w,
                "pct_from_52w_high": (
                    round((current_price / high_52w - 1) * 100, 2)
                    if current_price and high_52w and high_52w > 0 else None
                ),
                "avg_volume_30d":   fund.get("avg_volume"),
            }

            # Enrich income statement with revenue_growth_yoy from fundamentals
            inc_enriched = {
                **inc,
                "revenue_growth_yoy": (
                    inc.get("revenue_growth_yoy")
                    or fund.get("revenue_growth_yoy")
                    or fund.get("revenue_growth")
                ),
            }

            # Enrich cashflow with fcf_margin (needs revenue from income stmt)
            rev = inc.get("revenue") or inc.get("total_revenue")
            fcf = cf.get("fcf") or cf.get("free_cash_flow")
            bal = state.get("balance_sheet", {})
            cf_enriched = {
                **cf,
                "fcf_margin": (
                    round(fcf / rev, 4) if fcf and rev and rev != 0 else None
                ),
                # Propagate working_capital_change from balance sheet so Damodaran can read it
                "working_capital_change": bal.get("working_capital_change"),
            }

            # Compute ROIC-WACC spread now that we have yield curve + fundamentals
            yield_curve = state.get("yield_curve", {})
            try:
                roic  = fund.get("roic")
                beta  = fund.get("beta") or 1.0
                rf    = float(yield_curve.get("10y") or 4.5) / 100  # 10Y treasury
                erp   = 0.055           # Damodaran equity risk premium estimate
                cost_of_equity = rf + beta * erp
                debt_to_cap    = fund.get("debt_to_capital") or 0.3
                after_tax_cod  = (fund.get("cost_of_debt") or 0.05) * 0.75
                wacc           = cost_of_equity * (1 - debt_to_cap) + after_tax_cod * debt_to_cap
                roic_wacc_spread = round(roic - wacc, 4) if roic is not None else None
            except Exception:
                wacc             = None
                roic_wacc_spread = None

            # ── Enrich fund with multi-year trends from SEC EDGAR XBRL ──────────
            sec_facts = state.get("sec_facts", {})
            try:
                rev_series = [r for r in sec_facts.get("revenue", []) if r.get("val")]
                ni_series  = [r for r in sec_facts.get("net_income", []) if r.get("val")]
                eps_series = [r for r in sec_facts.get("eps", []) if r.get("val")]

                rev_vals: list = []
                if rev_series:
                    rev_vals = [r["val"] for r in rev_series]
                    if len(rev_vals) >= 4:
                        cagr_3yr = (rev_vals[0] / rev_vals[3]) ** (1 / 3) - 1
                        fund.setdefault("revenue_cagr_3yr", f"{cagr_3yr:+.1%}")
                    if len(rev_vals) >= 6:
                        cagr_5yr = (rev_vals[0] / rev_vals[5]) ** (1 / 5) - 1
                        fund.setdefault("revenue_cagr_5yr", f"{cagr_5yr:+.1%}")
                    rev_hist = " | ".join(
                        f"{r['end'][:4]}: ${r['val']/1e9:.1f}B" for r in rev_series[:5]
                    )
                    fund.setdefault("revenue_history_5yr", rev_hist)

                if ni_series:
                    ni_vals = [r["val"] for r in ni_series]
                    ni_hist = " | ".join(
                        f"{r['end'][:4]}: ${r['val']/1e9:.1f}B" for r in ni_series[:5]
                    )
                    fund.setdefault("net_income_history_5yr", ni_hist)
                    if len(ni_vals) >= 2 and ni_vals[1] != 0:
                        fund.setdefault("net_income_growth_yoy", f"{ni_vals[0]/ni_vals[1]-1:+.1%}")

                # EPS 5yr CAGR from SEC EDGAR
                if len(eps_series) >= 6:
                    e_vals = [r["val"] for r in eps_series]
                    if e_vals[5] and e_vals[5] != 0 and e_vals[0] / e_vals[5] > 0:
                        fund.setdefault("eps_cagr_5yr", f"{(e_vals[0]/e_vals[5])**(1/5)-1:+.1%}")
                if len(eps_series) >= 4:
                    e_vals = [r["val"] for r in eps_series]
                    if e_vals[3] and e_vals[3] != 0 and e_vals[0] / e_vals[3] > 0:
                        fund.setdefault("eps_cagr_3yr", f"{(e_vals[0]/e_vals[3])**(1/3)-1:+.1%}")

            except Exception as exc_sec:
                logger.debug("SEC CAGR enrichment skipped: %s", exc_sec)

            # ── Compute derived ratios that many personas reference ────────────
            try:
                # PEG = trailing P/E ÷ EPS growth rate (as %)
                pe_v  = fund.get("pe_ratio")
                g_pct = None
                # Prefer SEC-computed CAGRs — formatted as percentage strings "+12.3%"
                g_str = fund.get("eps_cagr_5yr") or fund.get("revenue_cagr_5yr")
                if g_str and g_str != "N/A":
                    g_pct = float(str(g_str).replace("%", "").replace("+", ""))
                else:
                    # yfinance returns revenue_growth_yoy as raw decimal (0.123 = 12.3%)
                    raw = inc.get("revenue_growth_yoy")
                    if raw is not None:
                        g_pct = float(raw) * 100   # convert to percentage points
                if pe_v and g_pct and g_pct > 0:
                    fund.setdefault("peg_ratio", round(float(pe_v) / g_pct, 2))
            except Exception:
                pass

            try:
                # Net Debt / EBITDA
                td     = fund.get("total_debt") or 0
                cash_v = fund.get("total_cash") or \
                         state.get("balance_sheet", {}).get("cash") or 0
                ebitda_v = fund.get("ebitda")
                if ebitda_v and ebitda_v != 0:
                    fund.setdefault("net_debt_ebitda", round((td - cash_v) / abs(ebitda_v), 2))
            except Exception:
                pass

            try:
                # CapEx / Revenue
                capex_v = abs(cf.get("capex") or cf.get("capital_expenditure") or 0)
                rev_v   = inc.get("revenue") or inc.get("total_revenue")
                if capex_v and rev_v and rev_v != 0:
                    fund.setdefault("capex_to_revenue", f"{capex_v/rev_v:.1%}")
            except Exception:
                pass

            try:
                # Cash burn: negative operating_cf − capex (for pre-profit companies)
                op_cf = cf.get("operating_cash_flow") or cf.get("operating_cf") or 0
                capex_b = abs(cf.get("capex") or 0)
                net_cf = op_cf - capex_b
                fund.setdefault("cash_burn", round(net_cf, 0))   # negative = burning
            except Exception:
                pass

            try:
                # Forward EPS growth: (forward_eps - trailing_eps) / abs(trailing_eps)
                fwd_eps = fund.get("forward_eps")
                trail_eps = fund.get("eps")
                if fwd_eps and trail_eps and trail_eps != 0:
                    fwd_growth = (fwd_eps - trail_eps) / abs(trail_eps)
                    fund.setdefault("forward_eps_growth", f"{fwd_growth:+.1%}")
            except Exception:
                pass

            try:
                # Revenue per employee
                employees = fund.get("employees")
                rev_e = inc.get("revenue") or inc.get("total_revenue")
                if employees and rev_e and employees > 0:
                    fund.setdefault("revenue_per_employee", round(rev_e / employees, 0))
            except Exception:
                pass

            try:
                # Earnings yield = 1 / PE
                pe_ey = fund.get("pe_ratio")
                if pe_ey and pe_ey != 0:
                    fund.setdefault("earnings_yield", f"{1/float(pe_ey):.1%}")
            except Exception:
                pass

            try:
                # Short interest as readable %
                si = fund.get("short_interest")
                if si is not None:
                    fund.setdefault("short_interest_pct", f"{float(si)*100:.1f}%")
            except Exception:
                pass

            # ── Wire institutional ownership into fund for Lynch/Pabrai ────────
            inst = state.get("institutional_ownership", {})
            if inst:
                fund.setdefault("institutional_ownership",
                    inst.get("pct_institutionally_held", "N/A"))
                fund.setdefault("top_institutional_holders",
                    ", ".join(h["name"] for h in inst.get("top_holders", [])[:3]))

            # ── Shares outstanding trend (buyback / dilution signal) ───────────
            try:
                shares_hist = state.get("shares_history", {})
                sc3 = shares_hist.get("shares_change_3yr")
                if sc3:
                    fund.setdefault("shares_change_3yr", sc3)
            except Exception:
                pass

            # ── Historical mode: recompute price-based multiples at end_date ──
            if state.get("analysis_mode", "current") == "historical":
                try:
                    hist_price = tech.get("current_price")   # last price in the window
                    hist_eps   = (inc.get("eps") or inc.get("basic_eps")
                                  or inc.get("diluted_eps"))
                    if hist_price and hist_eps and hist_eps != 0:
                        fund["pe_ratio"] = round(float(hist_price) / float(hist_eps), 2)
                    # Historical P/B = price / (book equity / shares)
                    eq_hist  = (bal.get("stockholders_equity") or bal.get("common_stock_equity"))
                    sh_hist  = (bal.get("ordinary_shares_number")
                                or fund.get("shares_outstanding"))
                    if hist_price and eq_hist and sh_hist and sh_hist != 0:
                        bvps_hist = eq_hist / sh_hist
                        if bvps_hist != 0:
                            fund["pb_ratio"] = round(float(hist_price) / float(bvps_hist), 2)
                    # Label the analysis period so personas see context
                    fund["analysis_as_of"] = f"{state['end_date']} (Historical)"
                except Exception:
                    pass

            fund_enriched = {
                **fund,
                "wacc":            round(wacc, 4) if wacc is not None else None,
                "cost_of_equity":  round(cost_of_equity, 4) if wacc is not None else None,
                "erp":             "5.5%",
                "roic_wacc_spread": roic_wacc_spread,
                # Alias for balance sheet agent access
                "bvps":            fund.get("bvps"),
            }

            # ── Per-persona 10-K text routing ─────────────────────────────────
            # Each entry: (chars_to_pass, focus_label_for_prompt)
            # chars_to_pass is a slice of the 80 000-char fetch so no LLM
            # receives the full document — only the section relevant to its
            # investment philosophy.
            #
            # Item 1  (Business)      ≈ chars   0 – 40 000
            # Item 1A (Risk Factors)  ≈ chars 20 000 – 60 000  (varies by filer)
            # Item 7  (MD&A)          ≈ chars 60 000+  (usually beyond our fetch)
            _FILING_TEXT_CFG: dict[str, tuple[int, str]] = {
                # ── Business-description focused ──────────────────────────────
                "fisher": (
                    30000,
                    "Item 1 — Business description. Evaluate against Fisher's "
                    "15-point Scuttlebutt checklist: products with growth potential, "
                    "R&D effectiveness, sales-force quality, customer relationships, "
                    "management integrity, long-term profit orientation.",
                ),
                "lynch": (
                    25000,
                    "Item 1 — Business description. Use this to classify the stock "
                    "into Lynch's 6 categories (slow grower / stalwart / fast grower / "
                    "cyclical / turnaround / asset play) and assess whether the "
                    "expansion story is replicable.",
                ),
                "pabrai": (
                    20000,
                    "Item 1 — Business description. Assess simplicity of the business "
                    "model, sources of competitive moat, and whether it passes the "
                    "Dhandho 'can a 10-year-old understand it' test.",
                ),
                "ackman": (
                    20000,
                    "Item 1 — Business description. Assess predictability, barriers "
                    "to entry, and any activist catalyst potential visible in the "
                    "business structure and operating model.",
                ),
                # ── Business + risk balance ───────────────────────────────────
                "buffett": (
                    20000,
                    "Item 1 + early Risk Factors. Focus on business quality, "
                    "competitive moat durability, and management's capital allocation "
                    "language.",
                ),
                "munger": (
                    15000,
                    "Item 1 + MD&A language. Focus on management tone, capital "
                    "allocation decisions, and quality of the business model.",
                ),
                # ── Risk-factors focused ──────────────────────────────────────
                "graham": (
                    25000,
                    "Item 1A — Risk Factors. Focus on earnings reliability warnings, "
                    "balance sheet quality issues, contingent liabilities, and any "
                    "hidden financial risks that threaten margin of safety.",
                ),
                "burry": (
                    30000,
                    "Item 1A — Risk Factors. Read every line. Surface off-balance-sheet "
                    "items, contingent liabilities, unusual accounting, customer "
                    "concentration, supply-chain dependencies, and anything that could "
                    "destroy the thesis.",
                ),
            }

            raw_filing = state.get("filing_text_excerpt", "")
            _cfg = _FILING_TEXT_CFG.get(persona_id)
            if _cfg and raw_filing:
                filing_chars, filing_label = _cfg
                filing_text  = raw_filing[:filing_chars]
            else:
                filing_text  = ""
                filing_label = ""

            # Analyst recs — summarised string for prompt embedding
            analyst_recs = state.get("analyst_recommendations", {})
            analyst_recs_str = (
                f"{analyst_recs.get('consensus', 'N/A')} "
                f"({analyst_recs.get('strong_buy', 0)} strong buy / "
                f"{analyst_recs.get('buy', 0)} buy / "
                f"{analyst_recs.get('hold', 0)} hold / "
                f"{analyst_recs.get('sell', 0)} sell / "
                f"{analyst_recs.get('strong_sell', 0)} strong sell, "
                f"{analyst_recs.get('total_analysts', 0)} analysts)"
                if analyst_recs else "N/A"
            )
            # Earnings calendar — next earnings date string
            cal = state.get("earnings_calendar", {})
            next_earnings = (
                cal.get("earnings_date") or cal.get("earnings_dates") or "N/A"
            )

            data = {
                "fundamentals":          fund_enriched,
                "balance_sheet":         state.get("balance_sheet", {}),
                "income_statement":      inc_enriched,
                "cashflow":              cf_enriched,
                "technical_indicators":  tech,
                "news":                  state.get("news", []),
                "news_articles":         state.get("news", []),       # alias
                "insider_transactions":  state.get("insider_transactions", []),
                "macro_summary":         state.get("macro_summary", ""),
                "sec_facts":             sec_facts,
                "filing_text_excerpt":   filing_text,
                "filing_text_label":     filing_label,
                "price_data":            price_data,
                "yield_curve":           yield_curve,
                # New enriched fields — available to ALL personas
                "analyst_recommendations_summary": analyst_recs_str,
                "analyst_recommendations":         analyst_recs,
                "next_earnings_date":              next_earnings,
                "earnings_calendar":               cal,
                # Field aliases various agents use
                "key_metrics":  fund_enriched,      # BUG-08 fix (was technical_indicators)
                "cash_flow":    cf_enriched,        # alias for fundamentals_analyst
                "company_info": fund_enriched,      # alias for macro_analyst
            }
            # Run the synchronous analyze() in a thread pool
            result = await asyncio.to_thread(agent.analyze, state["ticker"], data)
            signal = result.signal
            confidence = result.confidence
            reasoning = result.reasoning
            key_points = result.key_points
        except Exception as exc:
            logger.warning("Persona %s failed: %s", persona_id, exc)
            exc_str = str(exc)
            if "exhausted" in exc_str.lower() or "rate limit" in exc_str.lower() or "429" in exc_str:
                reasoning = (
                    "⚠ All free LLM providers are temporarily rate-limited. "
                    "Add your own API key (Groq, Gemini, or OpenRouter) in the sidebar "
                    "to get unlimited analysis without shared rate limits."
                )
                confidence = 0
            else:
                reasoning = f"Analysis failed: {exc_str[:300]}"
                confidence = 50
            signal = "neutral"
            key_points = []

    await on_event(
        {
            "type": "agent_complete",
            "agent": persona_id,
            "signal": signal,
            "confidence": confidence,
            "reasoning": reasoning,
        }
    )

    return PersonaSignalDict(
        agent=persona_id,
        signal=signal,
        confidence=confidence,
        reasoning=reasoning,
        key_points=key_points if isinstance(key_points, list) else [],
    )


async def _node_debate_bull(
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> None:
    await on_event({"type": "debate_start"})
    await on_event(
        {
            "type": "agent_start",
            "agent": "debate_bull",
            "message": "Bull analyst building the investment case...",
        }
    )

    bull_personas = [
        s for s in state.get("persona_signals", []) if s["signal"] == "bullish"
    ]
    bull_reasoning = "\n\n".join(
        f"**{s['agent'].title()}**: {s['reasoning'][:500]}" for s in bull_personas
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Bull Analyst in an investment debate.  "
                "Your job is to construct the strongest possible bull case for the stock, "
                "synthesising the bullish signals from multiple investor personas.  "
                "Be concise, data-driven, and persuasive."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Synthesise the following bullish views on {state['ticker']} "
                f"into a coherent bull case (3–5 paragraphs):\n\n{bull_reasoning}\n\n"
                f"Also incorporate key metrics:\n{_fmt_fundamentals(state.get('fundamentals', {}))}"
            ),
        },
    ]

    bull_case = await _async_llm_invoke(llm_router, messages, task_type="quick")
    state["bull_arguments"] = [bull_case]

    await on_event({"type": "debate_message", "side": "bull", "message": bull_case})
    await on_event({"type": "agent_complete", "agent": "debate_bull", "signal": "neutral", "confidence": 100, "reasoning": "Bull case built."})


async def _node_debate_bear(
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> None:
    await on_event(
        {
            "type": "agent_start",
            "agent": "debate_bear",
            "message": "Bear analyst building the counter-case...",
        }
    )

    bear_personas = [
        s for s in state.get("persona_signals", []) if s["signal"] == "bearish"
    ]
    bear_reasoning = "\n\n".join(
        f"**{s['agent'].title()}**: {s['reasoning'][:500]}" for s in bear_personas
    )
    if not bear_reasoning:
        bear_reasoning = "No explicit bearish signals — construct devil's advocate case."

    messages = [
        {
            "role": "system",
            "content": (
                "You are the Bear Analyst in an investment debate.  "
                "Construct the strongest possible bear case and highlight all risks, "
                "even if the overall consensus leans bullish.  Be honest and rigorous."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Construct a bear case for {state['ticker']} "
                f"synthesising bearish signals and risks:\n\n{bear_reasoning}\n\n"
                f"Technical context:\n{_fmt_technicals(state.get('technical_indicators', {}))}\n\n"
                f"Macro context:\n{state.get('macro_summary', '')}"
            ),
        },
    ]

    bear_case = await _async_llm_invoke(llm_router, messages, task_type="quick")
    state["bear_arguments"] = [bear_case]

    await on_event({"type": "debate_message", "side": "bear", "message": bear_case})
    await on_event({"type": "agent_complete", "agent": "debate_bear", "signal": "neutral", "confidence": 100, "reasoning": "Bear case built."})


async def _node_research_manager(
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> None:
    """Run the ResearchManager agent — the senior analyst who synthesises all signals.

    Uses the full ResearchManager class from DEBATE_REGISTRY which applies a
    structured scoring framework (bull/bear score, investment horizon, position sizing).
    """
    await on_event(
        {
            "type": "agent_start",
            "agent": "research_manager",
            "message": "Research Manager reading all signals and rendering final synthesis...",
        }
    )

    ResearchManagerClass = DEBATE_REGISTRY.get("research_manager")
    synthesis = "Analysis unavailable."
    signal_out = "neutral"
    confidence_out = 50

    if ResearchManagerClass is not None:
        try:
            # Transform state into the format ResearchManager.analyze() expects
            persona_signals_dict = {
                ps["agent"]: {
                    "signal":     ps["signal"],
                    "confidence": ps["confidence"],
                    "reasoning":  ps["reasoning"][:300],
                }
                for ps in state.get("persona_signals", [])
            }

            bull_text = "\n".join(state.get("bull_arguments", []))
            bear_text = "\n".join(state.get("bear_arguments", []))
            fund = state.get("fundamentals", {})
            tech = state.get("technical_indicators", {})
            current_price = tech.get("current_price")
            high_52w = fund.get("52w_high")

            data = {
                "persona_signals": persona_signals_dict,
                "bull_debate":  {"signal": "bullish", "reasoning": bull_text[:800]},
                "bear_debate":  {"signal": "bearish", "reasoning": bear_text[:800]},
                "analyst_reports": {},   # analyst LLM reports not yet in pipeline
                "company_info":  fund,
                "key_metrics":   fund,
                "price_data": {
                    "current_price":     current_price,
                    "week_52_high":      high_52w,
                    "week_52_low":       fund.get("52w_low"),
                    "pct_from_52w_high": (
                        round((current_price / high_52w - 1) * 100, 2)
                        if current_price and high_52w and high_52w > 0 else None
                    ),
                },
            }

            mgr = ResearchManagerClass(llm_router)
            result = await asyncio.to_thread(mgr.analyze, state["ticker"], data)
            synthesis = result.reasoning or synthesis
            signal_out = result.signal or signal_out
            confidence_out = result.confidence or confidence_out
        except Exception as exc:
            logger.warning("ResearchManager agent failed: %s", exc)
            # Fall back to a compact inline synthesis using the QUICK chain
            # (deep chain may already be exhausted by the time RM runs)
            signals_summary = "\n".join(
                f"- {s['agent'].title()}: {s['signal'].upper()} ({s['confidence']}%)"
                for s in state.get("persona_signals", [])
            )
            bull = "\n".join(state.get("bull_arguments", []))
            bear = "\n".join(state.get("bear_arguments", []))
            messages = [
                {"role": "system", "content": (
                    "You are the Head of Research. Given analyst signals and a bull/bear debate, "
                    "write a concise 2-paragraph synthesis: "
                    "(1) overall verdict and conviction level, "
                    "(2) top 2 risks to watch. Be direct and data-driven."
                )},
                {"role": "user", "content": (
                    f"Signals:\n{signals_summary}\n\n"
                    f"Bull:\n{bull[:400]}\n\nBear:\n{bear[:400]}"
                )},
            ]
            synthesis = await _async_llm_invoke(
                llm_router, messages,
                task_type="deep",   # Research Manager always uses the best reasoning model
                fallback="Synthesis unavailable — rate limits hit. Core verdict derived from persona vote.",
            )

    state["research_synthesis"] = synthesis
    state["research_manager_signal"] = {
        "signal": signal_out,
        "confidence": confidence_out,
        "reasoning": synthesis[:500],
    }

    await on_event(
        {
            "type": "agent_complete",
            "agent": "research_manager",
            "signal": signal_out,
            "confidence": confidence_out,
            "reasoning": synthesis[:300] + ("..." if len(synthesis) > 300 else ""),
        }
    )


async def _node_risk(
    profile: str,
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> None:
    """Run a risk-profile-specific view using the dedicated risk agent class."""
    profile_names = {
        "aggressive": "Aggressive Risk Analyst",
        "conservative": "Conservative Risk Analyst",
        "neutral": "Neutral Risk Analyst",
    }
    agent_key = f"{profile}_risk"
    RiskClass = RISK_REGISTRY.get(agent_key)

    await on_event({
        "type": "agent_start",
        "agent": f"risk_{profile}",
        "message": f"{profile_names.get(profile, profile.title())} evaluating position...",
    })

    if not RiskClass:
        logger.warning("No risk agent found for profile: %s", profile)
        state[f"{profile}_view"] = f"{profile.title()} risk assessment unavailable."  # type: ignore[literal-required]
        state[f"{profile}_signal"] = "neutral"  # type: ignore[literal-required]
        state[f"{profile}_confidence"] = 50  # type: ignore[literal-required]
        state[f"{profile}_key_points"] = []  # type: ignore[literal-required]
        return

    try:
        agent = RiskClass(llm_router)

        # Build data package matching what each risk agent's analyze() expects
        persona_signals_dict = {
            s["agent"]: s for s in state.get("persona_signals", [])
        }
        data = {
            "research_manager_signal": state.get("research_manager_signal", {
                "signal": "neutral", "confidence": 50
            }),
            "bear_debate":             {"reasoning": "\n".join(state.get("bear_arguments", []))},
            "bull_debate":             {"reasoning": "\n".join(state.get("bull_arguments", []))},
            "key_metrics":             state.get("key_metrics", {}),
            "price_data":              state.get("price_data", {}),
            "balance_sheet":           state.get("balance_sheet", {}),
            "company_info":            state.get("company_info", {}),
            "technical_indicators":    state.get("technical_indicators", {}),
            "persona_signals":         persona_signals_dict,
            "macro_data":              state.get("macro_data", {}),
            # Neutral agent uses aggressive + conservative views for balance
            "aggressive_risk_signal":  {
                "signal": state.get("aggressive_signal", "neutral"),
                "reasoning": state.get("aggressive_view", ""),
            },
            "conservative_risk_signal": {
                "signal": state.get("conservative_signal", "neutral"),
                "reasoning": state.get("conservative_view", ""),
            },
        }

        result = await asyncio.to_thread(agent.analyze, state["ticker"], data)

        state[f"{profile}_view"] = result.reasoning       # type: ignore[literal-required]
        state[f"{profile}_signal"] = result.signal        # type: ignore[literal-required]
        state[f"{profile}_confidence"] = result.confidence  # type: ignore[literal-required]
        state[f"{profile}_key_points"] = result.key_points  # type: ignore[literal-required]

        await on_event({
            "type": "agent_complete",
            "agent": f"risk_{profile}",
            "signal": result.signal,
            "confidence": result.confidence,
            "reasoning": result.reasoning[:200] + ("..." if len(result.reasoning) > 200 else ""),
        })

    except Exception as exc:
        logger.warning("Risk agent %s failed: %s", profile, exc)
        fallback = f"{profile_names.get(profile, profile.title())} analysis unavailable: {str(exc)[:200]}"
        state[f"{profile}_view"] = fallback  # type: ignore[literal-required]
        state[f"{profile}_signal"] = "neutral"  # type: ignore[literal-required]
        state[f"{profile}_confidence"] = 50  # type: ignore[literal-required]
        state[f"{profile}_key_points"] = []  # type: ignore[literal-required]


async def _node_portfolio_manager(
    state: AurumState,
    llm_router: LLMRouter,
    on_event: Callable,
) -> FinalResult:
    """Final node — produce the structured FinalResult."""
    await on_event(
        {
            "type": "agent_start",
            "agent": "portfolio_manager",
            "message": "Portfolio manager issuing final verdict...",
        }
    )

    persona_signals_raw = state.get("persona_signals", [])
    signal_objs = [
        PersonaSignalDict(
            agent=s["agent"],
            signal=s["signal"],
            confidence=s["confidence"],
            reasoning=s["reasoning"],
            key_points=s.get("key_points", []),
        )
        for s in persona_signals_raw
    ]

    base_verdict, base_conf = _verdict_from_signals(signal_objs)
    bull_case = "\n".join(state.get("bull_arguments", ["No bull case available."]))
    bear_case = "\n".join(state.get("bear_arguments", ["No bear case available."]))
    risk_parts = []
    if state.get("aggressive_view", "").strip():
        risk_parts.append(f"**Aggressive Risk View**\n{state['aggressive_view']}")
    if state.get("conservative_view", "").strip():
        risk_parts.append(f"**Conservative Risk View**\n{state['conservative_view']}")
    if state.get("neutral_view", "").strip():
        risk_parts.append(f"**Neutral Risk View**\n{state['neutral_view']}")
    risk_agg = "\n\n".join(risk_parts)

    # Ask the LLM for a refined verdict, target price and summary
    messages = [
        {
            "role": "system",
            "content": (
                "You are the Portfolio Manager.  Based on all research, issue the final "
                "investment recommendation.  Respond in this EXACT JSON format:\n"
                '{"verdict": "BUY", "confidence": 75, "target_price": 185.0, '
                '"summary": "One-paragraph executive summary."}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"Ticker: {state['ticker']}\n"
                f"Quantitative verdict: {base_verdict} ({base_conf}% confidence)\n"
                f"Research synthesis:\n{state.get('research_synthesis', '')}\n\n"
                f"Bull case: {bull_case[:400]}\n"
                f"Bear case: {bear_case[:400]}\n\n"
                "Return ONLY the JSON object."
            ),
        },
    ]

    pm_text = await _async_llm_invoke(
        llm_router, messages, task_type="quick", fallback="{}"
    )

    # Parse PM output, fall back to quantitative verdict on parse error
    import json, re as _re

    verdict = base_verdict
    confidence = base_conf
    target_price = None
    summary = state.get("research_synthesis", "")[:500]

    try:
        # Extract JSON from the response (may have surrounding text)
        # BUG-16 fix: non-greedy to avoid overshooting past the JSON object
        json_match = _re.search(r"\{.*?\}", pm_text, _re.DOTALL) or _re.search(r"\{.*\}", pm_text, _re.DOTALL)
        if json_match:
            pm_data = json.loads(json_match.group())
            verdict = pm_data.get("verdict", verdict)
            confidence = int(pm_data.get("confidence", confidence))
            target_price_raw = pm_data.get("target_price")
            if target_price_raw is not None:
                target_price = float(target_price_raw)
            summary = pm_data.get("summary", summary)
    except Exception as exc:
        logger.warning("Could not parse PM JSON response: %s | raw: %s", exc, pm_text[:200])

    # Build key metrics snapshot
    fund = state.get("fundamentals", {})
    tech = state.get("technical_indicators", {})
    key_metrics = {
        "current_price": tech.get("current_price"),
        "pe_ratio": fund.get("pe_ratio"),
        "pb_ratio": fund.get("pb_ratio"),
        "market_cap": fund.get("market_cap"),
        "rsi_14": tech.get("rsi_14"),
        "sma_50": tech.get("sma_50"),
        "sma_200": tech.get("sma_200"),
        "revenue": fund.get("revenue"),
        "eps": fund.get("eps"),
        "beta": fund.get("beta"),
        "sector": fund.get("sector"),
        "industry": fund.get("industry"),
    }

    result = FinalResult(
        verdict=verdict,
        confidence=min(100, max(0, confidence)),
        target_price=target_price,
        summary=summary,
        persona_signals=signal_objs,
        bull_case=bull_case[:5000],
        bear_case=bear_case[:5000],
        risk_assessment=risk_agg[:8000],
        key_metrics=key_metrics,
    )
    result.research_synthesis = state.get("research_synthesis", "")[:6000]
    result.aggressive_risk = state.get("aggressive_view", "")
    result.aggressive_risk_signal = state.get("aggressive_signal", "")
    result.aggressive_risk_confidence = state.get("aggressive_confidence", 0)
    result.aggressive_risk_key_points = state.get("aggressive_key_points", [])
    result.conservative_risk = state.get("conservative_view", "")
    result.conservative_risk_signal = state.get("conservative_signal", "")
    result.conservative_risk_confidence = state.get("conservative_confidence", 0)
    result.conservative_risk_key_points = state.get("conservative_key_points", [])
    result.neutral_risk = state.get("neutral_view", "")
    result.neutral_risk_signal = state.get("neutral_signal", "")
    result.neutral_risk_confidence = state.get("neutral_confidence", 0)
    result.neutral_risk_key_points = state.get("neutral_key_points", [])

    await on_event(
        {
            "type": "agent_complete",
            "agent": "portfolio_manager",
            "signal": verdict,
            "confidence": confidence,
            "reasoning": summary,
        }
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TradingGraph orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class TradingGraph:
    """Orchestrates the full multi-agent stock analysis pipeline.

    Usage::

        graph = TradingGraph()
        result = await graph.run(
            ticker="AAPL",
            date_range={"start": "2024-01-01", "end": "2025-01-01"},
            personas=["buffett", "burry"],
            llm_router=router,
            on_event=callback,
        )
    """

    async def run(
        self,
        ticker: str,
        date_range: dict,
        personas: list[str],
        llm_router: LLMRouter,
        on_event: Callable[..., Coroutine],
        analysis_mode: str = "current",
    ) -> FinalResult:
        """Execute the full pipeline and return a ``FinalResult``.

        Args:
            ticker: Stock ticker symbol.
            date_range: Dict with keys ``start`` and ``end`` (YYYY-MM-DD strings).
            personas: List of persona IDs to include.
            llm_router: Configured ``LLMRouter`` instance.
            on_event: Async callable ``(event_dict) -> None`` for streaming.
            analysis_mode: ``"current"`` (latest fundamentals) or
                ``"historical"`` (financials from the annual filing closest
                to ``date_range["end"]``).

        Returns:
            ``FinalResult`` with verdict, confidence, target price, and supporting
            analysis.
        """
        valid_personas = [
            p for p in personas if p in PERSONA_REGISTRY
        ]
        if not valid_personas:
            valid_personas = DEFAULT_PERSONAS

        state: AurumState = {
            "ticker": ticker.upper(),
            "start_date": date_range.get("start", "2024-01-01"),
            "end_date": date_range.get("end", "2025-01-01"),
            "personas": valid_personas,
            "persona_signals": [],
            "analysis_mode": analysis_mode,
        }

        # ── 1. Entry: data fetch (price history) ─────────────────────────────
        await _node_data_fetch(state, on_event)

        # ── 2. Parallel data collection ───────────────────────────────────────
        # All four nodes run concurrently; each uses asyncio.to_thread internally
        # so blocking HTTP calls don't stall the event loop.
        await asyncio.gather(
            _node_fundamentals(state, on_event),
            _node_technical(state, on_event),
            _node_news(state, on_event),
            _node_macro(state, on_event),
        )

        # ── 3. Rate-throttled persona analysis ───────────────────────────────
        # Semaphore(1) forces personas to run fully sequentially — one at a time.
        # This prevents burst exhaustion of all free-tier providers simultaneously.
        # Each persona also gets its own 90-second graceful timeout: if a single
        # persona hangs (slow provider, rate-limit retry storm), it emits a neutral
        # fallback signal and the pipeline continues — no total analysis failure.
        _persona_sem = asyncio.Semaphore(1)

        async def _throttled_persona(pid: str) -> PersonaSignalDict:
            async with _persona_sem:
                persona_name = PERSONA_INFO.get(pid, {}).get("name", pid.replace("_", " ").title())
                try:
                    result = await asyncio.wait_for(
                        _node_persona(pid, state, llm_router, on_event),
                        timeout=90.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning("Persona %s timed out after 90s — using neutral fallback", pid)
                    await on_event({
                        "type": "agent_result",
                        "agent": pid,
                        "agent_name": persona_name,
                        "signal": "neutral",
                        "confidence": 50,
                        "reasoning": (
                            f"{persona_name} analysis timed out (provider took >90s). "
                            "No signal available for this persona."
                        ),
                    })
                    result = PersonaSignalDict(
                        agent=pid,
                        signal="neutral",
                        confidence=50,
                        reasoning=(
                            f"{persona_name} analysis timed out — no signal available."
                        ),
                        key_points=[],
                    )
                await asyncio.sleep(0.5)   # brief gap so provider quotas can breathe
                return result

        persona_tasks = [_throttled_persona(pid) for pid in valid_personas]
        persona_results: list[PersonaSignalDict] = await asyncio.gather(*persona_tasks)

        # Store as plain dicts for serialisability across state mutations
        state["persona_signals"] = [
            {
                "agent": p.agent,
                "signal": p.signal,
                "confidence": p.confidence,
                "reasoning": p.reasoning,
                "key_points": p.key_points if isinstance(p.key_points, list) else [],
            }
            for p in persona_results
        ]

        # ── 4. Debate ─────────────────────────────────────────────────────────
        await _node_debate_bull(state, llm_router, on_event)
        await _node_debate_bear(state, llm_router, on_event)

        # ── 5. Research synthesis ─────────────────────────────────────────────
        await _node_research_manager(state, llm_router, on_event)

        # ── 6. Parallel risk views ────────────────────────────────────────────
        await asyncio.gather(
            _node_risk("aggressive", state, llm_router, on_event),
            _node_risk("conservative", state, llm_router, on_event),
            _node_risk("neutral", state, llm_router, on_event),
        )

        # ── 7. Portfolio manager — final verdict ──────────────────────────────
        result = await _node_portfolio_manager(state, llm_router, on_event)

        # ── 8. Emit raw data snapshot for the frontend "Data Sources" panel ──
        # By this point state["fundamentals"] has been enriched in-place by all
        # persona runs (setdefault calls), so it carries CAGRs, PEG, etc.
        try:
            _fund = state.get("fundamentals", {})
            _tech = state.get("technical_indicators", {})
            _bal  = state.get("balance_sheet", {})
            _inc  = state.get("income_statement", {})
            _cf   = state.get("cashflow", {})
            _inst = state.get("institutional_ownership", {})
            _sh   = state.get("shares_history", {})
            _yc   = state.get("yield_curve", {})
            _ar   = state.get("analyst_recommendations", {})

            def _clean(d: dict) -> dict:
                """Strip None/NaN values so the frontend doesn't render empty rows."""
                out = {}
                for k, v in d.items():
                    if v is None or v == "":
                        continue
                    if isinstance(v, float) and (_math.isnan(v) or _math.isinf(v)):
                        continue
                    out[k] = v
                return out

            import math as _math

            def _safe(v: object) -> object:
                """Replace NaN/Inf floats with None so JSON.parse never chokes.

                Python's json.dumps emits the bare token ``NaN`` for float('nan')
                which is not valid JSON — browsers raise SyntaxError on it.
                The WebSocket onmessage handler silently swallows parse errors,
                so the entire data_snapshot event is dropped without any warning.
                """
                if isinstance(v, float) and (_math.isnan(v) or _math.isinf(v)):
                    return None
                return v

            def _sanitize_list(rows: list[dict]) -> list[dict]:
                """Run _safe() over every value in every row dict."""
                return [{k: _safe(val) for k, val in row.items()} for row in rows]

            await on_event({
                "type": "data_snapshot",
                "company": _clean({
                    "Name":        _fund.get("name"),
                    "Sector":      _fund.get("sector"),
                    "Industry":    _fund.get("industry"),
                    "Country":     _fund.get("country"),
                    "Currency":    _fund.get("currency"),
                    "Employees":   _fund.get("employees"),
                    "Description": (_fund.get("description") or "")[:400] or None,
                }),
                "valuation": _clean({
                    "P/E (TTM)":       _fund.get("pe_ratio"),
                    "Forward P/E":     _fund.get("forward_pe"),
                    "P/B":             _fund.get("pb_ratio"),
                    "P/S":             _fund.get("ps_ratio"),
                    "EV/EBITDA":       _fund.get("ev_ebitda"),
                    "PEG Ratio":       _fund.get("peg_ratio"),
                    "FCF Yield":       f"{_fund['fcf_yield']:.1f}%" if _fund.get("fcf_yield") else None,
                    "Earnings Yield":  _fund.get("earnings_yield"),
                    "Market Cap":      _fund.get("market_cap"),
                    "Enterprise Value":_fund.get("enterprise_value"),
                }),
                "profitability": _clean({
                    "Gross Margin":      _fund.get("gross_margin") or _inc.get("gross_margin"),
                    "Operating Margin":  _fund.get("operating_margin") or _inc.get("operating_margin"),
                    "Net Margin":        _fund.get("net_margin") or _inc.get("net_margin"),
                    "ROE":               _fund.get("roe"),
                    "ROA":               _fund.get("roa"),
                    "ROIC":              _fund.get("roic"),
                    "ROIC−WACC Spread":  _fund.get("roic_wacc_spread"),
                }),
                "financials": _clean({
                    "Revenue":           _inc.get("revenue") or _fund.get("revenue"),
                    "Gross Profit":      _inc.get("gross_profit"),
                    "Operating Income":  _inc.get("operating_income"),
                    "Net Income":        _inc.get("net_income") or _fund.get("net_income"),
                    "EBITDA":            _fund.get("ebitda"),
                    "EPS (TTM)":         _fund.get("eps"),
                    "Forward EPS":       _fund.get("forward_eps"),
                    "R&D % Revenue":     _inc.get("rd_pct_revenue"),
                    "Revenue Growth YoY":_fund.get("revenue_growth_yoy"),
                }),
                "balance_sheet": _clean({
                    "Total Assets":         _bal.get("total_assets"),
                    "Total Liabilities":    _bal.get("total_liabilities"),
                    "Stockholders Equity":  _bal.get("stockholders_equity"),
                    "Cash & Equivalents":   _bal.get("cash") or _bal.get("cash_and_equivalents"),
                    "Long-Term Debt":       _bal.get("long_term_debt"),
                    "Current Ratio":        _bal.get("current_ratio"),
                    "Debt / Equity":        _bal.get("debt_equity"),
                    "Net Debt / EBITDA":    _fund.get("net_debt_ebitda"),
                    "Working Capital Δ":    _bal.get("working_capital_change"),
                }),
                "cash_flow": _clean({
                    "Free Cash Flow":    _cf.get("fcf"),
                    "Operating CF":      _cf.get("operating_cf"),
                    "CapEx":             _cf.get("capex"),
                    "FCF Margin":        _cf.get("fcf_margin"),
                    "Cash Burn (net)":   _fund.get("cash_burn"),
                    "CapEx / Revenue":   _fund.get("capex_to_revenue"),
                }),
                "growth": _clean({
                    "Revenue CAGR 3yr":    _fund.get("revenue_cagr_3yr"),
                    "Revenue CAGR 5yr":    _fund.get("revenue_cagr_5yr"),
                    "EPS CAGR 3yr":        _fund.get("eps_cagr_3yr"),
                    "EPS CAGR 5yr":        _fund.get("eps_cagr_5yr"),
                    "Fwd EPS Growth":      _fund.get("forward_eps_growth"),
                    "Net Income Growth YoY": _fund.get("net_income_growth_yoy"),
                    "Shares Change 3yr":   _fund.get("shares_change_3yr") or _sh.get("shares_change_3yr"),
                    "Revenue History":     _fund.get("revenue_history_5yr"),
                    "Net Income History":  _fund.get("net_income_history_5yr"),
                }),
                "technical": _clean({
                    "Current Price":         _tech.get("current_price"),
                    "52-Week High":          _fund.get("52w_high"),
                    "52-Week Low":           _fund.get("52w_low"),
                    "% from 52W High":       _tech.get("pct_from_52w_high"),
                    "RSI (14)":              _tech.get("rsi"),
                    "MACD":                  _tech.get("macd"),
                    "Signal Line":           _tech.get("signal_line"),
                    "SMA 50":                _tech.get("sma_50"),
                    "SMA 200":               _tech.get("sma_200"),
                    "% Above SMA50":         _tech.get("pct_above_sma50"),
                    "% Above SMA200":        _tech.get("pct_above_sma200"),
                    "Trend":                 _tech.get("trend_direction"),
                    "SPY Relative Strength": _tech.get("relative_strength_vs_spy"),
                    "Beta":                  _fund.get("beta"),
                }),
                "market": _clean({
                    "Shares Outstanding":      _fund.get("shares_outstanding"),
                    "Avg Volume (30d)":        _fund.get("avg_volume"),
                    "Dividend Yield":          _fund.get("dividend_yield"),
                    "Annual Dividend":         _fund.get("dividend_rate"),
                    "Short Interest %":        _fund.get("short_interest_pct"),
                    "Short Ratio":             _fund.get("short_ratio"),
                    "Institutional Ownership": _fund.get("institutional_ownership"),
                    "Revenue / Employee":      _fund.get("revenue_per_employee"),
                }),
                "macro": _clean({
                    "2Y Treasury":  _yc.get("2y"),
                    "5Y Treasury":  _yc.get("5y"),
                    "10Y Treasury": _yc.get("10y"),
                    "30Y Treasury": _yc.get("30y"),
                    "Yield Spread (10Y−2Y)": (
                        round(float(_yc["10y"]) - float(_yc["2y"]), 2)
                        if _yc.get("10y") and _yc.get("2y") else None
                    ),
                    "Macro Summary": (state.get("macro_summary") or "")[:600] or None,
                }),
                "analyst_recs": _clean({
                    "Consensus":    _ar.get("consensus"),
                    "Strong Buy":   _ar.get("strong_buy"),
                    "Buy":          _ar.get("buy"),
                    "Hold":         _ar.get("hold"),
                    "Sell":         _ar.get("sell"),
                    "Strong Sell":  _ar.get("strong_sell"),
                    "Total Analysts": _ar.get("total_analysts"),
                    "Price Target": _ar.get("mean_target"),
                }),
                # ── List-type sections ────────────────────────────────────────
                "earnings": _clean({
                    "Next Earnings Date": (
                        state.get("earnings_calendar", {}).get("earnings_date")
                        or state.get("earnings_calendar", {}).get("earnings_dates")
                    ),
                    "EPS Estimate (Avg)":  state.get("earnings_calendar", {}).get("earnings_avg"),
                    "EPS Estimate (Low)":  state.get("earnings_calendar", {}).get("earnings_low"),
                    "EPS Estimate (High)": state.get("earnings_calendar", {}).get("earnings_high"),
                    "Revenue Estimate":    state.get("earnings_calendar", {}).get("revenue_avg"),
                }),
                "news": [
                    {
                        "title":     n.get("title", ""),
                        "date":      n.get("date", ""),
                        "publisher": n.get("publisher", ""),
                    }
                    for n in state.get("news", [])[:10]
                    if n.get("title")
                ],
                "insider_transactions": _sanitize_list([
                    {
                        "name":   t.get("name", ""),
                        "role":   t.get("role", ""),
                        "date":   t.get("date", ""),
                        "type":   t.get("transaction_type", t.get("action", "")),
                        "shares": t.get("shares"),
                        "value":  t.get("value") or t.get("total_value"),
                    }
                    for t in state.get("insider_transactions", [])[:8]
                ]),
                "top_holders": _inst.get("top_holders", []),
                # ── SEC Filings Log ───────────────────────────────────────────
                "sec_filings": [
                    {
                        "form":        f["form"],
                        "filed_date":  f["filed_date"],
                        "report_date": f["report_date"],
                        # Direct link to the EDGAR filing index page
                        "url": (
                            f"https://www.sec.gov/Archives/edgar/data/{f['cik']}"
                            f"/{f['accession_number'].replace('-', '')}/"
                        ) if f.get("cik") and f.get("accession_number") else "",
                    }
                    for f in (state.get("sec_filings", []) + state.get("sec_filings_q", []))
                    if f.get("filed_date")
                ],
                # ── Peer Comparison ───────────────────────────────────────────
                # Main ticker row first (is_subject=True), then sector peers.
                # _sanitize_list() converts any NaN/Inf floats → None so that
                # the browser's JSON.parse() never throws a SyntaxError.
                "peer_comparison": _sanitize_list([
                    {
                        "ticker":         state["ticker"],
                        "name":           _fund.get("name") or state["ticker"],
                        "price":          _tech.get("current_price"),
                        "pe_ratio":       _fund.get("pe_ratio"),
                        "pb_ratio":       _fund.get("pb_ratio"),
                        "ps_ratio":       _fund.get("ps_ratio"),
                        "profit_margin":  _fund.get("net_margin") or _inc.get("net_margin"),
                        "revenue_growth": _fund.get("revenue_growth_yoy"),
                        "market_cap":     _fund.get("market_cap"),
                        "is_subject":     True,
                    },
                    *state.get("peer_comparison", []),
                ]),
            })
        except Exception as _snap_exc:
            logger.warning("data_snapshot emit failed: %s", _snap_exc)

        return result
