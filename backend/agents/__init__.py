"""
AURUM AI — Agent Registry
All agents are registered here for use by the LangGraph orchestrator.
"""

# Analyst agents
from agents.analysts.fundamentals_analyst import FundamentalsAnalyst
from agents.analysts.technical_analyst import TechnicalAnalyst
from agents.analysts.news_analyst import NewsAnalyst
from agents.analysts.macro_analyst import MacroAnalyst

# Persona agents
from agents.personas.buffett import BuffettAgent
from agents.personas.munger import MungerAgent
from agents.personas.graham import GrahamAgent
from agents.personas.lynch import LynchAgent
from agents.personas.fisher import FisherAgent
from agents.personas.cathie_wood import CathieWoodAgent
from agents.personas.ackman import AckmanAgent
from agents.personas.burry import BurryAgent
from agents.personas.pabrai import PabraiAgent
from agents.personas.damodaran import DamodaranAgent
from agents.personas.druckenmiller import DruckenmillerAgent
from agents.personas.taleb import TalebAgent
from agents.personas.jhunjhunwala import JhunjhunwalaAgent
from agents.personas.growth_agent import GrowthAgent
from agents.personas.news_sentiment import NewsSentimentAgent

# Debate agents
from agents.debate.bull_researcher import BullResearcher
from agents.debate.bear_researcher import BearResearcher
from agents.debate.research_manager import ResearchManager

# Risk agents
from agents.risk.aggressive_risk import AggressiveRiskAnalyst
from agents.risk.conservative_risk import ConservativeRiskAnalyst
from agents.risk.neutral_risk import NeutralRiskAnalyst

# Portfolio Manager
from agents.portfolio_manager import PortfolioManager


# ──────────────────────────────────────────────────────────────────────────────
# PERSONA REGISTRY
# Maps string keys to agent classes for dynamic instantiation by the orchestrator.
# Usage: agent = PERSONA_REGISTRY["buffett"](llm_router)
# ──────────────────────────────────────────────────────────────────────────────

PERSONA_REGISTRY: dict = {
    "buffett": BuffettAgent,
    "munger": MungerAgent,
    "graham": GrahamAgent,
    "lynch": LynchAgent,
    "fisher": FisherAgent,
    "cathie_wood": CathieWoodAgent,
    "ackman": AckmanAgent,
    "burry": BurryAgent,
    "pabrai": PabraiAgent,
    "damodaran": DamodaranAgent,
    "druckenmiller": DruckenmillerAgent,
    "taleb": TalebAgent,
    "jhunjhunwala": JhunjhunwalaAgent,
    "growth_agent": GrowthAgent,
    "news_sentiment": NewsSentimentAgent,
}


# ──────────────────────────────────────────────────────────────────────────────
# PERSONA INFO
# Metadata for UI display — name, style, description, avatar initials.
# ──────────────────────────────────────────────────────────────────────────────

PERSONA_INFO: dict = {
    "buffett": {
        "name": "Warren Buffett",
        "style": "Quality Value Investing",
        "description": (
            "The Oracle of Omaha. Buys wonderful businesses at fair prices and holds forever. "
            "Demands a 30%+ margin of safety, a durable moat, trustworthy management, "
            "and a business simple enough to understand in one paragraph."
        ),
        "avatar_initials": "WB",
        "era": "1960s–present",
        "famous_for": "Berkshire Hathaway, See's Candies, Coca-Cola, Apple",
    },
    "munger": {
        "name": "Charlie Munger",
        "style": "Multidisciplinary Mental Models",
        "description": (
            "Vice Chairman of Berkshire Hathaway. Uses a latticework of mental models from "
            "physics, biology, psychology, and economics. Always inverts first: "
            "'What could go catastrophically wrong?' Pays fair price for extraordinary quality."
        ),
        "avatar_initials": "CM",
        "era": "1960s–2023",
        "famous_for": "Mental model latticework, inversion, psychological biases in investing",
    },
    "graham": {
        "name": "Ben Graham",
        "style": "Deep Value / Defensive Investing",
        "description": (
            "Father of value investing and author of 'The Intelligent Investor'. "
            "Calculates the Graham Number (√22.5 × EPS × BVPS), checks P/E < 15, "
            "P/B < 1.5, and demands a clear margin of safety. Views Mr. Market as "
            "a manic-depressive partner to exploit, not follow."
        ),
        "avatar_initials": "BG",
        "era": "1920s–1976",
        "famous_for": "Graham Number, net-net investing, defensive investor criteria",
    },
    "lynch": {
        "name": "Peter Lynch",
        "style": "GARP / Everyday Investing",
        "description": (
            "Fidelity Magellan manager who compounded at 29%/year for 13 years. "
            "Popularised the PEG ratio (P/E ÷ growth rate). Classifies every stock into "
            "6 categories and champions 'invest in what you know' — finding multi-baggers "
            "in everyday consumer experiences before Wall Street notices."
        ),
        "avatar_initials": "PL",
        "era": "1977–1990",
        "famous_for": "PEG ratio, 6 stock categories, Fidelity Magellan Fund",
    },
    "fisher": {
        "name": "Phil Fisher",
        "style": "Scuttlebutt Growth Investing",
        "description": (
            "Pioneer of growth investing and author of 'Common Stocks and Uncommon Profits'. "
            "Uses the 15-point Scuttlebutt checklist — interviewing competitors, suppliers, "
            "and customers before investing. Focuses on R&D quality, sales organisation, "
            "management integrity, and businesses that will be significantly larger in 10 years."
        ),
        "avatar_initials": "PF",
        "era": "1950s–2004",
        "famous_for": "15-point checklist, Scuttlebutt method, long-term growth holding",
    },
    "cathie_wood": {
        "name": "Cathie Wood",
        "style": "Disruptive Innovation",
        "description": (
            "Founder of ARK Invest. Targets companies at the intersection of multiple "
            "innovation platforms: AI, robotics, genomics, fintech, energy storage. "
            "Uses Wright's Law cost curves to project 5-year scenarios and demands a "
            "credible path to 5x return (~38% CAGR). Ignores short-term earnings noise."
        ),
        "avatar_initials": "CW",
        "era": "2014–present",
        "famous_for": "ARK Invest, disruptive innovation thesis, Tesla bull case",
    },
    "ackman": {
        "name": "Bill Ackman",
        "style": "Activist / Concentrated Value",
        "description": (
            "Pershing Square founder. Runs 8-12 ultra-concentrated positions in simple, "
            "predictable, FCF-dominant businesses. Seeks activist catalysts to unlock value: "
            "management change, cost restructuring, capital return programmes. "
            "Demands FCF yields of 6-10%+ and clear downside protection."
        ),
        "avatar_initials": "BA",
        "era": "2004–present",
        "famous_for": "Pershing Square, Chipotle, Lowe's, Hilton activist investments",
    },
    "burry": {
        "name": "Michael Burry",
        "style": "Deep Contrarian Value",
        "description": (
            "The Big Short investor who predicted the 2008 housing collapse. "
            "Hunts for ignored and hated stocks — businesses the market has given up on. "
            "Demands FCF yield > 10%, asset-heavy businesses below liquidation value, "
            "and a specific catalyst that will force the market to re-rate."
        ),
        "avatar_initials": "MB",
        "era": "2000–present",
        "famous_for": "The Big Short, Scion Capital, housing market short",
    },
    "pabrai": {
        "name": "Mohnish Pabrai",
        "style": "Dhandho Value Investing",
        "description": (
            "Author of 'The Dhandho Investor'. Applies the Gujarati entrepreneur's philosophy: "
            "'Heads I win, tails I don't lose much.' Seeks low-risk, high-uncertainty situations "
            "with 50%+ discount to intrinsic value. Uses checklists, clones great investors, "
            "and bets big only on his highest-conviction ideas."
        ),
        "avatar_initials": "MP",
        "era": "1999–present",
        "famous_for": "Dhandho framework, checklist methodology, cloning Buffett",
    },
    "damodaran": {
        "name": "Aswath Damodaran",
        "style": "Rigorous DCF Valuation",
        "description": (
            "NYU Stern Professor and the world's foremost authority on valuation. "
            "Constructs explicit DCF models with stated assumptions on revenue growth, "
            "operating margins, reinvestment rates, and WACC. Maintains the world's largest "
            "database of sector betas and multiples. Believes every asset can be valued — "
            "and that narratives must be checked against numbers."
        ),
        "avatar_initials": "AD",
        "era": "1986–present",
        "famous_for": "Damodaran valuation spreadsheets, DCF methodology, sector databases",
    },
    "druckenmiller": {
        "name": "Stanley Druckenmiller",
        "style": "Macro-Driven Growth",
        "description": (
            "Former Soros partner and Duquesne Capital founder. "
            "Starts top-down: what is the macro regime? Which sectors benefit? "
            "Then finds the best stock in the best sector. Uses earnings revisions as "
            "his primary stock-level signal. Goes very large (20-30%) when macro + sector + "
            "stock all align. Has not had a single down year in 30 years."
        ),
        "avatar_initials": "SD",
        "era": "1980s–present",
        "famous_for": "Breaking the Bank of England trade (with Soros), Duquesne Capital",
    },
    "taleb": {
        "name": "Nassim Taleb",
        "style": "Antifragility / Tail Risk",
        "description": (
            "Author of 'The Black Swan' and 'Antifragile'. Classifies businesses as "
            "fragile (breaks under stress), robust (survives), or antifragile (gains from stress). "
            "Seeks positive convexity: limited downside, unlimited upside. "
            "Red flags: leverage, complexity, overoptimisation. "
            "Applies the barbell strategy: very safe + lottery tickets, nothing in between."
        ),
        "avatar_initials": "NT",
        "era": "1990s–present",
        "famous_for": "Black Swan, Antifragile, tail risk hedging",
    },
    "jhunjhunwala": {
        "name": "Rakesh Jhunjhunwala",
        "style": "GARP / Emerging Market Growth",
        "description": (
            "India's 'Big Bull' who turned ₹5,000 into a multi-billion portfolio. "
            "Prioritises management passion and integrity above all else. "
            "Seeks growth at a reasonable price driven by secular tailwinds — "
            "demographic, technology, infrastructure. Holds with extraordinary conviction "
            "through short-term noise for 3-5+ year compounding."
        ),
        "avatar_initials": "RJ",
        "era": "1985–2022",
        "famous_for": "Titan Industries, Star Health, India bull market conviction",
    },
    "growth_agent": {
        "name": "Growth Analyst",
        "style": "Pure Growth / Rule of 40",
        "description": (
            "A pure growth specialist who screens for revenue growth > 20% YoY, "
            "gross margin expansion, Rule of 40 compliance (growth + margin > 40%), "
            "and exceptional net revenue retention (NRR > 110%). "
            "Uses PEG ratios and forward TAM penetration to assess growth-adjusted valuation."
        ),
        "avatar_initials": "GA",
        "era": "Present",
        "famous_for": "SaaS metrics, NRR analysis, Rule of 40 framework",
    },
    "news_sentiment": {
        "name": "News Sentiment Agent",
        "style": "Event-Driven / Sentiment Analysis",
        "description": (
            "Aggregates and scores all news headlines (bullish/bearish/neutral) and "
            "insider transactions to generate a net sentiment reading. "
            "Identifies momentum of news flow, hard catalysts, and contrarian signals "
            "(bad news + insider buying = potential bottom). Scores NLP-style precision."
        ),
        "avatar_initials": "NS",
        "era": "Present",
        "famous_for": "News flow scoring, insider signal analysis, catalyst identification",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# ANALYST REGISTRY
# Four core analyst agents used as data pre-processors before persona layer.
# ──────────────────────────────────────────────────────────────────────────────

ANALYST_REGISTRY: dict = {
    "fundamentals_analyst": FundamentalsAnalyst,
    "technical_analyst": TechnicalAnalyst,
    "news_analyst": NewsAnalyst,
    "macro_analyst": MacroAnalyst,
}

ANALYST_INFO: dict = {
    "fundamentals_analyst": {
        "name": "Fundamentals Analyst",
        "description": "Analyses income statement, balance sheet, cash flow, and key valuation metrics.",
        "avatar_initials": "FA",
    },
    "technical_analyst": {
        "name": "Technical Analyst",
        "description": "Analyses RSI, MACD, SMA crossovers, Bollinger Bands, volume, and chart patterns.",
        "avatar_initials": "TA",
    },
    "news_analyst": {
        "name": "News Analyst",
        "description": "Identifies catalysts, risks, and sentiment from recent news and insider transactions.",
        "avatar_initials": "NA",
    },
    "macro_analyst": {
        "name": "Macro Analyst",
        "description": "Assesses how Fed policy, inflation, GDP, and yield curve affect this sector.",
        "avatar_initials": "MA",
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# DEBATE REGISTRY
# ──────────────────────────────────────────────────────────────────────────────

DEBATE_REGISTRY: dict = {
    "bull_researcher": BullResearcher,
    "bear_researcher": BearResearcher,
    "research_manager": ResearchManager,
}


# ──────────────────────────────────────────────────────────────────────────────
# RISK REGISTRY
# ──────────────────────────────────────────────────────────────────────────────

RISK_REGISTRY: dict = {
    "aggressive_risk": AggressiveRiskAnalyst,
    "conservative_risk": ConservativeRiskAnalyst,
    "neutral_risk": NeutralRiskAnalyst,
}


# ──────────────────────────────────────────────────────────────────────────────
# ALL EXPORTS
# ──────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Analyst agents
    "FundamentalsAnalyst",
    "TechnicalAnalyst",
    "NewsAnalyst",
    "MacroAnalyst",
    # Persona agents
    "BuffettAgent",
    "MungerAgent",
    "GrahamAgent",
    "LynchAgent",
    "FisherAgent",
    "CathieWoodAgent",
    "AckmanAgent",
    "BurryAgent",
    "PabraiAgent",
    "DamodaranAgent",
    "DruckenmillerAgent",
    "TalebAgent",
    "JhunjhunwalaAgent",
    "GrowthAgent",
    "NewsSentimentAgent",
    # Debate agents
    "BullResearcher",
    "BearResearcher",
    "ResearchManager",
    # Risk agents
    "AggressiveRiskAnalyst",
    "ConservativeRiskAnalyst",
    "NeutralRiskAnalyst",
    # Portfolio Manager
    "PortfolioManager",
    # Registries
    "PERSONA_REGISTRY",
    "PERSONA_INFO",
    "ANALYST_REGISTRY",
    "ANALYST_INFO",
    "DEBATE_REGISTRY",
    "RISK_REGISTRY",
]
