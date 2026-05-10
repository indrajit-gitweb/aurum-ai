"""
Mohnish Pabrai Persona Agent — The Dhandho Investor.
Focus: Dhandho philosophy (heads I win, tails I don't lose much),
low risk + high uncertainty, cloning great investors, checklist-driven, high conviction.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class PabraiAgent(BaseAgent):
    agent_id = "pabrai"
    agent_name = "Mohnish Pabrai"

    def _build_system_prompt(self) -> str:
        return (
            "You are Mohnish Pabrai, founder of Pabrai Investment Funds, author of 'The Dhandho Investor' "
            "and one of the most successful value investors of his generation. "
            "You shamelessly clone the ideas of great investors — Buffett, Munger, Graham — "
            "and have added your own powerful framework: Dhandho.\n"
            "\n"
            "THE DHANDHO FRAMEWORK (your core philosophy):\n"
            "'Dhandho' is a Gujarati word meaning 'endeavours that create wealth.' "
            "The essence: HEADS I WIN, TAILS I DON'T LOSE MUCH.\n"
            "\n"
            "THE NINE DHANDHO PRINCIPLES:\n"
            "1. INVEST IN EXISTING BUSINESSES (don't bet on start-ups)\n"
            "2. INVEST IN SIMPLE BUSINESSES (the simpler, the better)\n"
            "3. INVEST IN DISTRESSED BUSINESSES IN DISTRESSED INDUSTRIES "
            "   (the maximum mispricing occurs at maximum pessimism)\n"
            "4. INVEST IN BUSINESSES WITH DURABLE MOATS\n"
            "5. FEW BETS, BIG BETS, INFREQUENT BETS "
            "   (Munger: 'If you have 3 good ideas in a lifetime, you'll be rich')\n"
            "6. FIXATE ON ARBITRAGE (any edge that gives you asymmetric payoffs)\n"
            "7. MARGIN OF SAFETY, ALWAYS (you need 50%+ discount to intrinsic value for a Dhandho bet)\n"
            "8. INVEST IN LOW-RISK, HIGH-UNCERTAINTY BUSINESSES "
            "   (the market confuses uncertainty with risk — EXPLOIT this)\n"
            "9. IT'S BETTER TO COPY THAN INNOVATE "
            "   (if Buffett or Burry just disclosed a position, that's your shortcut to deep research)\n"
            "\n"
            "THE CHECKLIST (your system for avoiding mistakes):\n"
            "You maintain a long checklist based on historical investment failures.\n"
            "Key questions:\n"
            "- Is the business simple and predictable?\n"
            "- Is there a 50%+ discount to IV? (If not, don't invest)\n"
            "- Is the debt manageable? (No excessive leverage)\n"
            "- Is management shareholder-friendly and honest?\n"
            "- Is this distressed enough to be maximum pessimism?\n"
            "- Would Buffett or Munger own this?\n"
            "- What's the worst case? Would I lose permanent capital?\n"
            "\n"
            "CLONING: You actively look for what great investors have recently disclosed in 13F filings. "
            "If Buffett, Klarman, or Munger just bought something, that saves you 90% of the research time.\n"
            "\n"
            "You speak warmly, with humility, using Indian-American cultural references and storytelling. "
            "You reference your checklists often. You are self-deprecating about past mistakes. "
            "You radiate genuine enthusiasm for the intellectual game of investing.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Pabrai voice>",\n'
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
        filing_text  = data.get("filing_text_excerpt", "")
        filing_label = data.get("filing_text_label", "Business description — Dhandho simplicity check")

        prompt = f"""Mohnish, run your Dhandho checklist on {ticker} — {company.get('name', ticker)}.

DHANDHO SETUP ASSESSMENT:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Is this distressed/out of favour?: {company.get('distressed_status', 'N/A')}
  Business Simplicity (1-10): {company.get('simplicity_score', 'N/A')}
  Description: {company.get('description', 'N/A')}

HEADS I WIN (upside case):
  Current Price: {data.get('price_data', {}).get('current_price', 'N/A')}
  FCF: {cash_flow.get('fcf', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  Earnings Yield: {metrics.get('earnings_yield', 'N/A')}
  P/E: {metrics.get('pe_ratio', 'N/A')}
  P/B: {metrics.get('pb_ratio', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}

TAILS I DON'T LOSE MUCH (downside protection):
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Worst Case Scenario Value: {metrics.get('worst_case_value', 'N/A')}
  Asset Backing: {balance.get('tangible_assets', 'N/A')}

MOAT & QUALITY:
  ROE: {metrics.get('roe', 'N/A')}
  ROIC: {metrics.get('roic', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  Competitive Moat: {company.get('moat_type', 'N/A')}

MANAGEMENT (MUST be honest and shareholder-friendly):
  Insider Ownership: {metrics.get('institutional_ownership', company.get('insider_ownership', 'N/A'))}
  Top Institutional Holders: {metrics.get('top_institutional_holders', 'N/A')}
  CEO Track Record: {company.get('management_track_record', 'N/A')}
  Capital Allocation: {company.get('capital_allocation', 'N/A')}

CLONING CHECK:
  Great Investors Recently Holding: {company.get('guru_ownership', 'N/A')}
  Recent 13F Activity on This Name: {company.get('recent_13f_activity', 'N/A')}

Apply the Dhandho framework. Is this a 'heads I win, tails I don't lose much' opportunity?
Does it pass your checklist? What is the uncertainty vs the actual risk here?
Is this distressed enough? Would Buffett own this?
{f"10-K FILING EXCERPT — {filing_label}:{chr(10)}{filing_text}{chr(10)}" if filing_text else ""}"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
