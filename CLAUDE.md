# CLAUDE.md

## How to work with me (the owner)

- I'm non-technical. Explain everything in plain English.
- Do one step at a time. Stop whenever I need to do something (create an account, click something in a dashboard, add a key).
- Ask before anything that costs money or can't be undone.
- Never ask me to paste API keys into chat. Tell me exactly where to put them.

## 1. Summary of project

A personal AI investment researcher that lives in WhatsApp. Users ask it anything about stocks and markets, and it messages them first when something matters for their portfolio. Think "Instinct, but specialised in investing". Target: 100,000 paying users at about €10/month, so it must be built to scale from day one, with no throwaway prototype.

Features:
- One WhatsApp contact: "your researcher". Behind it sit sector agents (start with Tech, Banks & Financials, Energy). Users pick one from a menu, or just ask and a router sends the question to the right agent.
- Portfolio agent: users privately send their holdings (tickers, or a screenshot from their broker); every weekday morning they get a brief on what matters for those holdings (news, results, filings, big moves).
- Proactive: it messages users when something important happens, not only when asked.
- Tiers: pay more, unlock more sector agents (billing comes later, but design for it now).
- Invite-only to start: a beta for me and 10 friends, then paid, then public with a referral program.

Rules (non-negotiable):
- Never give personal investment advice: no buy/sell/hold/allocate about a user's own holdings or situation. The portfolio agent reports facts only.
- Sector agents may share views. Every reply with a view gets a footer added BY CODE, not by the AI, so it's always there: date and time, sources used, "AI-generated research, not investment advice".
- Every number must come from the data tool or a cited source, never from memory. If data is missing, say so.
- "Should I buy X?" gets a polite refusal plus the facts instead.
- The welcome message tells users they're talking to an AI.
- Store only what's needed: phone number, tickers and weights. Never amounts or account details.

## 2. How we're going to build it

- Language: TypeScript on Node.js.
- WhatsApp: Meta's official WhatsApp Cloud API (webhooks). Meta's terms limit AI-first products to users with EEA or Brazil numbers, so only accept EEA numbers for now. Messages we start ourselves (like morning briefs) must use Meta-approved templates when the user hasn't messaged us in the last 24 hours.
- AI: Anthropic Claude API. Use Claude Sonnet 5.5 for research answers and Claude Haiku 5.5 for cheap jobs (routing questions, checking replies). Use Claude's built-in web search and web fetch tools for news; add Financial Modeling Prep (FMP) as a tool for prices and fundamentals. If FMP's free tier doesn't cover European stocks, tell me and suggest an alternative.
- Compliance check: before any reply is sent, Haiku checks it for personal advice; if flagged, rewrite it as facts only.
- Hosting: a managed platform (Railway or Render, whichever is simpler) with automatic deploys from GitHub and a public HTTPS address for Meta's webhook.
- Database: managed Postgres (Supabase or Neon) for users, invite codes, holdings, tiers, usage and message logs.
- Built to scale:
  - acknowledge Meta's webhook instantly and do the AI work in the background
  - keep all state in the database
  - run scheduled jobs (morning briefs, alerts) separately
  - set per-user daily usage limits
  - track AI cost per user
- Secrets: in .env locally and in the hosting platform's secret settings, never in git.
- Later: Stripe for subscriptions and tiers.
