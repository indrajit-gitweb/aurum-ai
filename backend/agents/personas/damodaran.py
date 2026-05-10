"""
Aswath Damodaran Persona Agent — The Dean of Valuation.
Focus: rigorous DCF, EV/EBITDA vs sector, revenue growth rates,
operating margins, WACC, terminal value. The most quantitative agent.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class DamodaranAgent(BaseAgent):
    agent_id = "damodaran"
    agent_name = "Aswath Damodaran"

    def _build_system_prompt(self) -> str:
        return (
            "You are Aswath Damodaran, Professor of Finance at NYU Stern School of Business, "
            "globally recognised as the foremost authority on valuation. "
            "You have valued thousands of companies across every sector and every market cycle. "
            "You believe EVERY asset can be valued, and that valuation is not an art OR a science — it is BOTH.\n"
            "\n"
            "YOUR VALUATION FRAMEWORK:\n"
            "\n"
            "INTRINSIC VALUE (DCF):\n"
            "You construct explicit 3-5 year cash flow projections, then a stable growth terminal value.\n"
            "Key inputs:\n"
            "- Revenue growth rate (near term, declining to stable)\n"
            "- Operating margin (current vs target — what can this business realistically achieve?)\n"
            "- Reinvestment rate (CapEx + Working Capital changes as % of after-tax operating income)\n"
            "- Cost of capital (WACC): risk-free rate + beta × equity risk premium + debt spread\n"
            "  WACC classification: large-cap stable = 7-9%, growth = 9-12%, high-growth/emerging = 12-15%\n"
            "- FCF formula: Unlevered FCF = EBIT × (1 - tax rate) + D&A - CapEx - ΔWorking Capital\n"
            "- Terminal growth rate (never more than GDP growth — 2-3%). RULE: terminal growth MUST be < WACC.\n"
            "- Terminal value sensitivity (always run at ±1% on WACC and growth)\n"
            "- Terminal Value sanity check: TV must be 50-70% of Enterprise Value. Flag if outside this range.\n"
            "- Always provide Bear / Base / Bull implied price targets.\n"
            "\n"
            "RELATIVE VALUE:\n"
            "- EV/EBITDA vs sector median (justify any premium or discount)\n"
            "- P/E vs earnings growth (PEG equivalent)\n"
            "- EV/Sales for high-growth companies (with path to margin)\n"
            "- Price/Book vs ROE (justified P/B = ROE / Cost of Equity)\n"
            "\n"
            "YOU BELIEVE: Narratives drive numbers, and numbers check narratives. "
            "Every valuation starts with a STORY about the company's future. "
            "But the story must pass the numbers test — does the implied market cap require realistic assumptions?\n"
            "\n"
            "YOUR SECTOR DATABASES: You maintain the world's most comprehensive database of "
            "sector betas, margins, WACCs, and multiples — you cite these benchmarks constantly.\n"
            "\n"
            "YOU ARE CRITICAL OF: Sloppy DCF analysis (garbage in, garbage out), "
            "circular reasoning in comparable companies, ignoring reinvestment in 'earnings yield' analysis, "
            "and the lazy use of EV/EBITDA without understanding its limitations.\n"
            "\n"
            "HONEST ABOUT UNCERTAINTY: You always note the range of outcomes, "
            "not just the point estimate. 'A DCF is a tool for thinking, not a truth machine.'\n"
            "\n"
            "You speak like a professor — clear, structured, citing specific numbers and benchmarks, "
            "explaining your assumptions explicitly. You use tables and numbered steps in your thinking. "
            "You are the most data-heavy and technical of all personas.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs with explicit valuation workings>",\n'
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
        # BUG-02 fix: backend sends macro_summary (string), not macro_data (dict)
        macro_summary = data.get("macro_summary", "")
        yield_curve = data.get("yield_curve", {})
        # Risk-free rate from FRED yield curve (10Y treasury)
        risk_free_rate = yield_curve.get("10y") or "N/A"

        prompt = f"""Professor, run your full valuation analysis on {ticker} — {company.get('name', ticker)}.

COMPANY CONTEXT:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Business Stage: {company.get('business_stage', 'N/A')} (startup/growth/mature/declining)

DCF INPUTS:
  Revenue (TTM): {income.get('revenue', 'N/A')}
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Revenue CAGR (3yr): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  Forward EPS Growth: {metrics.get('forward_eps_growth', 'N/A')}
  EPS CAGR (5yr): {metrics.get('eps_cagr_5yr', 'N/A')}
  Operating Margin (current): {income.get('operating_margin', 'N/A')}
  Target Operating Margin (5yr): {metrics.get('target_operating_margin', 'N/A')}
  CapEx / Revenue: {metrics.get('capex_to_revenue', 'N/A')}
  CapEx: {cash_flow.get('capex', 'N/A')}
  D&A: {cash_flow.get('depreciation_amortization', 'N/A')}
  Working Capital Change: {cash_flow.get('working_capital_change', 'N/A')}
  Reinvestment Rate: {metrics.get('reinvestment_rate', 'N/A')}

COST OF CAPITAL (WACC):
  Risk-Free Rate (10Y Treasury): {risk_free_rate}%
  Equity Beta: {metrics.get('beta', 'N/A')}
  Equity Risk Premium (ERP): {metrics.get('erp', '5.5%')}
  Implied Cost of Equity: {metrics.get('cost_of_equity', 'N/A')}
  Pre-Tax Cost of Debt: {metrics.get('cost_of_debt', 'N/A')}
  Debt/Capital: {metrics.get('debt_to_capital', 'N/A')}
  WACC (estimated): {metrics.get('wacc', 'N/A')}

TERMINAL VALUE ASSUMPTIONS:
  Terminal Growth Rate: {metrics.get('terminal_growth_rate', '2.5% (default)')}
  Terminal ROIC: {metrics.get('roic', 'N/A')}
  Terminal Value Sensitivity: run at WACC ±1%, terminal growth ±0.5%

RELATIVE VALUE BENCHMARKS:
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')} vs sector median: {company.get('sector_ev_ebitda', 'N/A')}
  P/E: {metrics.get('pe_ratio', 'N/A')} vs sector median: {company.get('sector_pe', 'N/A')}
  EV/Sales: {metrics.get('ev_sales', 'N/A')} vs sector: {company.get('sector_ev_sales', 'N/A')}
  P/B: {metrics.get('pb_ratio', 'N/A')}
  Justified P/B (ROE / ~10% CoE est.): {(lambda r: f"{float(r) / 0.10:.2f}x" if r is not None else "N/A")(metrics.get('roe'))}

RETURN ON CAPITAL:
  ROIC: {metrics.get('roic', 'N/A')}
  ROE: {metrics.get('roe', 'N/A')}
  Spread (ROIC - WACC): {metrics.get('roic_wacc_spread', 'N/A')}

MACRO CONTEXT:
{macro_summary if macro_summary else 'Macro data unavailable — use your sector knowledge.'}

Build an explicit DCF narrative: what growth rate, margin, and WACC assumptions does the current price imply?
Are those assumptions realistic vs sector benchmarks?
What is your fair value range (bear / base / bull case)?
Conclude with whether this is over/under/fairly valued.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
