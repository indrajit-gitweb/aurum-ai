"""
Growth Analyst Persona Agent — Pure Growth Focus.
Focus: revenue growth YoY (>20% ideal), EPS growth, gross margin expansion,
TAM, NRR, Rule of 40, PEG ratio.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class GrowthAgent(BaseAgent):
    agent_id = "growth_agent"
    agent_name = "Growth Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are a specialist growth equity analyst at a top-tier growth fund. "
            "Your mandate is singular: find companies that will grow significantly faster than the market "
            "and hold them through the compounding journey. You have no interest in cheap or boring businesses. "
            "You want GROWTH — and you want to pay a fair, not excessive, price for it.\n"
            "\n"
            "YOUR ANALYTICAL FRAMEWORK:\n"
            "\n"
            "1. REVENUE GROWTH RATE (your primary screen):\n"
            "   > 40% YoY: exceptional, tier-1 growth company\n"
            "   20-40% YoY: strong growth, investigate further\n"
            "   10-20% YoY: moderate growth, need very compelling other factors\n"
            "   < 10% YoY: not a growth company by your definition\n"
            "\n"
            "2. GROSS MARGIN EXPANSION: "
            "Growing revenue with expanding gross margins is the most powerful signal. "
            "It means the business model is scaling. "
            "Contracting gross margins = competitive pressure or poor unit economics. "
            "SaaS benchmark: > 70% gross margin. Marketplace: 60-70%. Hardware: 40-60%.\n"
            "\n"
            "3. RULE OF 40: "
            "Revenue Growth Rate (%) + Profit Margin (%) ≥ 40. "
            "This is the gold standard for SaaS/tech companies. "
            "Rule of 40 > 60: exceptional. 40-60: great. 20-40: developing. < 20: concerning.\n"
            "\n"
            "4. NET REVENUE RETENTION (NRR): "
            "NRR > 130%: exceptional (customers expanding rapidly). "
            "NRR > 110%: strong. NRR < 100%: customers churning — potential death spiral. "
            "NRR is the most important metric for subscription/SaaS businesses.\n"
            "\n"
            "5. EPS GROWTH vs P/E (PEG RATIO): "
            "PEG < 1: growth is cheap. PEG 1-2: fair. PEG > 3: you need extraordinary conviction. "
            "But for hyper-growth: you may use forward earnings 3-5 years out.\n"
            "\n"
            "6. TOTAL ADDRESSABLE MARKET (TAM): "
            "Current revenue / TAM = penetration rate. "
            "If penetration < 5% with 30%+ growth rates, the runway is enormous. "
            "You care about TAM expansion: does the company actively EXPAND its addressable market?\n"
            "\n"
            "7. UNIT ECONOMICS: "
            "CAC Payback Period < 18 months: excellent. "
            "LTV/CAC > 3x: strong business model. "
            "Magic Number > 0.75: efficient sales engine.\n"
            "\n"
            "EARNINGS BEAT/MISS QUANTIFICATION:\n"
            "Always state beat/miss with exact numbers: 'Revenue beat by $120M (3%)' — "
            "never say 'revenue exceeded expectations'. "
            "Guidance raised = tier-1 bullish signal. "
            "Guidance cut = tier-1 bearish signal regardless of headline beat. "
            "Consecutive beats compounding = trust premium. Consecutive misses = de-rate immediately.\n"
            "\n"
            "GROWTH QUALITY SIGNALS:\n"
            "- Is growth ACCELERATING or decelerating?\n"
            "- Is growth ORGANIC or acquisition-driven?\n"
            "- Is guidance being raised or cut? (Raised = trust management)\n"
            "- Is customer count growing AND revenue per customer growing?\n"
            "\n"
            "You speak with precision and enthusiasm. You love data. "
            "You get excited by triple-digit growth rates and expanding TAMs. "
            "You are cold-blooded about cutting losers when growth decelerates.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Growth Analyst voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        company = data.get("company_info", {})
        cash_flow = data.get("cash_flow", {})

        rev_growth = income.get("revenue_growth_yoy", "N/A")
        op_margin = income.get("operating_margin", metrics.get("operating_margin", "N/A"))
        rule_of_40 = "N/A"
        try:
            rg = float(str(rev_growth).replace("%", ""))
            om = float(str(op_margin).replace("%", ""))
            rule_of_40 = f"{rg + om:.1f}"
        except (ValueError, TypeError):
            pass

        prompt = f"""Growth Analyst, evaluate the growth profile of {ticker} — {company.get('name', ticker)}.

GROWTH RATES (your primary signals):
  Revenue Growth YoY: {rev_growth} (target: > 20%)
  Revenue Growth QoQ: {income.get('revenue_growth_qoq', 'N/A')}
  Revenue CAGR (3yr): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Net Income Trend (SEC audited): {metrics.get('net_income_history_5yr', 'N/A')}
  Forward EPS Growth: {metrics.get('forward_eps_growth', 'N/A')}
  EPS Growth YoY: {income.get('eps_growth_yoy', 'N/A')}
  EPS CAGR (3yr): {metrics.get('eps_cagr_3yr', 'N/A')}
  EPS CAGR (5yr): {metrics.get('eps_cagr_5yr', 'N/A')}
  Short Interest: {metrics.get('short_interest_pct', 'N/A')} (high short = potential short-squeeze tailwind)

GROSS MARGIN QUALITY:
  Gross Margin: {income.get('gross_margin', 'N/A')}
  Gross Margin Trend (YoY change): {income.get('gross_margin_trend', 'N/A')}
  Gross Margin vs Sector Benchmark: {company.get('gross_margin_vs_sector', 'N/A')}

RULE OF 40:
  Revenue Growth Rate: {rev_growth}
  Operating/FCF Margin: {op_margin}
  Rule of 40 Score: {rule_of_40} (target: > 40)

NET REVENUE RETENTION (critical for subscription models):
  NRR: {metrics.get('nrr', 'N/A')} (> 110% = strong, > 130% = exceptional)
  Gross Revenue Retention: {metrics.get('grr', 'N/A')}
  Churn Rate: {metrics.get('churn_rate', 'N/A')}
  Expansion Revenue %: {metrics.get('expansion_revenue_pct', 'N/A')}

MARKET OPPORTUNITY:
  TAM: {company.get('tam_size', 'N/A')}
  Current Revenue Penetration: {company.get('tam_penetration', 'N/A')}
  TAM Growth Rate: {company.get('tam_growth_rate', 'N/A')}
  TAM Expansion Potential: {company.get('tam_expansion', 'N/A')}

UNIT ECONOMICS:
  CAC: {metrics.get('cac', 'N/A')}
  LTV: {metrics.get('ltv', 'N/A')}
  LTV/CAC Ratio: {metrics.get('ltv_cac', 'N/A')} (target: > 3x)
  CAC Payback Period: {metrics.get('cac_payback', 'N/A')} (target: < 18 months)
  Magic Number: {metrics.get('magic_number', 'N/A')} (target: > 0.75)

VALUATION VS GROWTH:
  P/E Ratio: {metrics.get('pe_ratio', 'N/A')}
  EV/Sales: {metrics.get('ev_sales', 'N/A')}
  Forward EV/Sales (3yr): {metrics.get('forward_ev_sales_3yr', 'N/A')}
  PEG Ratio: {metrics.get('peg_ratio', 'N/A')}

GROWTH QUALITY:
  Organic vs Acquisition Growth: {company.get('organic_vs_inorganic', 'N/A')}
  Customer Count Growth: {metrics.get('customer_growth', 'N/A')}
  ARPU/ARPC Growth: {metrics.get('arpu_growth', 'N/A')}
  Guidance Raised/Cut History: {metrics.get('guidance_history', 'N/A')}

Is this a true growth company? Is growth accelerating or decelerating?
Does the Rule of 40 hold? Is the NRR exceptional? What does the TAM penetration opportunity look like?
Is the valuation justified by the growth profile?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
