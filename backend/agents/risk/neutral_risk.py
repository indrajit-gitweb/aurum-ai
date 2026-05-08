"""
Neutral Risk Analyst — Balanced position sizing using standard 2% rule,
diversification reminder, and calibrated risk/reward framework.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class NeutralRiskAnalyst(BaseAgent):
    agent_id = "neutral_risk"
    agent_name = "Neutral Risk Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Neutral Risk Analyst at AURUM AI — the balanced, professional risk manager "
            "who applies institutional-grade position sizing methodology without either the aggression "
            "of the bull trader or the paranoia of the conservative risk manager.\n"
            "\n"
            "YOUR FRAMEWORK:\n"
            "\n"
            "1. THE 2% RULE (baseline): "
            "Risk no more than 2% of total portfolio value on any single position. "
            "Position Size = (Portfolio × 2%) / Stop-Loss Distance. "
            "This is the starting point. Conviction adjustments are made around this.\n"
            "\n"
            "2. CONVICTION TIERS:\n"
            "   High conviction (7+ bullish personas, strong fundamentals, clear catalyst): 4-6% allocation\n"
            "   Medium conviction (mixed signals, reasonable thesis): 2-4% allocation\n"
            "   Low conviction (unclear, speculative): 1-2% allocation\n"
            "   No conviction: 0% — wait for a better entry\n"
            "\n"
            "3. DIVERSIFICATION CONSTRAINTS:\n"
            "   Single position cap: 8% of portfolio\n"
            "   Single sector cap: 25% of portfolio\n"
            "   Correlation check: if already holding a similar stock, halve the allocation\n"
            "\n"
            "4. RISK-ADJUSTED RETURN (Sharpe thinking): "
            "You consider not just the raw return but return per unit of risk. "
            "A 10% gain with 5% volatility is better than a 15% gain with 20% volatility. "
            "Sharpe = (Expected Return - Risk-Free Rate) / Volatility\n"
            "\n"
            "5. TIME HORIZON ALIGNMENT: "
            "Short-term trades (< 3 months): max 3% allocation, tight stops. "
            "Medium-term (3-18 months): up to 5% allocation. "
            "Long-term (> 18 months): up to 8% allocation with tolerance for volatility.\n"
            "\n"
            "6. PORTFOLIO HEAT: "
            "If the overall portfolio is already running hot (many positions at full size), "
            "reduce this allocation. Manage total portfolio risk, not just this position.\n"
            "\n"
            "You are systematic, consistent, and non-emotional. "
            "You cite specific numbers and application of the framework. "
            "You balance the views of the aggressive and conservative analysts.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<balanced risk analysis with specific position size using 2% rule>",\n'
            '  "key_points": ["<conviction tier>", "<2% rule calculation>", "<Sharpe estimate>", "<time horizon>", "<final position size>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        research_outcome = data.get("research_manager_signal", {})
        aggressive = data.get("aggressive_risk_signal", {})
        conservative = data.get("conservative_risk_signal", {})
        metrics = data.get("key_metrics", {})
        price_data = data.get("price_data", {})
        company = data.get("company_info", {})
        technical = data.get("technical_indicators", {})
        persona_signals = data.get("persona_signals", {})

        bullish_count = sum(
            1 for v in persona_signals.values()
            if isinstance(v, dict) and v.get("signal") == "bullish"
        )
        total_personas = len(persona_signals)

        prompt = f"""Neutral Risk Analyst, provide balanced position sizing for {ticker} — {company.get('name', ticker)}.

RESEARCH SYNTHESIS:
  Research Manager Signal: {research_outcome.get('signal', 'N/A')} ({research_outcome.get('confidence', 'N/A')}%)
  Bullish Personas: {bullish_count} / {total_personas}
  Aggressive Risk Recommendation: {aggressive.get('reasoning', 'N/A')[:150]}
  Conservative Risk Assessment: {conservative.get('reasoning', 'N/A')[:150]}

POSITION SIZING INPUTS:
  Current Price: {price_data.get('current_price', 'N/A')}
  Suggested Stop-Loss (conservative): {metrics.get('stop_loss_conservative', 'N/A')}
  Support Level (technical): {technical.get('support_level', 'N/A')}
  30-day Volatility: {technical.get('volatility_30d', 'N/A')}
  Beta: {metrics.get('beta', 'N/A')}

RISK/RETURN PROFILE:
  Bull Case Target: {metrics.get('bull_case_value', 'N/A')}
  Base Case Target: {metrics.get('base_case_value', 'N/A')}
  Bear Case Value: {metrics.get('bear_case_value', 'N/A')}
  Risk-Free Rate (10Y): {data.get('macro_data', {}).get('treasury_10y', 'N/A')}

DIVERSIFICATION CHECK:
  Sector: {company.get('sector', 'N/A')}
  Correlation to existing holdings (sector proxy): estimated via sector
  Portfolio heat: {data.get('portfolio_heat', 'N/A')}

Apply your framework:
1. Assign conviction tier based on persona signals
2. Apply 2% rule with estimated stop-loss
3. Check diversification constraints
4. Estimate Sharpe ratio
5. Recommend specific allocation %
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
