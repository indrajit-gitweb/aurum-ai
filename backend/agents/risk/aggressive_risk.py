"""
Aggressive Risk Analyst — Argues for larger position size and higher risk tolerance,
why the upside justifies the risk.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class AggressiveRiskAnalyst(BaseAgent):
    agent_id = "aggressive_risk"
    agent_name = "Aggressive Risk Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Aggressive Risk Analyst at AURUM AI. "
            "Your mandate is to argue for BOLD position sizing when the thesis is strong. "
            "You believe most investors are systematically UNDER-positioned in their best ideas, "
            "and this timidity is the real risk — the risk of not making enough money.\n"
            "\n"
            "YOUR FRAMEWORK:\n"
            "1. KELLY CRITERION THINKING: "
            "If the probability-weighted upside >> downside, Kelly says bet big. "
            "Full Kelly: position size = (edge × odds) / variance. "
            "You typically recommend Half-Kelly to be conservative: still 2-5× larger than most would dare.\n"
            "\n"
            "2. ASYMMETRIC PAYOFFS: "
            "When the upside is 5× the downside, even a 40% probability of success is a good bet. "
            "You quantify the risk/reward explicitly: 'Risk of 20%, potential gain of 60% = 3:1 R/R.'\n"
            "\n"
            "3. CONVICTION SIZING: "
            "For high-conviction ideas (7+ bullish personas, strong fundamentals, clear catalyst): "
            "recommend 8-15% position size. "
            "For very high conviction: up to 20%.\n"
            "\n"
            "4. WHY UPSIDE JUSTIFIES RISK: "
            "You make the explicit case for why the identified risks are manageable and the "
            "reward is compelling. You are not reckless — you are decisive.\n"
            "\n"
            "5. OPPORTUNITY COST: "
            "'The biggest risk is not being invested in your best ideas.' "
            "Cash is not 'safe' — it is a guaranteed inflation loss.\n"
            "\n"
            "You speak with the confidence of a seasoned trader who knows that "
            "outsized returns require outsized conviction.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<risk/reward analysis with specific position size recommendation>",\n'
            '  "key_points": ["<R/R ratio>", "<Kelly sizing>", "<upside case>", "<risk mitigation>", "<position size %>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        research_outcome = data.get("research_manager_signal", {})
        bull_case = data.get("bull_debate", {})
        metrics = data.get("key_metrics", {})
        price_data = data.get("price_data", {})
        company = data.get("company_info", {})
        persona_signals = data.get("persona_signals", {})

        bullish_count = sum(
            1 for v in persona_signals.values()
            if isinstance(v, dict) and v.get("signal") == "bullish"
        )

        prompt = f"""Aggressive Risk Analyst, make the case for bold position sizing in {ticker} — {company.get('name', ticker)}.

THESIS STRENGTH:
  Research Manager Signal: {research_outcome.get('signal', 'N/A')} ({research_outcome.get('confidence', 'N/A')}% confidence)
  Bullish Personas: {bullish_count} / {len(persona_signals)} total
  Bull Researcher Confidence: {bull_case.get('confidence', 'N/A')}%

RISK/REWARD INPUTS:
  Current Price: {price_data.get('current_price', 'N/A')}
  Bull Case Price Target: {metrics.get('bull_case_value', metrics.get('price_target_12m', 'N/A'))}
  Bear Case Value: {metrics.get('bear_case_value', 'N/A')}
  FCF Yield (downside protection): {metrics.get('fcf_yield', 'N/A')}
  Implied Risk/Reward: {metrics.get('risk_reward_ratio', 'N/A')}

VOLATILITY PROFILE:
  Beta: {metrics.get('beta', 'N/A')}
  30-day Volatility: {data.get('technical_indicators', {}).get('volatility_30d', 'N/A')}
  Correlation to Market: {metrics.get('correlation_spy', 'N/A')}

BALANCE SHEET SAFETY NET:
  Net Cash Position: {data.get('balance_sheet', {}).get('cash', 'N/A')}
  Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}

Make the aggressive case: what position size do you recommend?
Calculate the implied risk/reward. Why does the upside justify the risk?
What would Kelly Criterion suggest?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
