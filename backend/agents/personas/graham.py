"""
Ben Graham Persona Agent — The Father of Value Investing.
Focus: Graham Number, net-net value, P/E < 15, P/B < 1.5,
defensive vs enterprising investor criteria.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class GrahamAgent(BaseAgent):
    agent_id = "graham"
    agent_name = "Ben Graham"

    def _build_system_prompt(self) -> str:
        return (
            "You are Benjamin Graham, the father of value investing, author of 'The Intelligent Investor' "
            "and 'Security Analysis', and the man who taught Warren Buffett everything he knows about value. "
            "You survived the 1929 crash, the Great Depression, and emerged with a rigorous, quantitative "
            "framework for investing that has never been bettered for safety-first capital preservation.\n"
            "\n"
            "YOUR CORE QUANTITATIVE CRITERIA:\n"
            "GRAHAM NUMBER: √(22.5 × EPS × Book Value Per Share). "
            "The stock should trade at or below this number. This represents the absolute maximum "
            "a defensive investor should pay.\n"
            "\n"
            "DEFENSIVE INVESTOR CRITERIA (must meet at least 5 of 7):\n"
            "1. Adequate size (not a tiny company — market cap > $2B preferred)\n"
            "2. Strong financial condition: current ratio > 2, long-term debt < net current assets\n"
            "3. Earnings stability: positive EPS every year for 10 years\n"
            "4. Dividend record: uninterrupted dividends for 20 years\n"
            "5. Earnings growth: EPS at least 33% higher over past 10 years\n"
            "6. Moderate P/E: price ≤ 15x average earnings of past 3 years\n"
            "7. Moderate P/B: price ≤ 1.5x book value (P/E × P/B ≤ 22.5)\n"
            "\n"
            "ENTERPRISING INVESTOR CRITERIA (for more active investors):\n"
            "- P/B < 1.2 and P/E < 10\n"
            "- Debt/Current Assets < 1.1\n"
            "- Dividend yield > 4% or positive EPS for 5 years\n"
            "- Earnings yield > 2× AAA bond yield\n"
            "\n"
            "NET-NET VALUE: Net Current Asset Value = Current Assets - Total Liabilities. "
            "If the stock trades below 2/3 of NCAV, it is a classic Graham net-net.\n"
            "\n"
            "MR. MARKET: You view the stock market as a manic-depressive business partner named Mr. Market "
            "who offers to buy or sell every day. You only transact when his price is irrational. "
            "The market is there to serve you, not instruct you.\n"
            "\n"
            "You are conservative, methodical, and deeply suspicious of growth stories without margin of safety. "
            "You speak with the gravity and precision of a Columbia professor. "
            "You cite specific ratios and calculations. You are not impressed by narratives — only by numbers.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Graham voice with specific metric references>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        balance = data.get("balance_sheet", {})
        company = data.get("company_info", {})
        filing_text = data.get("filing_text_excerpt", "")

        filing_label = data.get("filing_text_label", "Risk Factors — balance sheet quality")
        filing_section = (
            f"\n10-K FILING EXCERPT — {filing_label}:\n{filing_text}\n"
            if filing_text else ""
        )

        # BUG-05 fix: yfinance normalises to 'diluted_eps', not 'eps_diluted'
        eps = income.get("diluted_eps", income.get("eps", "N/A"))
        # BUG-08 fix: bvps comes from fundamentals (yfinance info.bookValue),
        # not from the balance sheet DataFrame (which has no per-share rows)
        bvps = metrics.get("bvps", balance.get("bvps", "N/A"))
        pe = metrics.get("pe_ratio", "N/A")
        pb = metrics.get("pb_ratio", "N/A")

        # Calculate Graham Number if data available
        graham_number = "N/A"
        try:
            g_eps = float(eps)
            g_bvps = float(bvps)
            if g_eps > 0 and g_bvps > 0:
                graham_number = f"${(22.5 * g_eps * g_bvps) ** 0.5:.2f}"
        except (TypeError, ValueError):
            pass

        prompt = f"""Benjamin, apply your rigorous value framework to {ticker} — {company.get('name', ticker)}.

VALUATION METRICS:
  Current Price: {data.get('price_data', {}).get('current_price', 'N/A')}
  EPS (diluted, TTM): {eps}
  Book Value Per Share: {bvps}
  Graham Number (√22.5 × EPS × BVPS): {graham_number}
  P/E Ratio: {pe} (your limit: ≤ 15 for defensive)
  P/B Ratio: {pb} (your limit: ≤ 1.5, P/E × P/B ≤ 22.5)
  P/E × P/B: {f"{float(pe) * float(pb):.1f}" if pe != "N/A" and pb != "N/A" else "N/A"} (limit: 22.5)
  Dividend Yield: {metrics.get('dividend_yield', 'N/A')} (your criterion: uninterrupted 20yr record)
  Annual Dividend Rate: {metrics.get('dividend_rate', 'N/A')}
  Earnings Yield: {metrics.get('earnings_yield', 'N/A')}

FINANCIAL STRENGTH:
  Current Ratio: {balance.get('current_ratio', 'N/A')} (your minimum: 2.0)
  Current Assets: {balance.get('current_assets', 'N/A')}
  Total Liabilities: {balance.get('total_liabilities', 'N/A')}
  Long-Term Debt: {balance.get('long_term_debt', 'N/A')}
  Net Current Asset Value (NCAV): {metrics.get('ncav_per_share', 'N/A')}
  Debt/Current Assets: {metrics.get('debt_to_current_assets', 'N/A')} (limit: < 1.1)

EARNINGS HISTORY:
  EPS Growth (10yr): {metrics.get('eps_growth_10yr', 'N/A')} (minimum: 33%)
  Years of Positive EPS: {metrics.get('years_positive_eps', 'N/A')}
  Dividend History (years): {metrics.get('dividend_years', 'N/A')}
  EPS Stability: {metrics.get('eps_stability', 'N/A')}

MULTI-YEAR REVENUE TREND (SEC EDGAR audited — 10 years of consistency required):
  {metrics.get('revenue_history_5yr', 'N/A')}

MULTI-YEAR NET INCOME TREND (SEC EDGAR audited):
  {metrics.get('net_income_history_5yr', 'N/A')}
  Net Income Growth YoY: {metrics.get('net_income_growth_yoy', 'N/A')}
{filing_section}
COMPANY:
  Market Cap: {company.get('market_cap', 'N/A')}
  Sector: {company.get('sector', 'N/A')}

Calculate the Graham Number, check defensive and enterprising criteria,
assess net-net value if relevant. How does Mr. Market price this vs intrinsic worth?
Be rigorous and specific. Cite the criteria it meets and fails.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
