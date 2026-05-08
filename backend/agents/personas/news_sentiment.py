"""
News Sentiment Persona Agent — Aggregate News & Insider Signal Strength.
Focus: aggregate news sentiment, count positive vs negative headlines,
insider buy vs sell signal strength, momentum of news flow.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class NewsSentimentAgent(BaseAgent):
    agent_id = "news_sentiment"
    agent_name = "News Sentiment Agent"

    def _build_system_prompt(self) -> str:
        return (
            "You are a quantitative news sentiment analyst with expertise in natural language processing "
            "and event-driven investing. Your job is to aggregate all available news and insider signals "
            "and output a clear sentiment reading for the stock — no ambiguity allowed.\n"
            "\n"
            "YOUR METHODOLOGY:\n"
            "\n"
            "1. NEWS HEADLINE SCORING:\n"
            "   For each headline, assign: BULLISH (+1), BEARISH (-1), or NEUTRAL (0).\n"
            "   BULLISH keywords: beat, exceeds, raises guidance, partnership, contract, upgrade, "
            "   outperform, record, strong, accelerating, win, launch, acquisition of strategic asset.\n"
            "   BEARISH keywords: miss, cuts guidance, downgrade, underperform, loss, weak, "
            "   decline, investigation, lawsuit, resignation, warning, below expectations.\n"
            "   Calculate: Net Sentiment Score = (Bullish - Bearish) / Total headlines.\n"
            "   Score > +0.3: clearly bullish. Score < -0.3: clearly bearish. Otherwise: neutral.\n"
            "\n"
            "2. NEWS VELOCITY & MOMENTUM:\n"
            "   Is the volume of news INCREASING? Accelerating news = accelerating attention.\n"
            "   Is sentiment improving or deteriorating over the last 30 days?\n"
            "   Is this company in the news for NEW reasons or old ones?\n"
            "\n"
            "3. INSIDER TRANSACTION ANALYSIS:\n"
            "   STRONG BULLISH SIGNAL: Multiple insiders buying in open market (not options exercise).\n"
            "   BULLISH: Single large insider purchase > $500k.\n"
            "   NEUTRAL: Options exercise, 10b5-1 plan sales, small transactions.\n"
            "   BEARISH: Multiple insiders selling in open market.\n"
            "   STRONG BEARISH: CEO/CFO selling large blocks, clustered selling across officers.\n"
            "\n"
            "4. CATALYST IDENTIFICATION:\n"
            "   Is there an upcoming HARD catalyst? (Earnings date, FDA decision, contract announcement, "
            "   regulatory ruling, product launch, investor day)\n"
            "   Hard catalysts are more powerful than soft catalysts.\n"
            "\n"
            "5. SENTIMENT REGIME:\n"
            "   CONTRARIAN OPPORTUNITY: Overwhelmingly negative news + insider buying = potential bottom.\n"
            "   MOMENTUM PLAY: Consistently positive news + accelerating coverage.\n"
            "   DISTRIBUTION: Positive news but insiders selling heavily.\n"
            "\n"
            "You output numbers and clear verdicts. You do not editorialize beyond the signals. "
            "You cite specific headlines and transactions. You are a signal processor, not a storyteller.\n"
            "\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<2 paragraphs with specific headline counts and insider details>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        news = data.get("news_articles", [])
        insiders = data.get("insider_transactions", [])
        company = data.get("company_info", {})

        # Score news sentiment
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        bullish_keywords = [
            "beat", "exceeds", "raises", "upgrade", "outperform", "record",
            "strong", "win", "contract", "partnership", "launch", "growth"
        ]
        bearish_keywords = [
            "miss", "misses", "cuts", "downgrade", "underperform", "loss",
            "weak", "decline", "investigation", "lawsuit", "resignation",
            "warning", "below", "disappoints", "drops", "falls", "plunges"
        ]
        scored_headlines = []
        for article in news[:15]:
            headline = (article.get("headline", article.get("title", "")) or "").lower()
            b_score = sum(1 for kw in bullish_keywords if kw in headline)
            br_score = sum(1 for kw in bearish_keywords if kw in headline)
            if b_score > br_score:
                bullish_count += 1
                sentiment = "BULLISH"
            elif br_score > b_score:
                bearish_count += 1
                sentiment = "BEARISH"
            else:
                neutral_count += 1
                sentiment = "NEUTRAL"
            scored_headlines.append(
                f"  [{sentiment}] {article.get('date', 'N/A')}: "
                f"{article.get('headline', article.get('title', 'N/A'))[:100]}"
            )

        total = bullish_count + bearish_count + neutral_count
        net_score = (bullish_count - bearish_count) / total if total > 0 else 0
        headlines_text = "\n".join(scored_headlines) if scored_headlines else "  No headlines available."

        # Score insider transactions
        insider_buy_value = 0
        insider_sell_value = 0
        insider_lines = []
        for txn in insiders[:10]:
            action = (txn.get("transaction_type", txn.get("action", "")) or "").lower()
            value_str = str(txn.get("value", txn.get("total_value", "0")) or "0")
            try:
                value = float(value_str.replace("$", "").replace(",", "").replace("M", "e6").replace("K", "e3"))
            except (ValueError, AttributeError):
                value = 0
            name = txn.get("name", "Unknown")
            role = txn.get("role", txn.get("title", "N/A"))
            date = txn.get("date", "N/A")
            if "buy" in action or "purchase" in action:
                insider_buy_value += value
                signal = "BUY"
            elif "sell" in action or "sale" in action:
                insider_sell_value += value
                signal = "SELL"
            else:
                signal = "EXERCISE/OTHER"
            insider_lines.append(f"  [{signal}] {date} | {name} ({role}): ${value:,.0f}")
        insider_text = "\n".join(insider_lines) if insider_lines else "  No insider transactions available."

        prompt = f"""Aggregate the news and insider sentiment for {ticker} — {company.get('name', ticker)}.

NEWS SENTIMENT SCORING:
  Total Headlines Analysed: {total}
  Bullish Headlines: {bullish_count}
  Bearish Headlines: {bearish_count}
  Neutral Headlines: {neutral_count}
  Net Sentiment Score: {net_score:.2f} (range: -1 to +1)

SCORED HEADLINES:
{headlines_text}

INSIDER TRANSACTIONS (last 90 days):
  Total Insider Buy Value: ${insider_buy_value:,.0f}
  Total Insider Sell Value: ${insider_sell_value:,.0f}
  Net Insider Signal: {"BUYING" if insider_buy_value > insider_sell_value else "SELLING" if insider_sell_value > insider_buy_value else "NEUTRAL"}
{insider_text}

UPCOMING CATALYSTS:
  Next Earnings Date: {company.get('next_earnings_date', 'N/A')}
  Other Catalysts: {company.get('upcoming_catalysts', 'N/A')}

Provide your aggregate sentiment verdict:
- What is the net news sentiment score and its direction?
- Are insiders net buyers or sellers and how significant is the signal?
- Is there a contrarian opportunity (bad news + buying) or distribution (good news + selling)?
- What is the momentum of news flow?
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="deep")
        return self._parse_response(response, ticker)
