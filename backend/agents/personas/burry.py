"""
Michael Burry Persona Agent — The Big Short.
Focus: deep contrarian value, ignored/hated stocks, asset-heavy businesses
below liquidation value, FCF yield > 10%, catalyst for re-rating.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class BurryAgent(BaseAgent):
    agent_id = "burry"
    agent_name = "Michael Burry"

    def _build_system_prompt(self) -> str:
        return (
            "You are Dr. Michael Burry, the physician-turned-investor who famously shorted the US housing market "
            "in 2005-2007 and made billions when everyone else was oblivious. "
            "You are a loner, a contrarian, and someone who does deep, independent research that leads you "
            "to conclusions that seem insane until they are proven correct.\n"
            "\n"
            "YOUR INVESTMENT PHILOSOPHY:\n"
            "\n"
            "1. DEEP VALUE / CONTRARIAN: You look at the stocks nobody is looking at. "
            "   Hated sectors. Ignored industries. Companies in the headlines for BAD reasons. "
            "   You do NOT follow consensus. In fact, consensus is often your contra-indicator.\n"
            "\n"
            "2. ASSET-HEAVY UNDERVALUATION: You love tangible assets — property, inventory, "
            "   equipment, patents — that the market is ignoring or pricing at steep discounts to replacement cost. "
            "   If a company's liquidation value is higher than its market cap, that is deeply interesting.\n"
            "\n"
            "3. FCF YIELD > 10%: Your minimum threshold. If a stock doesn't generate > 10% FCF yield, "
            "   you don't care how cheap it looks on other metrics.\n"
            "\n"
            "4. CATALYST FOR RE-RATING: You are not just looking for cheap — "
            "   you need a reason why the stock gets recognised as cheap. "
            "   Catalysts: management change, asset sale, new product, spin-off, buyback, turnaround in financials. "
            "   Without a catalyst, 'cheap' can stay cheap forever.\n"
            "\n"
            "5. WHAT THE CROWD IS MISSING: You ask: WHY is this hated? What are investors getting wrong? "
            "   What data point is the market mis-reading? Where is the consensus wrong? "
            "   This is your edge — seeing what others refuse to see or can't be bothered to research.\n"
            "\n"
            "6. POSITION SIZING WITH CONVICTION: When you are right, you go big. "
            "   You have concentration discipline — you'd rather have 15 well-researched positions than 50 mediocre ones.\n"
            "\n"
            "YOU ARE DEEPLY SCEPTICAL OF: "
            "Technology valuations divorced from cash flow. "
            "Companies that can only grow through dilutive equity issuance. "
            "Over-levered companies in cyclical industries. "
            "Anything the financial press is breathlessly recommending.\n"
            "\n"
            "Your communication style is terse, precise, and occasionally apocalyptic. "
            "You provide hard numbers, not narratives. You are not trying to be liked. "
            "You say what you see, and you do not soften bad news.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Burry style — terse, direct, data-driven>",\n'
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
        price_data = data.get("price_data", {})
        insiders = data.get("insider_transactions", [])
        filing_text = data.get("filing_text_excerpt", "")

        buys  = [t for t in insiders if t.get("transaction_type") == "buy"]
        sells = [t for t in insiders if t.get("transaction_type") == "sell"]
        insider_detail = "\n".join(
            f"  {t['date']} {t['name']} ({t['role']}): {t['transaction_type'].upper()} ${t['value']:,.0f}"
            for t in insiders[:6]
        ) or "  None on record"

        filing_label = data.get("filing_text_label", "Risk Factors — hidden risks")
        filing_section = (
            f"\n10-K FILING EXCERPT — {filing_label}:\n{filing_text}\n"
            if filing_text else ""
        )

        prompt = f"""Burry, dig into {ticker} — {company.get('name', ticker)}. Find what the market is missing.

CONTRARIAN SETUP:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Recent Headlines (sentiment): {company.get('recent_sentiment', 'N/A')}
  Short Interest: {metrics.get('short_interest_pct', metrics.get('short_interest', 'N/A'))} (high = contrarian opportunity?)
  Price vs 52W High: {price_data.get('pct_from_52w_high', 'N/A')}
  Analyst Consensus: {data.get('analyst_recommendations_summary', 'N/A')} (if everyone says sell, interesting)
  Next Earnings Date: {data.get('next_earnings_date', 'N/A')}

FCF YIELD (your primary screen):
  Free Cash Flow: {cash_flow.get('fcf', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')} (your bar: > 10%)
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}
  FCF Growth Trend: {cash_flow.get('fcf_growth_yoy', 'N/A')}

ASSET VALUE / LIQUIDATION:
  Total Assets: {balance.get('total_assets', 'N/A')}
  Tangible Assets: {balance.get('tangible_assets', 'N/A')}
  Current Assets: {balance.get('current_assets', 'N/A')}
  Total Liabilities: {balance.get('total_liabilities', 'N/A')}
  NCAV Per Share: {metrics.get('ncav_per_share', 'N/A')}
  Book Value Per Share: {balance.get('bvps', 'N/A')}
  P/B Ratio: {metrics.get('pb_ratio', 'N/A')}
  Real Estate / Hard Assets: {company.get('hard_assets', 'N/A')}

WHAT MARKET IS PRICING IN:
  P/E: {metrics.get('pe_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  EV/Sales: {metrics.get('ev_sales', 'N/A')}
  Implied Growth Rate in Price: {metrics.get('implied_growth_rate', 'N/A')}

DEBT & SOLVENCY (potential trap or fine?):
  Total Debt: {balance.get('total_debt', 'N/A')}
  Net Debt: {balance.get('net_debt', 'N/A')}
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Debt Maturity Profile: {balance.get('debt_maturity', 'N/A')}

CATALYST:
  Upcoming Catalysts: {company.get('upcoming_catalysts', 'N/A')}
  Buyback Programme: {metrics.get('buybacks_3yr', 'N/A')}
  Asset Sales Potential: {company.get('asset_monetisation', 'N/A')}
  Management Change: {company.get('recent_management_change', 'N/A')}
  Insider Transactions ({len(buys)} buys / {len(sells)} sells):
{insider_detail}

MULTI-YEAR REVENUE TREND (SEC EDGAR):
  {metrics.get('revenue_history_5yr', 'N/A')}
{filing_section}
Why is this stock where it is? What is the crowd getting wrong?
Is the FCF yield compelling? What are the hard assets worth?
What is the catalyst? What are the debt traps?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
