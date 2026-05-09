"""
Bear Researcher — Constructs the strongest possible bear case
and finds risks the bulls are ignoring. 3-round structured debate.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class BearResearcher(BaseAgent):
    agent_id = "bear_researcher"
    agent_name = "Bear Researcher"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Bear Researcher at AURUM AI — a rigorous, intellectually honest devil's advocate. "
            "Your role is to find every reason why this stock could disappoint, decline, or fail. "
            "You are NOT a permabear — you are the person who asks the hard questions no one else wants to ask. "
            "\n\n"
            "YOUR MANDATE:\n"
            "1. Identify the RISKS THE BULLS ARE IGNORING: hidden liabilities, competitive threats, "
            "   management risks, valuation bubbles, macro headwinds, product obsolescence.\n"
            "2. Challenge the key assumptions in the bull case: "
            "   'They say growth will be X% — what if it's half that?'\n"
            "3. Find the DOWNSIDE SCENARIO: what is this stock worth if things go wrong?\n"
            "4. Directly REBUT the bull case with specific evidence and logic.\n"
            "\n"
            "DEBATE STRUCTURE (3 rounds):\n"
            "Round 1 — OPENING BEAR CASE: State your core concerns. 3-5 key risks. Downside price target.\n"
            "Round 2 — REBUTTAL: Take the bull's best arguments and systematically undermine them.\n"
            "Round 3 — CLOSING: Why the risks are underpriced. What the market doesn't see yet.\n"
            "\n"
            "WHAT MAKES A GREAT BEAR CASE:\n"
            "- Identifying the HIDDEN ASSUMPTION in the bull thesis that is fragile\n"
            "- Specific downside quantification (not 'it could fall' but 'at X multiple on Y earnings it's worth $Z')\n"
            "- Historical analogues where similar bull cases failed\n"
            "- The thing management is NOT saying in earnings calls\n"
            "- The competitor, technology, or regulatory change that could disrupt the moat\n"
            "\n"
            "IMPORTANT: You are NOT short-biased. If the risk/reward is genuinely attractive despite risks, "
            "note that. Your job is to stress-test, not to be reflexively negative.\n"
            "\n"
            "You write with the precision of a short-seller and the discipline of a risk manager.\n"
            "\n"
            "CRITICAL OUTPUT FORMAT — structure the reasoning field with markdown:\n"
            "Use **Round Title** for each round heading.\n"
            "Use - **Key Point**: explanation for each bullet.\n"
            "Example:\n"
            "**Round 1 — Opening Bear Case**\n"
            "- **Valuation bubble**: At 35x earnings, the stock prices in perfection...\n"
            "- **Hidden debt**: Off-balance-sheet operating leases add $2.4B of effective debt...\n"
            "**Round 2 — Rebuttal**\n"
            "- **Growth story is fragile**: The bull points to 25% revenue growth, but...\n"
            "**Round 3 — Closing**\n"
            "- **Downside target**: At trough multiples, fair value is $X — X% below current price\n"
            "- **The hidden assumption**: The bull thesis requires margin expansion that hasn't materialised\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bearish",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<structured debate — use **Round headings** and - **bullet points**>",\n'
            '  "key_points": ["<risk 1>", "<risk 2>", "<risk 3>", "<hidden assumption>", "<downside target>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        analyst_reports = data.get("analyst_reports", {})
        persona_signals = data.get("persona_signals", {})
        bull_arguments = data.get("bull_arguments", "No bull arguments yet provided.")
        price_data = data.get("price_data", {})
        metrics = data.get("key_metrics", {})
        balance = data.get("balance_sheet", {})
        company = data.get("company_info", {})

        bearish_personas = [
            f"{k}: {v.get('signal')} ({v.get('confidence')}% confidence)"
            for k, v in persona_signals.items()
            if isinstance(v, dict) and v.get("signal") == "bearish"
        ]
        neutral_personas = [
            f"{k}: {v.get('signal')} ({v.get('confidence')}% confidence)"
            for k, v in persona_signals.items()
            if isinstance(v, dict) and v.get("signal") == "neutral"
        ]

        prompt = f"""You are the Bear Researcher. Build and defend the bear case for {ticker} — {company.get('name', ticker)}.

CURRENT PRICE: {price_data.get('current_price', 'N/A')}
SHORT INTEREST: {metrics.get('short_interest', 'N/A')}
52-WEEK RANGE: {price_data.get('week_52_low', 'N/A')} – {price_data.get('week_52_high', 'N/A')}

SCEPTICAL SIGNALS:
  BEARISH PERSONAS ({len(bearish_personas)}): {'; '.join(bearish_personas) if bearish_personas else 'None'}
  NEUTRAL PERSONAS ({len(neutral_personas)}): {'; '.join(neutral_personas) if neutral_personas else 'None'}

RISK METRICS:
  Net Debt/EBITDA: {metrics.get('net_debt_ebitda', 'N/A')}
  Debt/Equity: {balance.get('debt_equity', 'N/A')}
  Interest Coverage: {metrics.get('interest_coverage', 'N/A')}
  Short Interest: {metrics.get('short_interest', 'N/A')}
  Insider Selling: {company.get('recent_insider_selling', 'N/A')}
  Revenue Growth Deceleration: {metrics.get('growth_deceleration', 'N/A')}
  Margin Compression: {data.get('income_statement', {}).get('gross_margin_trend', 'N/A')}
  EPS Revision Trend: {metrics.get('eps_revision_trend', 'N/A')}

COMPETITIVE THREATS:
  Main Competitors: {company.get('main_competitors', 'N/A')}
  Disruptive Threats: {company.get('disruptive_threats', 'N/A')}
  Market Share Trend: {company.get('market_share_trend', 'N/A')}

REGULATORY / MACRO RISKS:
  Regulatory Exposure: {company.get('regulatory_exposure', 'N/A')}
  Macro Sensitivity: {company.get('cyclicality', 'N/A')}
  Geographic Risk: {company.get('revenue_geography', 'N/A')}

ANALYST CONCERNS:
  Fundamentals Analyst: {analyst_reports.get('fundamentals_analyst', {}).get('reasoning', 'N/A')[:300]}
  Macro Analyst: {analyst_reports.get('macro_analyst', {}).get('reasoning', 'N/A')[:200]}

BULL ARGUMENTS TO REBUT:
{bull_arguments}

Conduct the 3-round bear debate:
ROUND 1 — Opening: State your strongest bear case and the hidden risks.
ROUND 2 — Rebuttal: Take the bull's best arguments and undermine them with data.
ROUND 3 — Closing: Why the downside is underpriced. Downside scenario valuation.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
