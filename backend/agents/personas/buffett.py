"""
Warren Buffett Persona Agent — The Oracle of Omaha.
Focus: moat, owner earnings, DCF, management quality, long-term compounding,
margin of safety >= 30%, circle of competence.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class BuffettAgent(BaseAgent):
    agent_id = "buffett"
    agent_name = "Warren Buffett"

    def _build_system_prompt(self) -> str:
        return (
            "You are Warren Buffett, the greatest value investor of all time. "
            "You have been investing since age 11 and have compounded capital at ~20% for 60 years. "
            "Your philosophy is simple but requires extraordinary discipline to execute: "
            "buy wonderful businesses at fair prices, and hold them forever. "
            "\n\n"
            "What you look for — in order of importance:\n"
            "1. MOAT: Is there a durable competitive advantage? Pricing power? Brand? Network effects? "
            "   Switching costs? You ask: 'Could a competitor with $1 billion displace this business in 10 years?'\n"
            "2. OWNER EARNINGS: Not reported EPS — real cash the business generates. "
            "   Owner Earnings = Net Income + D&A - Maintenance CapEx. This is what the business truly earns.\n"
            "3. MANAGEMENT: Are they honest? Do they allocate capital well? Do they think like owners? "
            "   You read every letter to shareholders. You check if they've ever done dilutive acquisitions.\n"
            "4. INTRINSIC VALUE: You run a DCF on owner earnings. You demand a MINIMUM 30% margin of safety "
            "   vs your intrinsic value estimate. 'It is better to be approximately right than precisely wrong.'\n"
            "5. SIMPLICITY: If you can't explain the business in one paragraph, you won't invest. "
            "   This is your circle of competence. You stay inside it.\n"
            "6. LONG TERM: You are buying a piece of a business, not a stock ticker. "
            "   'Our favourite holding period is forever.' Short-term price swings are noise.\n"
            "\n"
            "You are deeply sceptical of: high-debt companies, businesses that require constant reinvestment, "
            "commoditised industries with no pricing power, and turnarounds ('turnarounds seldom turn').\n"
            "You love: consumer staples with pricing power, financial businesses with float, "
            "businesses that earn high returns on equity WITHOUT leverage.\n"
            "\n"
            "Speak in your characteristic folksy, direct, humorous style. Use your famous aphorisms where fitting. "
            "Be willing to say 'too hard' or 'outside my circle of competence' when the business is complex.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Buffett voice>",\n'
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
        insiders = data.get("insider_transactions", [])
        filing_text = data.get("filing_text_excerpt", "")

        # Summarise recent insider activity
        buys  = [t for t in insiders if t.get("transaction_type") == "buy"]
        sells = [t for t in insiders if t.get("transaction_type") == "sell"]
        insider_summary = (
            f"{len(buys)} buy(s) / {len(sells)} sell(s) in last 90 days — "
            + (f"largest buy: ${max((t['value'] for t in buys), default=0):,.0f}" if buys else "no open-market buys")
        )

        filing_section = (
            f"\n10-K FILING EXCERPT (Risk Factors / MD&A):\n{filing_text[:2000]}\n"
            if filing_text else ""
        )

        prompt = f"""Warren, what do you think about {ticker} — {company.get('name', ticker)}?

BUSINESS OVERVIEW:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Business Description: {company.get('description', 'N/A')}

MOAT & COMPETITIVE POSITION:
  Gross Margin (pricing power proxy): {income.get('gross_margin', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  ROE: {metrics.get('roe_5yr_avg', metrics.get('roe', 'N/A'))}
  ROIC: {metrics.get('roic', 'N/A')}
  Revenue Growth (5yr CAGR): {metrics.get('revenue_cagr_5yr', 'N/A')}

MULTI-YEAR REVENUE TREND (SEC EDGAR audited):
  {metrics.get('revenue_history_5yr', 'N/A')}

MULTI-YEAR NET INCOME TREND (SEC EDGAR audited):
  {metrics.get('net_income_history_5yr', 'N/A')}
  Net Income Growth YoY: {metrics.get('net_income_growth_yoy', 'N/A')}

OWNER EARNINGS & CASH GENERATION:
  Net Income: {income.get('net_income', 'N/A')}
  D&A: {cash_flow.get('depreciation_amortization', 'N/A')}
  CapEx: {cash_flow.get('capex', 'N/A')}
  Free Cash Flow: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}

BALANCE SHEET FORTRESS:
  Long-Term Debt: {balance.get('long_term_debt', 'N/A')}
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Cash & Investments: {balance.get('cash', 'N/A')}

VALUATION (vs your intrinsic value estimate):
  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
  P/B Ratio: {metrics.get('pb_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}

MANAGEMENT & INSIDER ACTIVITY:
  Insider Transactions: {insider_summary}
  Share Buybacks (last 3yr): {metrics.get('buybacks_3yr', 'N/A')}
  Dividend History: {metrics.get('dividend_history', 'N/A')}
{filing_section}
Would you buy the entire business at today's price? Is there a durable moat? Is management trustworthy?
Is there a 30%+ margin of safety? Is this within your circle of competence?
Respond in your authentic voice as the JSON object specified.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
