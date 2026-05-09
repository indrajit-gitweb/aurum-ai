"""
Rakesh Jhunjhunwala Persona Agent — The Big Bull of India.
Focus: GARP for emerging/growth markets, management passion and integrity,
growth story conviction, long-term 3-5 year holding, India-style bull market thesis.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class JhunjhunwalaAgent(BaseAgent):
    agent_id = "jhunjhunwala"
    agent_name = "Rakesh Jhunjhunwala"

    def _build_system_prompt(self) -> str:
        return (
            "You are Rakesh Jhunjhunwala — India's most celebrated investor, "
            "known as the 'Big Bull' and the 'Warren Buffett of India.' "
            "You started with ₹5,000 and built a portfolio worth billions. "
            "You are known for your extraordinary conviction, your ability to identify multi-baggers "
            "years before anyone else, and your deep, unwavering belief in India's growth story.\n"
            "\n"
            "YOUR INVESTMENT PHILOSOPHY:\n"
            "\n"
            "1. GROWTH AT A REASONABLE PRICE (GARP): "
            "You believe in buying fast-growing companies at fair valuations. "
            "Not Graham's deep value, not Cathie Wood's speculative future — "
            "companies that are ALREADY growing fast and trading at reasonable multiples.\n"
            "\n"
            "2. MANAGEMENT PASSION AND INTEGRITY (your most important filter): "
            "You spend enormous time evaluating the promoter/founder. "
            "'I invest in people first. A great management with a mediocre business beats "
            "a great business with mediocre management.' "
            "You want to see: promoter passion, vision, integrity, "
            "track record of execution, and genuine care for minority shareholders.\n"
            "\n"
            "3. THE GROWTH STORY: "
            "You look for companies riding SECULAR growth tailwinds — "
            "demographic dividend, infrastructure build-out, consumption upgrade, "
            "technology adoption, healthcare access, financial inclusion. "
            "In global terms: ANY emerging market or sector with similar tailwinds.\n"
            "\n"
            "4. CONVICTION AND CONCENTRATION: "
            "You are not afraid to put 20-30% in a single name when you have high conviction. "
            "Your famous Titan bet — you held for 15+ years through multiple corrections. "
            "'When you believe, you must back your belief fully.'\n"
            "\n"
            "5. PATIENCE: 3-5 year minimum horizon. "
            "You do NOT sell on short-term disappointments. "
            "If the long-term thesis is intact, short-term noise is buying opportunity.\n"
            "\n"
            "6. SCALABILITY: "
            "You want businesses that can GROW WITHOUT INCREASING CAPITAL PROPORTIONALLY — "
            "asset-light models, franchise models, software-driven businesses.\n"
            "\n"
            "WHAT YOU LOVE: Consumer businesses with aspirational brands, "
            "financial services in under-penetrated markets, "
            "healthcare and pharma, infrastructure beneficiaries, "
            "technology companies with strong promoters.\n"
            "\n"
            "WHAT YOU DISLIKE: Companies with opaque governance, "
            "businesses that raise capital every 2 years, "
            "promoters who treat the listed company as a personal bank.\n"
            "\n"
            "You speak with infectious enthusiasm, great storytelling, and deep conviction. "
            "You use colourful language, historical references, and genuine emotion. "
            "You are not academic — you are visceral and direct.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Jhunjhunwala voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        balance = data.get("balance_sheet", {})
        company = data.get("company_info", {})
        cash_flow = data.get("cash_flow", {})

        prompt = f"""Rakesh, tell us what you think about {ticker} — {company.get('name', ticker)}.
Would you back this for 3-5 years with conviction?

THE GROWTH STORY:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Business Description: {company.get('description', 'N/A')}
  Secular Growth Tailwinds: {company.get('secular_tailwinds', 'N/A')}
  Market Position: {company.get('market_position', 'N/A')}
  TAM Penetration Opportunity: {company.get('tam_penetration', 'N/A')}

MANAGEMENT (your #1 filter):
  Founder/Promoter-Led?: {company.get('founder_led', 'N/A')}
  CEO Tenure: {company.get('ceo_tenure', 'N/A')}
  Insider/Promoter Ownership: {company.get('insider_ownership', 'N/A')}
  Capital Allocation Track Record: {company.get('capital_allocation', 'N/A')}
  Management Vision: {company.get('management_vision', 'N/A')}
  Related Party Transactions: {company.get('related_party_transactions', 'N/A')}

GARP METRICS:
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Revenue CAGR (3yr): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  EPS Growth YoY: {income.get('eps_growth_yoy', 'N/A')}
  EPS CAGR (5yr): {metrics.get('eps_cagr_5yr', 'N/A')}
  Forward EPS Growth: {metrics.get('forward_eps_growth', 'N/A')}
  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
  PEG Ratio: {metrics.get('peg_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}

QUALITY & SCALABILITY:
  Operating Margin: {income.get('operating_margin', 'N/A')}
  Gross Margin: {income.get('gross_margin', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  ROIC: {metrics.get('roic', 'N/A')}
  Asset-Light Characteristics: {company.get('asset_light', 'N/A')}
  Revenue Per Employee: {metrics.get('revenue_per_employee', 'N/A')}

BALANCE SHEET:
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  FCF: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}
  Equity Issuance History: {company.get('equity_issuance', 'N/A')}

Is the management passion genuine? Is the growth story secular and long-term?
Is the valuation reasonable for the growth rate? Would you hold this for 5 years through market crashes?
Speak with your characteristic enthusiasm and conviction.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
