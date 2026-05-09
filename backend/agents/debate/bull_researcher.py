"""
Bull Researcher — Constructs the strongest possible bull case
and rebuts bear arguments in a 3-round structured debate.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class BullResearcher(BaseAgent):
    agent_id = "bull_researcher"
    agent_name = "Bull Researcher"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Bull Researcher at AURUM AI — a passionate, rigorous advocate for the bullish thesis. "
            "Your role in the investment debate is to construct the STRONGEST possible case for why this stock "
            "will appreciate significantly from its current price. "
            "\n\n"
            "YOUR MANDATE:\n"
            "1. Build the bull case using ALL available evidence: fundamentals, technicals, news, macro, "
            "   and the consensus of persona signals.\n"
            "2. Cherry-pick the most compelling data points — but do NOT fabricate or ignore material risks "
            "   (you are not a cheerleader, you are an advocate who must anticipate counterarguments).\n"
            "3. Directly REBUT the bear case with specific counterarguments.\n"
            "4. Make the case that REWARDS outweigh RISKS at the current price.\n"
            "\n"
            "DEBATE STRUCTURE (3 rounds):\n"
            "Round 1 — OPENING BULL CASE: State your core thesis. 3-5 key catalysts. Valuation upside.\n"
            "Round 2 — REBUTTAL: Directly address the bear's specific arguments. Don't dodge. Destroy them.\n"
            "Round 3 — CLOSING: Synthesise why the bull case wins. Price target. Risk/reward summary.\n"
            "\n"
            "WHAT MAKES A GREAT BULL CASE:\n"
            "- Specific, quantified upside scenarios (not vague 'could go higher')\n"
            "- Identification of the KEY MISUNDERSTANDING the market has about this stock\n"
            "- Timing catalysts: what will cause the re-rating?\n"
            "- Comparison to historical analogues where similar setups played out well\n"
            "\n"
            "You are confident, data-driven, and persuasive. You write like you are presenting to a CIO.\n"
            "\n"
            "CRITICAL OUTPUT FORMAT — structure the reasoning field with markdown:\n"
            "Use **Round Title** for each round heading.\n"
            "Use - **Key Point**: explanation for each bullet.\n"
            "Example:\n"
            "**Round 1 — Opening Bull Case**\n"
            "- **Earnings acceleration**: Revenue growing 28% YoY while margins expand...\n"
            "- **Valuation discount**: Trading at 14x FCF vs sector peers at 21x...\n"
            "**Round 2 — Rebuttal**\n"
            "- **Competition is overstated**: The bear cites new entrants, but switching costs...\n"
            "**Round 3 — Closing**\n"
            "- **Price target**: At 18x normalised FCF, fair value is $X...\n"
            "- **Risk/Reward**: 3.5:1 upside/downside at current price\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<structured debate — use **Round headings** and - **bullet points**>",\n'
            '  "key_points": ["<catalyst 1>", "<catalyst 2>", "<catalyst 3>", "<rebuttal>", "<price target>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        analyst_reports = data.get("analyst_reports", {})
        persona_signals = data.get("persona_signals", {})
        bear_arguments = data.get("bear_arguments", "No bear arguments yet provided.")
        price_data = data.get("price_data", {})
        metrics = data.get("key_metrics", {})
        company = data.get("company_info", {})

        # Summarise bullish persona signals
        bullish_personas = [
            f"{k}: {v.get('signal')} ({v.get('confidence')}% confidence)"
            for k, v in persona_signals.items()
            if isinstance(v, dict) and v.get("signal") == "bullish"
        ]
        bearish_personas = [
            f"{k}: {v.get('signal')} ({v.get('confidence')}% confidence)"
            for k, v in persona_signals.items()
            if isinstance(v, dict) and v.get("signal") == "bearish"
        ]

        prompt = f"""You are the Bull Researcher. Build and defend the bull case for {ticker} — {company.get('name', ticker)}.

CURRENT PRICE: {price_data.get('current_price', 'N/A')}
52-WEEK RANGE: {price_data.get('week_52_low', 'N/A')} – {price_data.get('week_52_high', 'N/A')}

PERSONA SIGNALS SUMMARY:
  BULLISH ({len(bullish_personas)} personas): {'; '.join(bullish_personas) if bullish_personas else 'None'}
  BEARISH ({len(bearish_personas)} personas): {'; '.join(bearish_personas) if bearish_personas else 'None'}

ANALYST REPORTS:
  Fundamentals: {analyst_reports.get('fundamentals_analyst', {}).get('reasoning', 'N/A')[:300]}
  Technical: {analyst_reports.get('technical_analyst', {}).get('reasoning', 'N/A')[:200]}
  News: {analyst_reports.get('news_analyst', {}).get('reasoning', 'N/A')[:200]}
  Macro: {analyst_reports.get('macro_analyst', {}).get('reasoning', 'N/A')[:200]}

KEY METRICS:
  P/E: {metrics.get('pe_ratio', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  Revenue Growth: {data.get('income_statement', {}).get('revenue_growth_yoy', 'N/A')}

BEAR ARGUMENTS TO REBUT:
{bear_arguments}

Conduct the 3-round bull debate:
ROUND 1 — Opening: State your strongest bull case.
ROUND 2 — Rebuttal: Destroy the bear arguments above point by point.
ROUND 3 — Closing: Final synthesis and price target.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
