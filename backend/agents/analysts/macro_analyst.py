"""
Macro Analyst — analyses the macroeconomic environment and its specific impact
on the target stock's sector and risk profile.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class MacroAnalyst(BaseAgent):
    agent_id = "macro_analyst"
    agent_name = "Macro Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are a macro strategist with 25 years of experience connecting top-down economic conditions "
            "to bottom-up stock impact. You think in terms of regime: are we in a risk-on or risk-off environment? "
            "Is the Fed tightening or easing? Is the yield curve signalling recession or expansion? "
            "You translate macro conditions into specific sector tailwinds and headwinds. "
            "A rate-sensitive REIT behaves very differently from a commodity producer during inflationary cycles. "
            "A defensive consumer staples company is a different animal in a recession than a high-beta tech stock. "
            "You assess: dollar strength/weakness, credit spreads, commodity prices, global growth trajectory, "
            "and geopolitical risk premiums — all in the context of THIS specific company and sector. "
            "You are forward-looking: where are rates heading, is inflation sticky or transitory, "
            "is consumer spending holding up? "
            "You are NOT a permabear — you call it as the data says. "
            "\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<detailed paragraph>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        # BUG-02/03 fix: backend passes macro_summary as a plain string (from FREDClient),
        # NOT a dict under "macro_data".  Use it directly.
        macro_summary = data.get("macro_summary", "") or data.get("macro_data", "")
        if isinstance(macro_summary, dict):
            # Legacy fallback: if somehow a dict arrives, format it
            macro_summary = "  ".join(f"{k}: {v}" for k, v in macro_summary.items() if v)
        company = data.get("company_info", {}) or data.get("fundamentals", {})

        prompt = f"""Assess how the current macroeconomic environment affects {ticker} ({company.get('sector', 'unknown sector')}).

MACROECONOMIC SNAPSHOT:
{macro_summary if macro_summary else 'Macro data currently unavailable — rely on general knowledge.'}

COMPANY CONTEXT:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Beta: {company.get('beta', 'N/A')}
  Country: {company.get('country', 'N/A')}

Evaluate how the current macro conditions (interest rates, inflation, GDP growth, labour market,
yield curve shape) serve as tailwinds or headwinds specifically for {ticker} and its sector.
Return your analysis as the specified JSON object.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
