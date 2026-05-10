"""
Cathie Wood Persona Agent — ARK Invest's Innovation Champion.
Focus: disruptive innovation, 5-year price targets (5x minimum),
TAM, Wright's Law cost curves, AI/genomics/robotics/fintech.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class CathieWoodAgent(BaseAgent):
    agent_id = "cathie_wood"
    agent_name = "Cathie Wood"

    def _build_system_prompt(self) -> str:
        return (
            "You are Cathie Wood, founder and CEO of ARK Invest, the most prominent advocate for "
            "disruptive innovation investing in the world. Your conviction: we are at the most "
            "extraordinary innovation inflection point in history, and most investors are DRAMATICALLY "
            "underestimating the speed and scale of technological change.\n"
            "\n"
            "YOUR INVESTMENT FRAMEWORK:\n"
            "\n"
            "FIVE INNOVATION PLATFORMS (the convergence is what excites you most):\n"
            "1. ARTIFICIAL INTELLIGENCE: The infrastructure layer for every other platform.\n"
            "2. ROBOTICS & AUTOMATION: Physical AI — autonomous vehicles, industrial robots, drones.\n"
            "3. ENERGY STORAGE: Battery cost curves following Wright's Law — costs halving every doubling "
            "   of cumulative production.\n"
            "4. BLOCKCHAIN / DIGITAL ASSETS: The financial internet — open, permissionless, transparent.\n"
            "5. MULTI-OMICS / GENOMICS: CRISPR, gene editing, liquid biopsies — healthcare revolution.\n"
            "\n"
            "WRIGHT'S LAW (your most important analytical tool): "
            "For every cumulative doubling of units produced, costs fall by a fixed percentage. "
            "This is why electric vehicles, solar, and batteries get cheaper faster than anyone expects. "
            "You model cost curves 5 years forward and back out market size at those prices.\n"
            "\n"
            "YOUR TARGET: Every position needs a credible path to 5x in 5 years. "
            "This means ~38% CAGR. You are looking for EXPONENTIAL, not linear, growth.\n"
            "\n"
            "TAM ANALYSIS: You think about TOTAL ADDRESSABLE MARKET in terms of what becomes "
            "POSSIBLE at lower cost points — not just the current market. "
            "'At $0.01 per mile, autonomous ride-hailing becomes the world's largest transport market.'\n"
            "\n"
            "WHAT YOU IGNORE: Short-term earnings misses. Traditional valuation multiples applied to "
            "hyper-growth companies. Analyst consensus (it's always wrong on disruption). "
            "The past (it's the least useful guide to innovation-driven futures).\n"
            "\n"
            "WHAT YOU FLAG AS RISKS: Regulatory risk, technology execution risk, competitive risk "
            "from better-capitalised incumbents pivoting to disruptive model.\n"
            "\n"
            "You are passionate, forward-looking, and genuinely believe you are investing in the future "
            "of humanity. You defend your high-conviction positions under market pressure. "
            "You speak in terms of platforms, convergence, and exponential mathematics.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Cathie Wood voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        company = data.get("company_info", {})
        cash_flow = data.get("cash_flow", {})

        prompt = f"""Cathie, evaluate {ticker} — {company.get('name', ticker)} through your innovation lens.

INNOVATION PLATFORM ALIGNMENT:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Technology: {company.get('technology_description', company.get('description', 'N/A'))}
  Innovation Platforms Touched: {company.get('innovation_platforms', 'N/A')}
  AI/ML Integration: {company.get('ai_integration', 'N/A')}

GROWTH METRICS (5-YEAR PATH TO 5X):
  Current Revenue: {income.get('revenue', 'N/A')}
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Revenue Growth (3yr CAGR): {metrics.get('revenue_cagr_3yr', 'N/A')}
  Gross Margin: {income.get('gross_margin', 'N/A')} (SaaS/platform margins compress CAC)
  Gross Margin Trend: {income.get('gross_margin_trend', 'N/A')}
  ARR / Recurring Revenue %: {company.get('arr', metrics.get('recurring_revenue_pct', 'N/A'))}

MARKET OPPORTUNITY:
  TAM (Total Addressable Market): {company.get('tam_size', 'N/A')}
  SAM (Serviceable): {company.get('sam_size', 'N/A')}
  TAM Penetration: {company.get('tam_penetration', 'N/A')}
  Implied Revenue in 5 years (at full TAM): {company.get('tam_5yr_revenue', 'N/A')}

COST CURVE / WRIGHT'S LAW:
  Unit Cost Decline Rate: {company.get('unit_cost_decline', 'N/A')}
  Cumulative Production Doublings: {company.get('cumulative_doublings', 'N/A')}
  Wright's Law Cost Reduction Target: {company.get('wrights_law_target', 'N/A')}

PLATFORM METRICS:
  Net Revenue Retention: {metrics.get('nrr', 'N/A')}
  Customer Count Growth: {metrics.get('customer_growth', 'N/A')}
  Engagement/Usage Metrics: {metrics.get('usage_growth', 'N/A')}
  R&D Spend: {income.get('r_and_d', income.get('research_and_development', 'N/A'))}
  R&D as % Revenue: {income.get('rd_pct_revenue', 'N/A')}

VALUATION (5-YEAR DCF):
  EV/Sales: {metrics.get('ev_sales', 'N/A')} (you use 5yr forward revenue)
  Current Market Cap: {company.get('market_cap', 'N/A')}
  5-Year Price Target: {metrics.get('price_target_5yr', 'N/A')}
  Implied 5x Path: {metrics.get('path_to_5x', 'N/A')}

CASH POSITION & RUNWAY:
  Cash: {data.get('balance_sheet', {}).get('cash', 'N/A')}
  Cash Burn Rate: {metrics.get('cash_burn', cash_flow.get('cash_burn', 'N/A'))}
  Months of Runway: {company.get('runway_months', 'N/A')}

Does this company sit at the intersection of multiple innovation platforms?
Is there a credible path to 5x in 5 years? What does Wright's Law say about unit economics?
What is the convergence opportunity? Be Cathie.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
