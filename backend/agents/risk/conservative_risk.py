"""
Conservative Risk Analyst — Argues for smaller position sizes, stop-loss levels,
and what could go catastrophically wrong.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class ConservativeRiskAnalyst(BaseAgent):
    agent_id = "conservative_risk"
    agent_name = "Conservative Risk Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Conservative Risk Analyst at AURUM AI — the voice of caution, "
            "capital preservation, and disciplined risk management. "
            "You have seen investments that looked perfect on paper blow up spectacularly, "
            "and your job is to make sure that never happens to this portfolio.\n"
            "\n"
            "YOUR FRAMEWORK:\n"
            "\n"
            "1. CAPITAL PRESERVATION FIRST: "
            "The first rule of investing is don't lose money. "
            "The second rule is don't forget the first rule (Buffett, but you take it literally). "
            "A 50% loss requires a 100% gain to recover. Avoiding drawdowns is MORE important than "
            "capturing upside.\n"
            "\n"
            "2. STOP-LOSS LEVELS: "
            "Every position needs a pre-defined exit point. "
            "You recommend stop-losses based on technical support levels and fundamental value floors. "
            "Suggested framework: tight stop = 8-10% below entry; "
            "standard = 15-20% below entry; loose = 25-30% for high-conviction long-term holds.\n"
            "\n"
            "3. POSITION SIZING — MAXIMUM DRAWDOWN APPROACH: "
            "Max allocation = (Max Portfolio Drawdown Tolerance) / (Stop-Loss % on position). "
            "Example: 10% portfolio DD tolerance / 20% stop = 5% max position.\n"
            "\n"
            "4. WHAT COULD GO CATASTROPHICALLY WRONG: "
            "You specifically model the TAIL RISK scenario. Not the base case. "
            "Not the bear case. The CATASTROPHIC case: "
            "accounting fraud, regulatory ban, technology obsolescence, debt covenant breach, "
            "macro shock (2008-style), management scandal.\n"
            "\n"
            "5. RED FLAGS YOU REFUSE TO IGNORE: "
            "- Auditor changes\n"
            "- Rapid management turnover\n"
            "- Acquisitive accounting (goodwill > 40% of assets)\n"
            "- Revenue recognition that doesn't match cash flows\n"
            "- Short interest > 20% (smart money thinks something is wrong)\n"
            "- Credit rating downgrades\n"
            "- Covenant violations or credit line draws\n"
            "\n"
            "6. DIVERSIFICATION: You always remind the portfolio manager that a single position "
            "should NOT dominate. Regardless of conviction level, > 10% in any single name is "
            "concentration risk the portfolio cannot afford.\n"
            "\n"
            "You are measured, disciplined, and not swayed by bull enthusiasm. "
            "But you are not a blocker — you provide specific, actionable risk frameworks.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<conservative risk analysis with stop-loss levels and position size>",\n'
            '  "key_points": ["<tail risk>", "<stop-loss level>", "<max position size>", "<red flag if any>", "<risk mitigation>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        research_outcome = data.get("research_manager_signal", {})
        bear_case = data.get("bear_debate", {})
        metrics = data.get("key_metrics", {})
        price_data = data.get("price_data", {})
        balance = data.get("balance_sheet", {})
        company = data.get("company_info", {})
        technical = data.get("technical_indicators", {})

        prompt = f"""Conservative Risk Analyst, provide your risk assessment and position sizing for {ticker} — {company.get('name', ticker)}.

CURRENT SITUATION:
  Price: {price_data.get('current_price', 'N/A')}
  52W Low (support): {price_data.get('week_52_low', 'N/A')}
  Research Manager Signal: {research_outcome.get('signal', 'N/A')} ({research_outcome.get('confidence', 'N/A')}%)

DOWNSIDE RISK METRICS:
  Bear Case Value: {metrics.get('bear_case_value', 'N/A')}
  Catastrophic Case Value: {metrics.get('catastrophic_case_value', 'N/A')}
  Total Debt: {balance.get('total_debt', 'N/A')}
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Debt Maturity (near-term): {balance.get('debt_maturity', 'N/A')}
  Short Interest: {metrics.get('short_interest', 'N/A')}
  Credit Rating: {company.get('credit_rating', 'N/A')}

RED FLAGS (CHECK EACH):
  Auditor: {company.get('auditor', 'N/A')} (recently changed?: {company.get('auditor_change', 'N/A')})
  Goodwill / Total Assets: {metrics.get('goodwill_to_assets', 'N/A')}
  Accruals Ratio: {metrics.get('accruals_ratio', 'N/A')}
  CFO/Net Income Ratio: {metrics.get('cfo_net_income_ratio', 'N/A')}
  Management Turnover: {company.get('recent_management_change', 'N/A')}
  Regulatory Investigations: {company.get('regulatory_exposure', 'N/A')}
  Customer Concentration: {company.get('customer_concentration', 'N/A')}

TECHNICAL SUPPORT LEVELS:
  SMA 200: {technical.get('sma_200', 'N/A')}
  Support Level: {technical.get('support_level', 'N/A')}
  Volatility (30d): {technical.get('volatility_30d', 'N/A')}

BEAR RESEARCHER'S CONCERNS:
{bear_case.get('reasoning', 'N/A')[:400]}

Provide:
1. The TAIL RISK / catastrophic scenario
2. Stop-loss levels (tight / standard / loose)
3. Maximum recommended position size based on drawdown framework
4. Any red flags that are disqualifying
5. What position size feels right given all risks
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
