"""
Research Manager — Reads the full bull/bear debate and synthesises
into an overall thesis, key risks, investment horizon, and recommended position size.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class ResearchManager(BaseAgent):
    agent_id = "research_manager"
    agent_name = "Research Manager"

    def _build_system_prompt(self) -> str:
        return (
            "You are the Research Manager at AURUM AI — the senior analyst who reads EVERYTHING "
            "and synthesises it into a final, balanced investment recommendation. "
            "You have read the full bull/bear debate, all analyst reports, and all persona signals. "
            "Your job is to cut through the noise and render a clear, well-supported verdict.\n"
            "\n"
            "YOUR OUTPUT (structured synthesis):\n"
            "1. OVERALL THESIS: One paragraph that captures the core investment thesis — "
            "   what the market is getting wrong (or right) about this stock.\n"
            "2. BULL CASE SCORE (0-10): How strong was the bull's case?\n"
            "3. BEAR CASE SCORE (0-10): How strong was the bear's case?\n"
            "4. KEY RISKS (top 3): The risks that could most seriously impair the thesis.\n"
            "5. INVESTMENT HORIZON: Short (< 6 months), Medium (6-18 months), or Long (> 18 months).\n"
            "6. SIGNAL: bullish / bearish / neutral based on preponderance of evidence.\n"
            "7. RECOMMENDED POSITION SIZE: Small (1-3%), Medium (3-6%), Large (6-10%), "
            "   Full (10%+), or No Position.\n"
            "\n"
            "HOW YOU WEIGH EVIDENCE:\n"
            "- Fundamental analysis > technical analysis for long-horizon calls\n"
            "- Technical analysis > fundamental for short-horizon calls\n"
            "- Persona consensus of 8+ signals in same direction = high confidence\n"
            "- Persona consensus split (e.g. 7 bullish, 5 bearish) = lower conviction, smaller size\n"
            "- Strong bear debate > weak bull debate = bearish lean regardless of persona vote\n"
            "\n"
            "You are senior, measured, and balanced. You do not get swept up in either extreme. "
            "You acknowledge uncertainty. You size recommendations according to conviction. "
            "You write for a sophisticated investor who wants CLARITY, not entertainment.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<FULL DETAILED REPORT with these **sections** (use **heading** and - **bullets**):\\n**Overall Investment Thesis** — what the market is getting wrong or right\\n**Bull Case Assessment (score X/10)** — strongest bull arguments with specific data\\n**Bear Case Assessment (score X/10)** — strongest bear arguments with specific data\\n**Key Risks** — top 3 risks that could impair the thesis, each with explanation\\n**Persona Consensus** — what the collective signals reveal, where they diverge\\n**Investment Horizon** — why this is short/medium/long term\\n**Recommended Position** — specific size with conviction rationale>",\n'
            '  "key_points": ["<overall thesis>", "<top risk 1>", "<top risk 2>", "<horizon>", "<position size>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        bull_debate = data.get("bull_debate", {})
        bear_debate = data.get("bear_debate", {})
        persona_signals = data.get("persona_signals", {})
        analyst_reports = data.get("analyst_reports", {})
        company = data.get("company_info", {})
        price_data = data.get("price_data", {})
        metrics = data.get("key_metrics", {})

        # Tally persona signals
        signal_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        avg_confidence = {"bullish": [], "bearish": [], "neutral": []}
        for persona_name, signal_data in persona_signals.items():
            if isinstance(signal_data, dict):
                sig = signal_data.get("signal", "neutral")
                conf = signal_data.get("confidence", 50)
                signal_counts[sig] = signal_counts.get(sig, 0) + 1
                avg_confidence.setdefault(sig, []).append(conf)

        conf_summary = {
            k: f"{sum(v)/len(v):.0f}%" for k, v in avg_confidence.items() if v
        }

        prompt = f"""Research Manager, synthesise the full analysis for {ticker} — {company.get('name', ticker)}.

PERSONA SIGNAL TALLY:
  Bullish: {signal_counts['bullish']} personas (avg confidence: {conf_summary.get('bullish', 'N/A')})
  Bearish: {signal_counts['bearish']} personas (avg confidence: {conf_summary.get('bearish', 'N/A')})
  Neutral: {signal_counts['neutral']} personas (avg confidence: {conf_summary.get('neutral', 'N/A')})

PERSONA SIGNAL DETAILS:
{chr(10).join([f"  {k}: {v.get('signal', 'N/A')} ({v.get('confidence', 'N/A')}%)" for k, v in persona_signals.items() if isinstance(v, dict)])}

BULL RESEARCHER CASE:
{bull_debate.get('reasoning', 'Not available.')[:600]}

BEAR RESEARCHER CASE:
{bear_debate.get('reasoning', 'Not available.')[:600]}

ANALYST REPORTS SUMMARY:
  Fundamentals ({analyst_reports.get('fundamentals_analyst', {}).get('signal', 'N/A')}):
    {analyst_reports.get('fundamentals_analyst', {}).get('reasoning', 'N/A')[:200]}
  Technical ({analyst_reports.get('technical_analyst', {}).get('signal', 'N/A')}):
    {analyst_reports.get('technical_analyst', {}).get('reasoning', 'N/A')[:150]}
  News ({analyst_reports.get('news_analyst', {}).get('signal', 'N/A')}):
    {analyst_reports.get('news_analyst', {}).get('reasoning', 'N/A')[:150]}
  Macro ({analyst_reports.get('macro_analyst', {}).get('signal', 'N/A')}):
    {analyst_reports.get('macro_analyst', {}).get('reasoning', 'N/A')[:150]}

CURRENT METRICS:
  Price: {price_data.get('current_price', 'N/A')}
  P/E: {metrics.get('pe_ratio', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}

Render your synthesis: overall thesis, bull case score, bear case score,
top 3 risks, investment horizon, signal, and recommended position size.
Be the senior voice that cuts through the debate.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
