"""
Fundamentals Analyst — analyses company fundamentals including income statement,
balance sheet, cash flow, and key valuation metrics.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class FundamentalsAnalyst(BaseAgent):
    agent_id = "fundamentals_analyst"
    agent_name = "Fundamentals Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are a senior fundamental equity analyst at a top-tier investment bank. "
            "Your job is to dissect a company's financial statements with forensic precision. "
            "You focus on the QUALITY of earnings (accruals, working capital changes, cash conversion), "
            "balance sheet strength (leverage ratios, interest coverage, liquidity), "
            "and whether the market price reflects intrinsic value. "
            "You apply conservative DCF analysis, scrutinise free cash flow conversion, "
            "and compare valuation multiples against sector peers and historical ranges. "
            "You are sceptical of non-GAAP adjustments and management spin. "
            "You reward businesses that compound capital efficiently at high ROE/ROIC with low reinvestment needs. "
            "Red flags: deteriorating margins, rising debt, negative FCF, aggressive revenue recognition. "
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
        income = data.get("income_statement", {})
        balance = data.get("balance_sheet", {})
        cash_flow = data.get("cash_flow", {})
        metrics = data.get("key_metrics", {})

        prompt = f"""Perform a comprehensive fundamental analysis of {ticker}.

INCOME STATEMENT:
  Revenue: {income.get('revenue', 'N/A')}
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Gross Margin: {income.get('gross_margin', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  Net Margin: {income.get('net_margin', 'N/A')}
  EPS (diluted): {income.get('eps_diluted', 'N/A')}
  EPS Growth YoY: {income.get('eps_growth_yoy', 'N/A')}

BALANCE SHEET:
  Total Assets: {balance.get('total_assets', 'N/A')}
  Total Debt: {balance.get('total_debt', 'N/A')}
  Cash & Equivalents: {balance.get('cash', 'N/A')}
  Book Value Per Share: {balance.get('bvps', 'N/A')}
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Current Ratio: {balance.get('current_ratio', 'N/A')}

CASH FLOW:
  Operating Cash Flow: {cash_flow.get('operating_cf', 'N/A')}
  Free Cash Flow: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}
  CapEx: {cash_flow.get('capex', 'N/A')}

KEY METRICS:
  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
  P/B Ratio: {metrics.get('pb_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  ROIC: {metrics.get('roic', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}

Evaluate quality of earnings, balance sheet strength, and valuation vs intrinsic value.
Return your analysis as the specified JSON object.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
