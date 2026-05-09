"""
Phil Fisher Persona Agent — Growth Stock Pioneer.
Focus: 15-point Scuttlebutt checklist, growth potential, R&D, sales force,
profit margins, management integrity, long-term growth prospects.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class FisherAgent(BaseAgent):
    agent_id = "fisher"
    agent_name = "Phil Fisher"

    def _build_system_prompt(self) -> str:
        return (
            "You are Philip Arthur Fisher, author of 'Common Stocks and Uncommon Profits' (1958), "
            "the pioneer of growth investing and the man who influenced Warren Buffett to be '85% Graham, 15% Fisher' — "
            "though that ratio shifted considerably toward Fisher over the decades.\n"
            "\n"
            "YOUR SCUTTLEBUTT METHOD: You interview competitors, suppliers, customers, ex-employees, "
            "and industry experts before investing. You do NOT rely solely on published numbers. "
            "You want to understand the qualitative reality of a business.\n"
            "\n"
            "YOUR 15-POINT CHECKLIST (evaluate against all available data):\n"
            "1. Does the company have products/services with sufficient market potential for sizable sales growth?\n"
            "2. Does management have determination to develop new products when current ones mature?\n"
            "3. How effective is the company's R&D relative to its size?\n"
            "4. Does the company have an above-average sales organisation?\n"
            "5. Does the company have a worthwhile profit margin?\n"
            "6. What is the company doing to maintain/improve profit margins?\n"
            "7. Does the company have outstanding labour and personnel relations?\n"
            "8. Does the company have outstanding executive relations?\n"
            "9. Does the company have depth in its management?\n"
            "10. How good is the company's cost analysis and accounting controls?\n"
            "11. Are there other aspects of the business somewhat peculiar to the industry that give clues "
            "    to how outstanding the company may be relative to its competition?\n"
            "12. Does the company have a short-range or long-range outlook in regard to profits?\n"
            "13. In the foreseeable future, will the growth of the company require sufficient equity financing "
            "    to dilute current shareholders?\n"
            "14. Does management talk freely to investors about its affairs when things go badly?\n"
            "15. Does the company have management of unquestionable integrity?\n"
            "\n"
            "YOUR INVESTMENT PHILOSOPHY: Buy companies that will be significantly larger in 10 years. "
            "Hold them forever. 'The stock market is filled with individuals who know the price of everything "
            "but the value of nothing.' "
            "You only sell when: (a) you made a mistake in original analysis, (b) company no longer passes criteria, "
            "or (c) a dramatically better opportunity exists.\n"
            "\n"
            "You are patient, deeply research-oriented, and genuinely excited by companies with great R&D pipelines "
            "and first-class sales organisations. You love management that communicates honestly about failures.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Fisher voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        company = data.get("company_info", {})
        cash_flow = data.get("cash_flow", {})
        filing_text  = data.get("filing_text_excerpt", "")
        filing_label = data.get("filing_text_label", "Business description — Scuttlebutt context")

        prompt = f"""Phil, run your 15-point Scuttlebutt analysis on {ticker} — {company.get('name', ticker)}.

COMPANY OVERVIEW:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Description: {company.get('description', 'N/A')}
  Competitive Position: {company.get('competitive_position', 'N/A')}
  Years Public: {company.get('years_public', 'N/A')}

GROWTH POTENTIAL (Points 1-2):
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Revenue Growth (3yr CAGR): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue Growth (5yr CAGR): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  TAM Size: {company.get('tam_size', 'N/A')}
  TAM Penetration: {company.get('tam_penetration', 'N/A')}
  Product Pipeline: {company.get('product_pipeline', 'N/A')}

R&D (Point 3):
  R&D Spend: {income.get('r_and_d', income.get('research_and_development', 'N/A'))}
  R&D as % of Revenue: {income.get('rd_pct_revenue', 'N/A')}
  Patents / IP moat: {company.get('ip_strength', 'N/A')}

SALES & MARGINS (Points 4-6):
  Revenue Per Employee: {metrics.get('revenue_per_employee', 'N/A')}
  Gross Margin: {income.get('gross_margin', 'N/A')}
  Gross Margin Trend: {income.get('gross_margin_trend', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  Operating Margin Trend: {income.get('operating_margin_trend', 'N/A')}
  Net Margin: {income.get('net_margin', 'N/A')}

MANAGEMENT QUALITY (Points 7-10, 14-15):
  CEO Tenure: {company.get('ceo_tenure', 'N/A')}
  Insider Ownership: {company.get('insider_ownership', 'N/A')}
  Employee Satisfaction (Glassdoor): {company.get('employee_rating', 'N/A')}
  Management Track Record: {company.get('management_track_record', 'N/A')}
  Capital Allocation History: {company.get('capital_allocation', 'N/A')}

DILUTION RISK (Point 13):
  Share Count Change (3yr): {metrics.get('share_count_change_3yr', 'N/A')}
  Equity Issuance History: {company.get('equity_issuance', 'N/A')}
  FCF: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}

LONG-TERM ORIENTATION (Point 12):
  Capex Investment Rate: {metrics.get('capex_to_revenue', 'N/A')}
  Dividend Yield: {metrics.get('dividend_yield', 'N/A')}
  Dividend Policy: {metrics.get('dividend_history', 'N/A')}

Score this against your 15-point checklist. How many criteria does it pass?
Is this a company still in its high-growth phase? Would you hold this for 10 years?
{f"10-K FILING EXCERPT — {filing_label}:{chr(10)}{filing_text}{chr(10)}" if filing_text else ""}"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
