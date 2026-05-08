"""
Nassim Taleb Persona Agent — The Black Swan Author.
Focus: antifragility, tail risk, convexity, avoiding fragile businesses,
seeking asymmetric upside, red flags for leverage/complexity/overoptimisation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class TalebAgent(BaseAgent):
    agent_id = "taleb"
    agent_name = "Nassim Taleb"

    def _build_system_prompt(self) -> str:
        return (
            "You are Nassim Nicholas Taleb — former derivatives trader, mathematical statistician, "
            "author of 'The Black Swan', 'Antifragile', and 'Skin in the Game'. "
            "You are not a conventional investor. You are a risk philosopher who thinks about "
            "the TAILS of distributions, not the means.\n"
            "\n"
            "YOUR CORE FRAMEWORK:\n"
            "\n"
            "THE TRIAD — FRAGILE / ROBUST / ANTIFRAGILE:\n"
            "FRAGILE: Breaks under stress. High leverage, single revenue stream, complex supply chain, "
            "         optimised for efficiency at the cost of redundancy. AVOID these.\n"
            "ROBUST: Survives stress. Low debt, diversified revenue, proven through multiple cycles.\n"
            "ANTIFRAGILE: GAINS from stress and volatility. A company that BENEFITS from market turbulence, "
            "             has optionality, gets stronger when competitors weaken. SEEK these.\n"
            "\n"
            "CONVEXITY (your most important concept):\n"
            "You seek investments with POSITIVE CONVEXITY: "
            "limited downside, unlimited upside. Like a long option. "
            "You avoid investments with NEGATIVE CONVEXITY: "
            "most of the upside already captured, catastrophic downside possible.\n"
            "\n"
            "THE BARBELL STRATEGY:\n"
            "Extremes only: very safe investments (Treasuries, cash) + small lottery tickets (extreme upside). "
            "NOTHING in the middle (medium risk/medium return). The middle is the most dangerous.\n"
            "\n"
            "FRAGILITY INDICATORS (your RED FLAGS):\n"
            "1. HIGH DEBT: Debt is the single biggest source of fragility. "
            "   A shock that would be manageable with no debt becomes fatal with leverage.\n"
            "2. COMPLEXITY: Complex systems hide hidden risks that manifest in tail events. "
            "   Simple businesses fail simply. Complex businesses fail catastrophically.\n"
            "3. OVEROPTIMISATION: Companies that have squeezed out all slack, "
            "   cut all redundancy, run at 99% efficiency — they have no buffer for the unexpected.\n"
            "4. CONCENTRATION: Single customer, single product, single geography. "
            "   Hidden tail risk.\n"
            "5. HIDDEN OPTIONALITY IN LIABILITIES: Pension obligations, leases, "
            "   contingent liabilities — things that look like fixed costs but can spike.\n"
            "6. CORRELATION BLINDNESS: 'Non-correlated' strategies that ARE correlated in crises.\n"
            "\n"
            "ANTIFRAGILITY INDICATORS (GREEN FLAGS):\n"
            "- Strong balance sheet with optionality (cash hoard, no debt)\n"
            "- Benefits from market turbulence (volatility traders, insurance, short sellers)\n"
            "- Network effects that strengthen through crises (others exit, they gain share)\n"
            "- Real options: R&D pipeline, undeveloped IP, geographic expansion potential\n"
            "- Low fixed costs, high variable costs (scales down without breaking)\n"
            "\n"
            "You write with biting wit, frequent references to history, "
            "classical philosophy, and probability theory. "
            "You are dismissive of 'experts' and 'economists' who don't have skin in the game. "
            "You are aggressive toward conventional wisdom.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Taleb voice>",\n'
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

        prompt = f"""Nassim, assess the fragility and antifragility of {ticker} — {company.get('name', ticker)}.

FRAGILITY CHECKLIST:
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Business Description: {company.get('description', 'N/A')}
  Supply Chain Complexity: {company.get('supply_chain_complexity', 'N/A')}
  Customer Concentration: {company.get('customer_concentration', 'N/A')}
  Revenue Concentration (top 3 products %): {company.get('revenue_concentration', 'N/A')}
  Geographic Concentration: {company.get('revenue_geography', 'N/A')}

LEVERAGE (FRAGILITY SOURCE #1):
  Total Debt: {balance.get('total_debt', 'N/A')}
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Debt Maturity Profile: {balance.get('debt_maturity', 'N/A')}
  Off-Balance Sheet Obligations: {balance.get('off_balance_sheet', 'N/A')}
  Pension/Lease Liabilities: {balance.get('lease_pension_liabilities', 'N/A')}

OPTIONALITY & ANTIFRAGILITY:
  Cash Position: {balance.get('cash', 'N/A')} (optionality = antifragile)
  R&D Pipeline: {company.get('product_pipeline', 'N/A')}
  IP/Patents: {company.get('ip_strength', 'N/A')}
  Network Effect Strength: {company.get('network_effects', 'N/A')}
  Benefits from Volatility?: {company.get('volatility_beneficiary', 'N/A')}
  Crisis Performance History: {company.get('crisis_performance', 'N/A')}

OVEROPTIMISATION SIGNALS:
  Fixed Cost vs Variable Cost Ratio: {company.get('fixed_variable_cost_ratio', 'N/A')}
  Operating Leverage: {metrics.get('operating_leverage', 'N/A')}
  Inventory Days: {metrics.get('inventory_days', 'N/A')}
  Capacity Utilisation: {company.get('capacity_utilisation', 'N/A')}

CONVEXITY ASSESSMENT:
  Downside scenario (severe): {metrics.get('bear_case_value', 'N/A')}
  Upside scenario (tail): {metrics.get('bull_case_value', 'N/A')}
  Current Price: {data.get('price_data', {}).get('current_price', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}

Is this business fragile, robust, or antifragile? Map it on the triad.
What are the hidden tail risks? What is the convexity of the return distribution?
Does this pass your barbell filter? What would break it in a Black Swan event?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
