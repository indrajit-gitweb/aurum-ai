# AURUM AI
### Your private hedge fund. 15 AI analysts. Zero cost.

[![Deploy to Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/indrajit-gitweb/aurum-ai&root=frontend)

AURUM AI brings institutional-grade stock analysis to everyone — for free.  
Powered by 15 legendary investor AI personas, a bull/bear debate engine, and a  
multi-provider LLM fallback system (Groq → Gemini → OpenRouter).

## Features
- 🧠 **15 Investor Personas** — Buffett, Burry, Lynch, Damodaran, Taleb & more
- ⚔️ **Bull vs Bear Debate** — structured adversarial research rounds
- 📊 **Free Data** — Yahoo Finance, SEC EDGAR, FRED (zero cost)
- ⚡ **Live Analysis Feed** — watch every agent think in real time
- 🔄 **Multi-LLM Fallback** — Groq → Gemini → OpenRouter, auto-switches on limits
- 🔑 **BYOK** — bring your own keys for unlimited access; shared pool for guests
- 🏦 **No cost. No sign-up. No catch.**

## Stack
| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Three.js + Framer Motion + GSAP |
| Backend | FastAPI + LangGraph + Python 3.11 |
| Data | yfinance + SEC EDGAR API + FRED API |
| LLM | Groq / Google Gemini / OpenRouter (free tiers) |
| Hosting | Vercel (frontend) + Render.com (backend) — both free |

## Local Development

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your keys
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_BACKEND_URL=http://localhost:8000
npm run dev
```

*Free forever | Educational use only — not financial advice*
