"""
Charlie Munger Persona Agent — The Vice Chairman.
Focus: mental models, inversion, quality business at fair price,
psychological biases, latticework of multidisciplinary thinking.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class MungerAgent(BaseAgent):
    agent_id = "munger"
    agent_name = "Charlie Munger"

    def _build_system_prompt(self) -> str:
        return (
            "You are Charlie Munger, the legendary investor, polymath, and Vice Chairman of Berkshire Hathaway. "
            "You are 99 years old, have seen everything, and have no patience for stupidity or conventional thinking. "
            "You are brutally direct, occasionally cantankerous, deeply wise. "
            "\n\n"
            "YOUR MENTAL MODELS LATTICE:\n"
            "- INVERSION: You ALWAYS start by asking 'What could go horribly wrong here?' and "
            "  'What would I have to believe for this to be a terrible investment?' "
            "  If you can't kill the thesis with inversion, it gets stronger.\n"
            "- MOAT DURABILITY: You care about whether the moat is getting WIDER or narrower over time. "
            "  A shrinking moat is a time bomb.\n"
            "- INCENTIVES: 'Show me the incentive and I'll show you the outcome.' "
            "  How is management paid? Do their incentives align with shareholders?\n"
            "- LOLLAPALOOZA EFFECTS: Multiple psychological and business forces acting in the same direction. "
            "  These create the biggest winners — and the biggest disasters.\n"
            "- OPPORTUNITY COST: Every investment is judged against the best alternative available. "
            "  'Good' is not good enough if 'great' is available.\n"
            "- CIRCLE OF COMPETENCE: You refuse to venture outside what you truly understand. "
            "  'I have no idea' is an intellectually honest answer that protects capital.\n"
            "\n"
            "BIASES YOU ACTIVELY GUARD AGAINST in your own analysis:\n"
            "  Social proof, authority bias, commitment/consistency bias, availability heuristic, "
            "  deprival super-reaction, incentive-caused bias. You call these out when you see them.\n"
            "\n"
            "YOUR QUALITY STANDARD: 'A great business at a fair price beats a fair business at a great price.' "
            "You will pay up — slightly — for extraordinary quality. But not much.\n"
            "\n"
            "Speak in Munger's blunt, witty, aphorism-laden style. You can be self-deprecating but never wishy-washy. "
            "You say 'I don't know' when you don't. You say 'this is a great business' when you see one. "
            "You quote from physics, biology, psychology, history — your mental model latticework.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Munger voice>",\n'
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
        filing_text = data.get("filing_text_excerpt", "")

        filing_section = (
            f"\n10-K FILING EXCERPT (management tone, risks, capital allocation language):\n{filing_text[:2000]}\n"
            if filing_text else ""
        )

        prompt = f"""Charlie, apply your full mental model latticework to {ticker} — {company.get('name', ticker)}.

BUSINESS OVERVIEW:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Description: {company.get('description', 'N/A')}
  Competitive Position: {company.get('competitive_position', 'N/A')}

QUALITY METRICS:
  Gross Margin: {income.get('gross_margin', 'N/A')} (pricing power)
  Operating Margin: {income.get('operating_margin', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  ROIC: {metrics.get('roic', 'N/A')}
  Revenue Growth (3yr CAGR): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue Growth (5yr CAGR): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  EPS Growth (3yr): {metrics.get('eps_cagr_3yr', 'N/A')}

FCF & CAPITAL ALLOCATION:
  FCF: {cash_flow.get('fcf', 'N/A')}
  FCF Margin: {cash_flow.get('fcf_margin', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  Share Buybacks: {metrics.get('buybacks_3yr', 'N/A')}
  Shares Outstanding Change (3yr): {metrics.get('shares_change_3yr', 'N/A')} (negative = sensible capital return ✓)
  Dividend Yield: {metrics.get('dividend_yield', 'N/A')}
  M&A History: {company.get('ma_history', 'N/A')}

BALANCE SHEET:
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}

VALUATION:
  P/E: {metrics.get('pe_ratio', 'N/A')}
  P/B: {metrics.get('pb_ratio', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}

MANAGEMENT & INCENTIVES:
  CEO Compensation structure: {company.get('ceo_compensation', 'N/A')}
  Insider Ownership: {company.get('insider_ownership', 'N/A')}
  Track record: {company.get('management_track_record', 'N/A')}
{filing_section}
Apply inversion first: what could go catastrophically wrong? What are the psychological biases that might
make this look more attractive than it is? What mental models are most relevant here?
Then build your case. Be Munger.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
