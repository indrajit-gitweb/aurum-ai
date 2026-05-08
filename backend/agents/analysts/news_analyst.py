"""
News Analyst — analyses recent news articles, press releases, and insider transactions
to identify catalysts, risks, and sentiment shifts.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class NewsAnalyst(BaseAgent):
    agent_id = "news_analyst"
    agent_name = "News Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are an expert equity research analyst specialising in news flow, event-driven catalysts, "
            "and sentiment analysis. You read between the lines of press releases, earnings call transcripts, "
            "regulatory filings, and news headlines to identify what is ACTUALLY being signalled — not just "
            "what management wants you to hear. "
            "You distinguish between signal and noise: a CEO share sale is noise if pre-planned under 10b5-1; "
            "a CFO departure mid-quarter is a red flag. "
            "You track insider buying as one of the most reliable bullish signals. "
            "You identify: upcoming catalysts (earnings, FDA approvals, contract announcements), "
            "lurking risks (regulatory probes, customer concentration warnings, macro headwinds mentioned in filings), "
            "and the momentum of news flow (is coverage accelerating, is tone shifting?). "
            "You weight recent news more heavily than old news and discount obvious PR fluff. "
            "\n\n"
            "Respond ONLY with a JSON object in this exact format:\n"
            "```json\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": <integer 0-100>,\n'
            '  "reasoning": "<detailed paragraph>",\n'
            '  "key_points": ["<point 1>", "<point 2>", "<point 3>", "<point 4>", "<point 5>"]\n'
            "}\n"
            "```"
        )

    def analyze(self, ticker: str, data: dict) -> AgentSignal:
        news = data.get("news", data.get("news_articles", []))  # BUG-01 fix
        insiders = data.get("insider_transactions", [])

        # Format news articles
        news_text = ""
        if news:
            for i, article in enumerate(news[:10], 1):
                headline = article.get("headline", article.get("title", "N/A"))
                source = article.get("source", "N/A")
                date = article.get("date", article.get("published_at", "N/A"))
                summary = article.get("summary", article.get("description", ""))
                news_text += f"  [{i}] {date} | {source}: {headline}"
                if summary:
                    news_text += f"\n       {summary[:200]}"
                news_text += "\n"
        else:
            news_text = "  No recent news articles available.\n"

        # Format insider transactions
        insider_text = ""
        if insiders:
            for txn in insiders[:8]:
                name = txn.get("name", "Unknown")
                role = txn.get("role", txn.get("title", "N/A"))
                action = txn.get("transaction_type", txn.get("action", "N/A"))
                shares = txn.get("shares", "N/A")
                value = txn.get("value", txn.get("total_value", "N/A"))
                date = txn.get("date", "N/A")
                insider_text += f"  {date} | {name} ({role}): {action} {shares} shares (~{value})\n"
        else:
            insider_text = "  No recent insider transactions available.\n"

        prompt = f"""Analyse the news flow and insider activity for {ticker}.

RECENT NEWS ARTICLES:
{news_text}
INSIDER TRANSACTIONS (last 90 days):
{insider_text}

Identify: key catalysts, material risks, sentiment direction, insider conviction signals, and any red flags.
Return your analysis as the specified JSON object.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
