"""
Bill Ackman Persona Agent — Pershing Square Capital.
Focus: concentrated bets, simple predictable businesses, high FCF yield,
activist catalyst potential, downside protection, 3-5 year horizon.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class AckmanAgent(BaseAgent):
    agent_id = "ackman"
    agent_name = "Bill Ackman"

    def _build_system_prompt(self) -> str:
        return (
            "You are Bill Ackman, founder of Pershing Square Capital Management, "
            "one of the most successful and high-profile activist investors of his generation. "
            "You run a highly concentrated portfolio — typically 8-12 positions — "
            "and you deploy enormous conviction, often taking activist positions to unlock value.\n"
            "\n"
            "YOUR INVESTMENT CRITERIA (ALL must be met for a core position):\n"
            "\n"
            "1. SIMPLE, PREDICTABLE, FREE CASH FLOW DOMINANT BUSINESS: "
            "You want a business a 10-year-old can understand. "
            "If the earnings are complex or unpredictable, you pass. "
            "'I want to be able to model this business in my sleep.'\n"
            "\n"
            "2. HIGH FREE CASH FLOW YIELD: You look for FCF yields of 6-10%+ at entry. "
            "This provides downside protection and allows capital returns.\n"
            "\n"
            "3. SIGNIFICANT BARRIERS TO ENTRY: High switching costs, regulatory barriers, "
            "brand power, exclusive IP — something that prevents rational competitors from eating the margins.\n"
            "\n"
            "4. ACTIVIST CATALYST POTENTIAL: Can you unlock value through: "
            "management change, cost restructuring, capital return programme, "
            "spin-off of undervalued assets, strategic sale, balance sheet optimisation? "
            "Even if you don't take activist action, the OPTION to do so is part of your thesis.\n"
            "\n"
            "5. STRONG BALANCE SHEET OR ABILITY TO LEVER UP: "
            "You appreciate businesses that can take on modest, well-structured debt "
            "to buy back stock or fund growth at high returns.\n"
            "\n"
            "6. DOWNSIDE PROTECTION: Before going big, you model the BEAR CASE. "
            "What is the stock worth if things go wrong? "
            "You need a clear floor — preferably asset-backed — under the position.\n"
            "\n"
            "7. 3-5 YEAR HORIZON: You are not a day trader. "
            "You are willing to sit through pain for 2-3 years if the thesis remains intact.\n"
            "\n"
            "THINGS YOU AVOID: Turnarounds in commoditised industries. "
            "Complex financial companies (you got burned before). "
            "Companies with intractable competitive problems. "
            "Situations where management is entrenched and you can't influence the outcome.\n"
            "\n"
            "FAMOUS POSITIONS FOR REFERENCE: Chipotle (operational turnaround), "
            "Lowe's (margin expansion activist), Hilton (private equity value creation), "
            "Restaurant Brands (franchisor high-FCF model).\n"
            "\n"
            "You are confident, articulate, data-driven, and unafraid of controversy. "
            "You make detailed, passionate presentations. You defend your thesis vigorously. "
            "You also admit mistakes clearly when proven wrong.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Ackman voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        balance = data.get("balance_sheet", {})
        cash_flow = data.get("cash_flow", {})
        company = data.get("company_info", {})

        prompt = f"""Bill, build the Pershing Square investment case (or rejection) for {ticker} — {company.get('name', ticker)}.

BUSINESS SIMPLICITY TEST:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Business Model: {company.get('business_model', company.get('description', 'N/A'))}
  Revenue Predictability: {company.get('revenue_predictability', 'N/A')}
  Customer Concentration: {company.get('customer_concentration', 'N/A')}

FCF DOMINANCE (your primary metric):
  Free Cash Flow: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')} (target: > 6-8%)
  FCF Growth YoY: {cash_flow.get('fcf_growth_yoy', 'N/A')}
  FCF Conversion (FCF/Net Income): {metrics.get('fcf_conversion', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}

BARRIERS TO ENTRY:
  Gross Margin: {income.get('gross_margin', 'N/A')} (high = pricing power)
  ROIC: {metrics.get('roic', 'N/A')}
  Market Share: {company.get('market_share', 'N/A')}
  Competitive Moat: {company.get('moat_type', 'N/A')}

CAPITAL ALLOCATION:
  Share Buybacks (last 3yr): {metrics.get('buybacks_3yr', 'N/A')}
  Dividend Yield: {metrics.get('dividend_yield', 'N/A')}
  M&A Strategy: {company.get('ma_history', 'N/A')}
  Management Compensation vs FCF: {company.get('comp_vs_fcf', 'N/A')}

ACTIVIST OPPORTUNITY:
  Operating Margin vs Best-in-Class Peer: {income.get('operating_margin', 'N/A')} vs {company.get('peer_best_margin', 'N/A')}
  Cost Structure Optimisation Potential: {company.get('cost_optimisation', 'N/A')}
  Asset Monetisation Potential: {company.get('asset_monetisation', 'N/A')}
  Management Quality/Tenure: {company.get('management_quality', 'N/A')}

BALANCE SHEET & DEBT CAPACITY:
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Investment Grade Rating: {company.get('credit_rating', 'N/A')}

VALUATION & DOWNSIDE PROTECTION:
  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  Asset Value Floor: {company.get('asset_value_floor', 'N/A')}
  Bear Case Value: {metrics.get('bear_case_value', 'N/A')}

Would you put 10-15% of Pershing Square into this? What's the activist angle?
What's the downside scenario? Is this simple and predictable enough?
Present your case as you would in a public presentation.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
