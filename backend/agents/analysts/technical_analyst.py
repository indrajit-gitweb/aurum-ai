"""
Technical Analyst — analyses price/volume patterns, momentum, and chart signals.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseAgent, AgentSignal


class TechnicalAnalyst(BaseAgent):
    agent_id = "technical_analyst"
    agent_name = "Technical Analyst"

    def _build_system_prompt(self) -> str:
        return (
            "You are a quantitative technical analyst with deep expertise in price action, "
            "momentum, and market structure. You read charts like a surgeon reads an X-ray. "
            "You prioritise high-probability setups: clean trend structures, volume confirmation, "
            "and momentum alignment across multiple timeframes. "
            "Key signals you weight heavily: RSI divergences, MACD histogram turns, "
            "golden/death cross on SMAs, Bollinger Band squeezes and expansions, "
            "volume spikes at key levels, and clearly defined support/resistance zones. "
            "You do NOT override strong technical signals with fundamental opinions. "
            "Overbought does not mean sell in a strong trend; oversold does not mean buy in a downtrend. "
            "Context is everything — trend first, then momentum, then entry timing. "
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
        tech = data.get("technical_indicators", {})
        price = data.get("price_data", {})

        prompt = f"""Perform a thorough technical analysis of {ticker}.

PRICE DATA:
  Current Price: {price.get('current_price', 'N/A')}
  52-Week High: {price.get('week_52_high', 'N/A')}
  52-Week Low: {price.get('week_52_low', 'N/A')}
  Price vs 52W High (%): {price.get('pct_from_52w_high', 'N/A')}
  Average Daily Volume (30d): {price.get('avg_volume_30d', 'N/A')}

MOVING AVERAGES:
  SMA 20: {tech.get('sma_20', 'N/A')}
  SMA 50: {tech.get('sma_50', 'N/A')}
  SMA 200: {tech.get('sma_200', 'N/A')}
  Price vs SMA 50 (%): {tech.get('price_vs_sma50', 'N/A')}
  Price vs SMA 200 (%): {tech.get('price_vs_sma200', 'N/A')}
  Golden/Death Cross: {tech.get('sma_cross_signal', 'N/A')}

MOMENTUM INDICATORS:
  RSI (14): {tech.get('rsi_14', 'N/A')}
  MACD Line: {tech.get('macd_line', 'N/A')}
  MACD Signal: {tech.get('macd_signal', 'N/A')}
  MACD Histogram: {tech.get('macd_histogram', 'N/A')}
  MACD Cross: {tech.get('macd_cross', 'N/A')}

BOLLINGER BANDS:
  Upper Band: {tech.get('bb_upper', 'N/A')}
  Middle Band: {tech.get('bb_middle', 'N/A')}
  Lower Band: {tech.get('bb_lower', 'N/A')}
  BB Width (volatility): {tech.get('bb_width', 'N/A')}
  Price vs BB (%B): {tech.get('bb_pct_b', 'N/A')}

VOLUME & SUPPORT/RESISTANCE:
  Volume vs Average (%): {tech.get('volume_vs_avg_pct', 'N/A')}
  Support Level: {tech.get('support_level', 'N/A')}
  Resistance Level: {tech.get('resistance_level', 'N/A')}
  Trend Direction: {tech.get('trend_direction', 'N/A')}

Assess momentum signals, trend direction, overbought/oversold conditions, and near-term price outlook.
Return your analysis as the specified JSON object.
"""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": prompt},
        ]

        response = self.llm.invoke(messages, task_type="quick")
        return self._parse_response(response, ticker)
