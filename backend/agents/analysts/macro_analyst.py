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
        macro = data.get("macro_data", {})
        company = data.get("company_info", {})

        prompt = f"""Assess how the current macroeconomic environment affects {ticker} ({company.get('sector', 'unknown sector')}).

MACROECONOMIC CONDITIONS:
  Fed Funds Rate: {macro.get('fed_funds_rate', 'N/A')}
  Fed Rate Direction: {macro.get('fed_rate_direction', 'N/A')}
  10Y Treasury Yield: {macro.get('treasury_10y', 'N/A')}
  2Y Treasury Yield: {macro.get('treasury_2y', 'N/A')}
  Yield Curve (10Y-2Y spread): {macro.get('yield_curve_spread', 'N/A')}
  CPI Inflation (YoY): {macro.get('cpi_yoy', 'N/A')}
  Core PCE: {macro.get('core_pce', 'N/A')}
  GDP Growth (latest quarter): {macro.get('gdp_growth', 'N/A')}
  Unemployment Rate: {macro.get('unemployment_rate', 'N/A')}
  Consumer Confidence: {macro.get('consumer_confidence', 'N/A')}
  ISM Manufacturing PMI: {macro.get('ism_manufacturing', 'N/A')}
  ISM Services PMI: {macro.get('ism_services', 'N/A')}
  Credit Spreads (HY): {macro.get('hy_spread', 'N/A')}
  USD Index (DXY): {macro.get('dxy', 'N/A')}
  VIX (Fear Index): {macro.get('vix', 'N/A')}

COMPANY CONTEXT:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Revenue Geography: {company.get('revenue_geography', 'N/A')}
  Interest Rate Sensitivity: {company.get('rate_sensitivity', 'N/A')}
  Cyclicality: {company.get('cyclicality', 'N/A')}

Evaluate how these macro conditions serve as tailwinds or headwinds for {ticker}.
Return your analysis as the specified JSON object.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
