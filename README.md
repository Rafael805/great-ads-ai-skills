# Great Ads AI — Skills for Claude Code

Public Claude Code skills for [Great Ads AI](https://www.greatads.io). These are **thin
clients**: the heavy lifting (AI image generation, brand styling, saving to your pipeline)
runs on the Great Ads AI hosted API. You connect with **one** Great Ads API key — no OpenAI or
Gemini keys of your own, and nothing to run locally beyond Claude Code.

## What's included

| Skill | What it does |
|---|---|
| `/static-ad` | Generate a finished static ad (4:5 feed + 9:16 story) for a brand in your workspace — on-brand angle + headline, your style, rendered on Great Ads AI and filed as a Ready-For-Review pipeline card. |
| `/update-brand` | Update your brand's knowledge — voice, tagline, ICP, words to avoid, and other guardrails the skills read every time they generate an ad. Reads the current brand, applies your change on Great Ads AI, and shows the result. |

More skills will be added here over time.

## Setup (one key)

1. **Install Claude Code** (if you haven't): `curl -fsSL https://claude.ai/install.sh | bash`
2. **Add this marketplace and install the plugin:**
   ```
   claude plugin marketplace add Rafael805/great-ads-ai-skills
   claude plugin install ad-creative@great-ads-ai-skills
   ```
3. **Get your key.** In the Great Ads AI dashboard go to **Settings → Integrations →
   Connect to Claude**, generate a key, and copy the ready-made env block into
   `~/.config/great-marketing-ai/great-marketing-ai.env`:
   ```
   GREAT_ADS_INTERNAL_API_KEY=gaa_live_…
   GREAT_ADS_INTERNAL_BASE_URL=https://www.greatads.io
   ```
4. **Use it:** in Claude Code run `/static-ad` and follow the prompts.

## Billing

Generation runs on Great Ads AI's hosted AI models and is billed to your workspace's
credits. Manage your balance and top up in the dashboard. Failed renders are auto-refunded.

## Privacy

This repo contains no secrets and no brand data — every brand's voice, styles, and assets are
loaded live from your own Great Ads AI workspace using your key.
