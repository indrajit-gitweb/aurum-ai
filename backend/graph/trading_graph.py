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
from agents import PERSONA_REGISTRY, PERSONA_INFO, DEBATE_REGISTRY

# Import main's Pydantic models (avoid circular — import lazily inside methods)
# We re-define lightweight dataclasses here to keep the graph self-contained.
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

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

    # Data layer
    price_history: Any          # pd.DataFrame
    fundamentals: dict
    balance_sheet: dict
    income_statement: dict
    cashflow: dict
    news: list[dict]
    technical_indicators: dict
    sec_facts: dict
    sec_filings: list[dict]
    macro_summary: str
    yield_curve: dict

    # Persona analysis
    persona_signals: list[dict]  # list of PersonaSignalDict

    # Debate
    bull_arguments: list[str]
    bear_arguments: list[str]
    research_synthesis: str

    # Risk
    aggressive_view: str
    conservative_view: str
    neutral_view: str

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

    # Run all four yfinance fundamental calls concurrently in thread pool
    fundamentals, balance_sheet, income_statement, cashflow = await asyncio.gather(
        asyncio.to_thread(yf.get_fundamentals),
        asyncio.to_thread(yf.get_balance_sheet),
        asyncio.to_thread(yf.get_income_statement),
        asyncio.to_thread(yf.get_cashflow),
    )
    state["fundamentals"] = fundamentals
    state["balance_sheet"] = balance_sheet
    state["income_statement"] = income_statement
    state["cashflow"] = cashflow

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
    except Exception as exc:
        logger.warning("SEC EDGAR fetch failed: %s", exc)
        state["sec_facts"] = {}
        state["sec_filings"] = []

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
            "message": f"Fetching latest news for {state['ticker']}...",
        }
    )
    yf = YFinanceClient(state["ticker"])
    state["news"] = await asyncio.to_thread(functools.partial(yf.get_news, limit=10))
    await on_event(
        {
            "type": "agent_complete",
            "agent": "news_analyst",
            "signal": "neutral",
            "confidence": 100,
            "reasoning": f"Retrieved {len(state.get('news', []))} news articles.",
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
            cf_enriched = {
                **cf,
                "fcf_margin": (
                    round(fcf / rev, 4) if fcf and rev and rev != 0 else None
                ),
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

            fund_enriched = {
                **fund,
                "wacc":            round(wacc, 4) if wacc is not None else None,
                "cost_of_equity":  round(cost_of_equity, 4) if wacc is not None else None,
                "erp":             "5.5%",
                "roic_wacc_spread": roic_wacc_spread,
                # Alias for balance sheet agent access
                "bvps":            fund.get("bvps"),
            }

            data = {
                "fundamentals": fund_enriched,
                "balance_sheet": state.get("balance_sheet", {}),
                "income_statement": inc_enriched,
                "cashflow": cf_enriched,
                "technical_indicators": tech,
                "news": state.get("news", []),
                "macro_summary": state.get("macro_summary", ""),
                "sec_facts": state.get("sec_facts", {}),
                "price_data": price_data,
                "yield_curve": yield_curve,
                # Field aliases various agents use
                "key_metrics": fund_enriched,      # BUG-08 fix (was technical_indicators)
                "cash_flow": cf_enriched,          # alias for fundamentals_analyst
                "company_info": fund_enriched,     # alias for macro_analyst
            }
            # Run the synchronous analyze() in a thread pool
            result = await asyncio.to_thread(agent.analyze, state["ticker"], data)
            signal = result.signal
            confidence = result.confidence
            reasoning = result.reasoning
        except Exception as exc:
            logger.warning("Persona %s failed: %s", persona_id, exc)
            signal, confidence, reasoning = "neutral", 50, str(exc)

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
            # Fall back to simple inline synthesis
            signals_summary = "\n".join(
                f"- {s['agent'].title()}: {s['signal'].upper()} ({s['confidence']}%)"
                for s in state.get("persona_signals", [])
            )
            bull = "\n".join(state.get("bull_arguments", []))
            bear = "\n".join(state.get("bear_arguments", []))
            messages = [
                {"role": "system", "content": (
                    "You are the Head of Research. Synthesise the analyst signals and debate "
                    "into a clear investment recommendation (2-3 paragraphs). "
                    "Note bull/bear case score and your recommended conviction level."
                )},
                {"role": "user", "content": (
                    f"Analyst Signals:\n{signals_summary}\n\n"
                    f"Bull Case:\n{bull[:500]}\n\nBear Case:\n{bear[:500]}"
                )},
            ]
            synthesis = await _async_llm_invoke(llm_router, messages, task_type="deep")

    state["research_synthesis"] = synthesis

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
    """Run a risk-profile-specific view (aggressive / conservative / neutral)."""
    profile_prompts = {
        "aggressive": (
            "You manage a high-conviction, concentrated portfolio.  "
            "Assess position sizing for an aggressive growth investor.  "
            "Focus on upside and acceptable drawdown."
        ),
        "conservative": (
            "You manage a capital-preservation mandate.  "
            "Assess downside risk, dividend safety, and balance-sheet strength.  "
            "Highlight tail risks."
        ),
        "neutral": (
            "You manage a balanced 60/40 portfolio.  "
            "Assess risk/reward relative to market beta and portfolio fit."
        ),
    }

    await on_event(
        {
            "type": "agent_start",
            "agent": f"risk_{profile}",
            "message": f"{profile.title()} risk manager evaluating position...",
        }
    )

    messages = [
        {"role": "system", "content": profile_prompts[profile]},
        {
            "role": "user",
            "content": (
                f"Given the research synthesis below, provide a {profile} risk assessment "
                f"for {state['ticker']} in 2–3 sentences:\n\n"
                f"{state.get('research_synthesis', 'See analyst signals.')}"
            ),
        },
    ]

    view = await _async_llm_invoke(llm_router, messages, task_type="quick")
    state[f"{profile}_view"] = view  # type: ignore[literal-required]

    await on_event(
        {
            "type": "agent_progress",
            "agent": f"risk_{profile}",
            "message": view[:200],
        }
    )


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
        )
        for s in persona_signals_raw
    ]

    base_verdict, base_conf = _verdict_from_signals(signal_objs)
    bull_case = "\n".join(state.get("bull_arguments", ["No bull case available."]))
    bear_case = "\n".join(state.get("bear_arguments", ["No bear case available."]))
    risk_agg = " | ".join(
        filter(
            None,
            [
                state.get("aggressive_view", ""),
                state.get("conservative_view", ""),
                state.get("neutral_view", ""),
            ],
        )
    )

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
        bull_case=bull_case[:2000],
        bear_case=bear_case[:2000],
        risk_assessment=risk_agg[:1000],
        key_metrics=key_metrics,
    )

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
    ) -> FinalResult:
        """Execute the full pipeline and return a ``FinalResult``.

        Args:
            ticker: Stock ticker symbol.
            date_range: Dict with keys ``start`` and ``end`` (YYYY-MM-DD strings).
            personas: List of persona IDs to include.
            llm_router: Configured ``LLMRouter`` instance.
            on_event: Async callable ``(event_dict) -> None`` for streaming.

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

        # ── 3. Parallel persona analysis ──────────────────────────────────────
        # Each persona runs its LLM call in a thread pool concurrently.
        persona_tasks = [
            _node_persona(pid, state, llm_router, on_event)
            for pid in valid_personas
        ]
        persona_results: list[PersonaSignalDict] = await asyncio.gather(*persona_tasks)

        # Store as plain dicts for serialisability across state mutations
        state["persona_signals"] = [
            {
                "agent": p.agent,
                "signal": p.signal,
                "confidence": p.confidence,
                "reasoning": p.reasoning,
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
        return result
