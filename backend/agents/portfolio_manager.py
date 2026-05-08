"""
Portfolio Manager — The final decision maker.
Reads all persona signals, debate outcome, and risk team opinions.
Outputs a comprehensive investment verdict with full context.
"""
import json
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_agent import BaseAgent, AgentSignal
from pydantic import BaseModel
from typing import Optional


class PortfolioDecision(BaseModel):
    ticker: str
    verdict: str          # STRONG BUY / BUY / HOLD / SELL / STRONG SELL
    signal: str           # bullish / bearish / neutral
    confidence: int       # 0-100
    bull_case: str
    bear_case: str
    risk_assessment: str
    suggested_position_size_pct: float  # as % of portfolio
    stop_loss_pct: float                # % below entry
    key_metrics: dict
    executive_summary: str
    investment_horizon: str  # "short" / "medium" / "long"
    key_points: list[str]


class PortfolioManager(BaseAgent):
    agent_id = "portfolio_manager"
    agent_name = "Portfolio Manager"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Portfolio Manager at AURUM AI — the ultimate decision maker who bears full "
            "accountability for investment decisions. You have read everything: every analyst report, "
            "every persona's view, the full bull/bear debate, and the risk team's recommendations. "
            "Now you must render a FINAL VERDICT.\n"
            "\n"
            "YOUR VERDICTS:\n"
            "STRONG BUY: > 8 bullish personas, strong fundamentals, clear catalyst, "
            "margin of safety present. Suggested allocation: 6-10%.\n"
            "BUY: Majority bullish, fundamentals solid, reasonable valuation. "
            "Suggested allocation: 3-6%.\n"
            "HOLD: Mixed signals, thesis intact but no clear near-term catalyst. "
            "Suggested allocation: maintain existing, no new capital deployed.\n"
            "SELL: Deteriorating fundamentals, bear thesis gaining weight, or thesis broken. "
            "Reduce exposure.\n"
            "STRONG SELL: Fundamental deterioration, high debt risk, or competitive collapse. "
            "Exit position.\n"
            "\n"
            "YOUR OUTPUT FORMAT (produce ALL of these in the JSON):\n"
            "1. verdict: STRONG BUY / BUY / HOLD / SELL / STRONG SELL\n"
            "2. signal: bullish / bearish / neutral\n"
            "3. confidence: 0-100\n"
            "4. bull_case: 2-3 sentence summary of why it could work\n"
            "5. bear_case: 2-3 sentence summary of the primary risks\n"
            "6. risk_assessment: 1-2 sentences on the key risk factor to monitor\n"
            "7. suggested_position_size_pct: specific % (e.g., 4.5)\n"
            "8. stop_loss_pct: specific % below entry (e.g., 15.0)\n"
            "9. key_metrics: dict of the 5-7 most important metrics (P/E, FCF yield, growth, etc.)\n"
            "10. executive_summary: one paragraph that a CEO could read in 60 seconds\n"
            "11. investment_horizon: 'short' (< 6mo) / 'medium' (6-18mo) / 'long' (> 18mo)\n"
            "12. key_points: 5 bullet points — the 5 things that matter most\n"
            "\n"
            "YOU ARE DECISIVE. You do not hedge every statement. You make a clear call. "
            "You acknowledge uncertainty but commit to a position. "
            "You write for sophisticated investors who want clarity, not ambiguity.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "verdict": "STRONG BUY" | "BUY" | "HOLD" | "SELL" | "STRONG SELL",\n'
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "bull_case": "<2-3 sentences>",\n'
            '  "bear_case": "<2-3 sentences>",\n'
            '  "risk_assessment": "<1-2 sentences>",\n'
            '  "suggested_position_size_pct": <float>,\n'
            '  "stop_loss_pct": <float>,\n'
            '  "key_metrics": {"pe": "...", "fcf_yield": "...", "ev_ebitda": "...", "growth": "...", "roe": "..."},\n'
            '  "executive_summary": "<one paragraph>",\n'
            '  "investment_horizon": "short" | "medium" | "long",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        """Standard analyze method — returns AgentSignal for compatibility."""
        decision = self.make_decision(ticker, data)
        return AgentSignal(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            signal=decision.signal,
            confidence=decision.confidence,
            reasoning=decision.executive_summary,
            key_points=decision.key_points,
        )

    def make_decision(self, ticker: str, data: dict) -> PortfolioDecision:
        """Full portfolio decision with rich output."""
        persona_signals = data.get("persona_signals", {})
        analyst_reports = data.get("analyst_reports", {})
        bull_debate = data.get("bull_debate", {})
        bear_debate = data.get("bear_debate", {})
        research_manager = data.get("research_manager_signal", {})
        aggressive_risk = data.get("aggressive_risk_signal", {})
        conservative_risk = data.get("conservative_risk_signal", {})
        neutral_risk = data.get("neutral_risk_signal", {})
        metrics = data.get("key_metrics", {})
        price_data = data.get("price_data", {})
        company = data.get("company_info", {})

        # Tally persona signals
        signal_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        persona_summary_lines = []
        for name, sig_data in persona_signals.items():
            if isinstance(sig_data, dict):
                sig = sig_data.get("signal", "neutral")
                conf = sig_data.get("confidence", 50)
                signal_counts[sig] = signal_counts.get(sig, 0) + 1
                persona_summary_lines.append(
                    f"  {name}: {sig} ({conf}%) — {sig_data.get('key_points', [''])[0][:80] if sig_data.get('key_points') else ''}"
                )

        persona_summary = "\n".join(persona_summary_lines) if persona_summary_lines else "  No persona signals available."

        prompt = f"""Portfolio Manager, render your final investment decision for {ticker} — {company.get('name', ticker)}.

COMPANY: {company.get('name', ticker)} | {company.get('sector', 'N/A')} | {company.get('industry', 'N/A')}
CURRENT PRICE: {price_data.get('current_price', 'N/A')}
MARKET CAP: {company.get('market_cap', 'N/A')}

PERSONA SIGNAL TALLY:
  BULLISH: {signal_counts['bullish']} / {sum(signal_counts.values())} personas
  BEARISH: {signal_counts['bearish']} / {sum(signal_counts.values())} personas
  NEUTRAL: {signal_counts['neutral']} / {sum(signal_counts.values())} personas

PERSONA DETAILS:
{persona_summary}

ANALYST REPORTS:
  Fundamentals: {analyst_reports.get('fundamentals_analyst', {}).get('signal', 'N/A')} — {analyst_reports.get('fundamentals_analyst', {}).get('reasoning', 'N/A')[:250]}
  Technical: {analyst_reports.get('technical_analyst', {}).get('signal', 'N/A')} — {analyst_reports.get('technical_analyst', {}).get('reasoning', 'N/A')[:150]}
  News: {analyst_reports.get('news_analyst', {}).get('signal', 'N/A')} — {analyst_reports.get('news_analyst', {}).get('reasoning', 'N/A')[:150]}
  Macro: {analyst_reports.get('macro_analyst', {}).get('signal', 'N/A')} — {analyst_reports.get('macro_analyst', {}).get('reasoning', 'N/A')[:150]}

DEBATE OUTCOME:
  Research Manager: {research_manager.get('signal', 'N/A')} ({research_manager.get('confidence', 'N/A')}%)
  Summary: {research_manager.get('reasoning', 'N/A')[:300]}

RISK TEAM:
  Aggressive: {aggressive_risk.get('reasoning', 'N/A')[:150]}
  Conservative: {conservative_risk.get('reasoning', 'N/A')[:150]}
  Neutral: {neutral_risk.get('reasoning', 'N/A')[:150]}

KEY METRICS:
  P/E: {metrics.get('pe_ratio', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  Revenue Growth: {data.get('income_statement', {}).get('revenue_growth_yoy', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  Debt/Equity: {data.get('balance_sheet', {}).get('debt_equity', 'N/A')}
  12-Month Price Target (consensus): {metrics.get('price_target_12m', 'N/A')}

VALUATION RANGE:
  Bull Case Value: {metrics.get('bull_case_value', 'N/A')}
  Base Case Value: {metrics.get('base_case_value', 'N/A')}
  Bear Case Value: {metrics.get('bear_case_value', 'N/A')}

Render your complete portfolio decision. Be decisive. Commit to a verdict.
Include ALL fields in the JSON: verdict, signal, confidence, bull_case, bear_case,
risk_assessment, suggested_position_size_pct, stop_loss_pct, key_metrics,
executive_summary, investment_horizon, key_points.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_portfolio_response(response, ticker, metrics)

    def _parse_portfolio_response(
        self, response: str, ticker: str, metrics: dict
    ) -> PortfolioDecision:
        """Parse LLM response into PortfolioDecision."""
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response)
        if json_match:
            raw = json_match.group(1)
        else:
            json_match = re.search(r"\{[\s\S]*\}", response)
            raw = json_match.group(0) if json_match else None

        if raw:
            try:
                parsed = json.loads(raw)
                verdict = parsed.get("verdict", "HOLD")
                signal = parsed.get("signal", "neutral").lower()
                if signal not in ("bullish", "bearish", "neutral"):
                    signal = "neutral"

                return PortfolioDecision(
                    ticker=ticker,
                    verdict=verdict,
                    signal=signal,
                    confidence=max(0, min(100, int(parsed.get("confidence", 50)))),
                    bull_case=parsed.get("bull_case", ""),
                    bear_case=parsed.get("bear_case", ""),
                    risk_assessment=parsed.get("risk_assessment", ""),
                    suggested_position_size_pct=float(parsed.get("suggested_position_size_pct", 2.0)),
                    stop_loss_pct=float(parsed.get("stop_loss_pct", 15.0)),
                    key_metrics=parsed.get("key_metrics", {}),
                    executive_summary=parsed.get("executive_summary", response),
                    investment_horizon=parsed.get("investment_horizon", "medium"),
                    key_points=parsed.get("key_points", [])[:5],
                )
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Fallback
        return PortfolioDecision(
            ticker=ticker,
            verdict="HOLD",
            signal="neutral",
            confidence=40,
            bull_case="Unable to parse bull case from response.",
            bear_case="Unable to parse bear case from response.",
            risk_assessment="Unable to parse risk assessment.",
            suggested_position_size_pct=2.0,
            stop_loss_pct=15.0,
            key_metrics={},
            executive_summary=response,
            investment_horizon="medium",
            key_points=["See full reasoning above."],
        )
