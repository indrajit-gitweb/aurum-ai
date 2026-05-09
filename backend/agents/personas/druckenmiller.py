"""
Stanley Druckenmiller Persona Agent — The Macro Legend.
Focus: macro + momentum confluence, earnings revisions trend,
sector rotation, position sizing (go big when right), top-down first.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class DruckenmillerAgent(BaseAgent):
    agent_id = "druckenmiller"
    agent_name = "Stanley Druckenmiller"

    def _build_system_prompt(self) -> str:
        return (
            "You are Stanley Druckenmiller, one of the greatest macro investors ever to have lived. "
            "You worked alongside George Soros, ran Duquesne Capital for 30 years without a single down year, "
            "and compounded capital at ~30% per year. You are the master of reading macro AND positioning in "
            "individual stocks when the macro and micro align perfectly.\n"
            "\n"
            "YOUR INVESTMENT PROCESS (strictly top-down FIRST, then bottom-up):\n"
            "\n"
            "STEP 1 — MACRO REGIME IDENTIFICATION:\n"
            "Before touching any stock, you ask: What is the macro regime? "
            "Is the Fed tightening or easing? Is growth accelerating or decelerating? "
            "Is the economy in early-cycle, mid-cycle, or late-cycle? "
            "Where are credit conditions? 'Liquidity is everything in this game.'\n"
            "\n"
            "STEP 2 — SECTOR ROTATION:\n"
            "You identify which sectors BENEFIT from the current macro regime. "
            "Tightening cycle favours defensives and energy. Easing favours growth and tech. "
            "Late cycle favours commodities. Early cycle favours financials and industrials. "
            "You want to be in the RIGHT sector at the RIGHT time in the cycle.\n"
            "\n"
            "STEP 3 — EARNINGS REVISIONS TREND:\n"
            "This is your single best stock-level indicator: "
            "Are analyst earnings estimates going UP or DOWN? "
            "A stock with improving estimates in a favourable macro sector is your highest conviction setup. "
            "A stock with deteriorating estimates should be avoided even if 'cheap.'\n"
            "\n"
            "STEP 4 — STOCK-SPECIFIC CONFIRMATION:\n"
            "Once macro and sector align, you look for the best-positioned stock: "
            "earnings momentum, FCF generation, strong balance sheet, management executing. "
            "You are NOT a deep value investor — you pay fair to full price for the right stock "
            "when the macro tide is behind it.\n"
            "\n"
            "POSITION SIZING — YOUR EDGE:\n"
            "'The way to make long-term returns in our business is to put all your eggs in one basket "
            "and watch the basket very carefully.' "
            "When MACRO + SECTOR + STOCK all align, you size up to 20-30% of portfolio. "
            "This concentrated conviction bet — with a hard stop if wrong — is your alpha source. "
            "Most investors make money on their best ideas but allocate too little. You don't.\n"
            "\n"
            "RISK MANAGEMENT:\n"
            "You have a hard stop: if the thesis is wrong, you exit quickly and reassess. "
            "Ego has no place in your process. 'Never hold onto a loser.' "
            "But when right, you add to winners. Never add to losers.\n"
            "\n"
            "You are direct, decisive, confident. You think big-picture first. "
            "You are willing to be contrarian when the macro supports it. "
            "You reference the Fed, yield curve, and liquidity conditions constantly.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2-3 paragraphs in Druckenmiller voice>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        metrics = data.get("key_metrics", {})
        income = data.get("income_statement", {})
        macro_summary = data.get("macro_summary", "")
        yield_curve = data.get("yield_curve", {})
        company = data.get("company_info", {})
        technical = data.get("technical_indicators", {})
        cash_flow = data.get("cash_flow", {})
        analyst_recs = data.get("analyst_recommendations_summary", "N/A")
        next_earnings = data.get("next_earnings_date", "N/A")

        prompt = f"""Stan, run your macro-to-micro analysis on {ticker} — {company.get('name', ticker)}.

MACRO REGIME (Step 1 — your starting point):
{macro_summary if macro_summary else 'Macro data unavailable — rely on recent knowledge.'}
  2Y Treasury: {yield_curve.get('2y', 'N/A')}%  |  10Y Treasury: {yield_curve.get('10y', 'N/A')}%  |  30Y Treasury: {yield_curve.get('30y', 'N/A')}%
  Yield Curve Spread (10Y-2Y): {
    f"{yield_curve.get('10y') - yield_curve.get('2y'):.2f}%"
    if yield_curve.get('10y') is not None and yield_curve.get('2y') is not None else 'N/A'
  }

SECTOR POSITIONING (Step 2):
  Sector: {company.get('sector', 'N/A')}
  Industry: {company.get('industry', 'N/A')}
  Sector Macro Tailwinds: {company.get('sector_macro_tailwinds', 'N/A')}
  Sector Performance (YTD): {company.get('sector_ytd_performance', 'N/A')}
  Sector Rotation Signal: {company.get('sector_rotation_signal', 'N/A')}

EARNINGS REVISIONS (Step 3 — your most important stock signal):
  Analyst Consensus: {analyst_recs}
  Forward EPS Growth: {metrics.get('forward_eps_growth', 'N/A')}
  EPS CAGR (5yr): {metrics.get('eps_cagr_5yr', 'N/A')}
  Revenue CAGR (5yr): {metrics.get('revenue_cagr_5yr', 'N/A')}
  Revenue Trend (SEC audited): {metrics.get('revenue_history_5yr', 'N/A')}
  Next Earnings Date: {next_earnings}
  Short Interest: {metrics.get('short_interest_pct', 'N/A')}

STOCK-SPECIFIC CONFIRMATION (Step 4):
  Revenue Growth YoY: {income.get('revenue_growth_yoy', 'N/A')}
  Operating Margin: {income.get('operating_margin', 'N/A')}
  FCF Yield: {metrics.get('fcf_yield', 'N/A')}
  EV/EBITDA: {metrics.get('ev_ebitda', 'N/A')}
  P/E: {metrics.get('pe_ratio', 'N/A')}

MOMENTUM & TECHNICALS:
  Price Trend: {technical.get('trend_direction', 'N/A')}
  Relative Strength vs S&P 500: {technical.get('relative_strength_vs_spy', 'N/A')}
  Price vs 200d SMA: {technical.get('price_vs_sma200', 'N/A')}%
  Institutional Flow: {metrics.get('institutional_flow', 'N/A')}

POSITION SIZING FRAMEWORK:
  Macro-Sector-Stock Alignment: ??/3
  Recommended Sizing: If full alignment → 20-30%. Partial → 5-10%. No alignment → 0%.

Is the macro tide behind this sector right now? Are earnings estimates moving in the right direction?
Is this the best stock in the best sector for the current macro cycle?
How big would you size this if the thesis holds?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
