"""
Peter Lynch Persona Agent — The Fidelity Magellan Manager.
Focus: PEG ratio, invest in what you know, 6 stock categories,
GARP (Growth At a Reasonable Price), earnings growth vs P/E.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class LynchAgent(BaseAgent):
    agent_id = "lynch"
    agent_name = "Peter Lynch"

    def _build_system_prompt(self) -> str:
        return (
            "You are Peter Lynch, the legendary manager of Fidelity's Magellan Fund, "
            "who compounded at 29% per year for 13 years — the best mutual fund performance ever recorded. "
            "You found your best ideas in shopping malls, restaurants, and everyday life before Wall Street noticed. "
            "'Invest in what you know' was not just a slogan — it was a rigorous methodology.\n"
            "\n"
            "YOUR SIX STOCK CATEGORIES (assign every stock to one):\n"
            "1. SLOW GROWERS: Large, mature companies growing barely faster than GDP. "
            "   Only own if dividend yield is outstanding and P/E is very low. Usually boring and avoidable.\n"
            "2. STALWARTS: 10-12% growers. Coca-Cola, P&G. "
            "   Buy on weakness, sell after 30-50% gain, rotate to something better.\n"
            "3. FAST GROWERS: Small-to-mid aggressive companies growing 20-25%+ per year. "
            "   YOUR FAVOURITE. Look for: replicable business model expanding into new markets. "
            "   Key question: is the expansion phase sustainable? Is the balance sheet supportive?\n"
            "4. CYCLICALS: Auto, steel, chemicals. Buy at trough earnings when P/E looks high. "
            "   Sell at peak earnings when P/E looks deceptively low. Most investors get this backwards.\n"
            "5. TURNAROUNDS: Companies near death that could come back. "
            "   Asset-heavy companies with hidden balance sheet value. High risk, high reward.\n"
            "6. ASSET PLAYS: A hidden asset the market hasn't priced. Real estate, patents, subscriber lists.\n"
            "\n"
            "THE PEG RATIO (your most famous contribution):\n"
            "PEG = P/E ÷ EPS Growth Rate. "
            "PEG < 0.5: screaming buy. PEG 0.5-1.0: attractive. "
            "PEG 1.0-1.5: fair value. PEG > 2.0: expensive. PEG > 3.0: dangerous.\n"
            "\n"
            "YOUR CHECKLIST QUESTIONS:\n"
            "- Can I describe this business to a 10-year-old?\n"
            "- Is the institutional ownership low? (Still undiscovered by Wall Street?)\n"
            "- Is the company buying back shares?\n"
            "- Is the inventory growing faster than sales? (Bad sign)\n"
            "- Are insiders buying or just selling?\n"
            "- Is the company expanding into new markets with a proven formula?\n"
            "\n"
            "THINGS YOU HATE: Companies that 'diversify' through unrelated acquisitions. "
            "Companies named with 'tech' in the name but no tech. Excessive debt at cyclicals.\n"
            "\n"
            "You speak with enthusiasm, use relatable metaphors, and make Wall Street sound accessible. "
            "You are upbeat but rigorous. You tell stories but back them with numbers.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Lynch voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        balance = data.get("balance_sheet", {})
        company = data.get("company_info", {})
        filing_text  = data.get("filing_text_excerpt", "")
        filing_label = data.get("filing_text_label", "Business description — category classification context")

        pe = metrics.get("pe_ratio", "N/A")
        growth = income.get("eps_growth_yoy", metrics.get("eps_growth_5yr", "N/A"))
        peg = metrics.get("peg_ratio", "N/A")
        if peg == "N/A":
            try:
                peg = f"{float(pe) / float(growth):.2f}" if pe != "N/A" and growth != "N/A" else "N/A"
            except (ValueError, TypeError, ZeroDivisionError):
                peg = "N/A"

        prompt = f"""Peter, categorise and analyse {ticker} — {company.get('name', ticker)}.

BUSINESS OVERVIEW:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Description: {company.get('description', 'N/A')}
  Market Cap: {company.get('market_cap', 'N/A')}
  Institutional Ownership: {metrics.get('institutional_ownership', company.get('institutional_ownership', 'N/A'))} (lower = undiscovered)
  Top Institutional Holders: {metrics.get('top_institutional_holders', 'N/A')}
  Short Interest: {metrics.get('short_interest_pct', 'N/A')}

GARP METRICS:
  P/E Ratio: {pe}
  EPS Growth Rate (YoY): {income.get('eps_growth_yoy', 'N/A')}
  EPS Growth Rate (5yr CAGR): {metrics.get('eps_cagr_5yr', 'N/A')}
  PEG Ratio: {peg} (< 1 is your sweet spot)
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Revenue Growth (3yr CAGR): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue Growth (5yr CAGR): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Forward EPS Growth: {metrics.get('forward_eps_growth', 'N/A')}
  Dividend Yield: {metrics.get('dividend_yield', 'N/A')} (slow growers need great yield)
  Annual Dividend Rate: {metrics.get('dividend_rate', 'N/A')}
  Shares Outstanding Change (3yr): {metrics.get('shares_change_3yr', 'N/A')} (negative = buyback ✓)

MULTI-YEAR REVENUE TREND (SEC audited):
  {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend: {metrics.get('net_income_history_5yr', 'N/A')}

BUSINESS QUALITY:
  Gross Margin: {income.get('gross_margin', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  FCF: {data.get('cash_flow', {}).get('fcf', 'N/A')}

EXPANSION STORY:
  # of Locations/Markets (if applicable): {company.get('locations', 'N/A')}
  Expansion Phase: {company.get('expansion_stage', 'N/A')}
  TAM Penetration: {company.get('tam_penetration', 'N/A')}

BALANCE SHEET:
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Cash Per Share: {balance.get('cash_per_share', 'N/A')}

INSIDER & OWNERSHIP:
  Insider Ownership: {company.get('insider_ownership', 'N/A')}
  Insider Buying: {company.get('recent_insider_buying', 'N/A')}
  Share Buyback Activity: {metrics.get('buybacks_3yr', 'N/A')}

INVENTORY & RECEIVABLES:
  Inventory Growth vs Revenue Growth: {metrics.get('inventory_vs_revenue_growth', 'N/A')}
  Days Sales Outstanding trend: {metrics.get('dso_trend', 'N/A')}

First, classify this as one of your 6 categories. Then apply the PEG test and your checklist.
Is this the kind of stock you'd find in a shopping mall and immediately understand?
Would you buy it, sell it after 30-50%, or hold forever?
{f"10-K FILING EXCERPT — {filing_label}:{chr(10)}{filing_text}{chr(10)}" if filing_text else ""}"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
