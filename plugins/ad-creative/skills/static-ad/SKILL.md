---
name: static-ad
description: Generate a finished STATIC paid-social ad (4:5 feed + 9:16 story) for one of your brands in Great Ads AI. Writes one on-brand angle + headline from the brand's own voice, lets you pick a style from your Style Library, then renders the complete designed ad on Great Ads AI's hosted AI and files it in your pipeline as a Ready-For-Review card. Runs entirely on the Great Ads AI API — no AI provider keys of your own; billed to your workspace credits. Use when the user says "make a static ad", "static ad for <brand>", "Facebook/Instagram image ad", "feed + story ad", or "/static-ad".
---

# Static Ad (hosted)

This skill is a **thin client** for the Great Ads AI hosted API. You do the conversational
craft (pick the brand, write ONE strong on-brand angle + headline, help the user pick a
style); Great Ads AI does the rendering, styling, and saving on its own servers and AI
models. The only credential needed is the user's **one** Great Ads API key — there are no
OpenAI/Gemini keys here, and no local image generation.

All commands go through `scripts/render.py` (stdlib-only; no pip installs). It reads
`GREAT_ADS_INTERNAL_API_KEY` + `GREAT_ADS_INTERNAL_BASE_URL` from
`~/.config/great-marketing-ai/great-marketing-ai.env`.

## Flow

1. **Pick the brand.** Ask which brand (a slug in their Great Ads AI workspace). Then load its
   voice/ICP/guards so the copy is on-brand — do NOT invent voice:
   ```bash
   python scripts/render.py brand <brand-slug>
   ```
   Read `identity`, `voice`, `audience`, `guards` (do's/don'ts/words-to-avoid), and `offers`.

2. **Write ONE strong angle + headline.** Using the brand's real voice and a single clear
   conversion angle (a benefit, a pain, a proof point — not generic hype), write:
   - a punchy **headline** (the text baked into the ad), and
   - a short **angle / art-direction prompt** describing the scene, mood, and what to show.
   Honor the brand's guards (avoid banned words; match tone). Optionally offer the user 2–3
   headline options first and let them choose.

3. **Pick a style.** List the workspace's saved looks and let the user choose one (or a few):
   ```bash
   python scripts/render.py styles
   ```
   Each style has an `id` and a reference look. If the user wants several looks of the same
   angle, you'll call generate once per style (each becomes its own pipeline card).

4. **Render + save.** For each chosen style, render both ratios and file the card:
   ```bash
   python scripts/render.py generate \
     --brand <brand-slug> \
     --style <style-id> \
     --headline "Your headline" \
     --prompt "The on-brand angle / art direction" \
     --ratios 4:5,9:16
   ```
   Optional: `--subheadline "..."`, `--product-url <https url of a product/screenshot to feature>`,
   `--resolution 2k|4k`, `--model gemini-3-pro-image-preview` (default; highest quality).

5. **Share the result.** Print the returned `reviewUrl`(s) so the user can open the
   Ready-For-Review card(s) in their pipeline, plus `creditsConsumed` and `balanceAfter`.

## Notes

- **Stories never get a baked CTA button.** The 9:16 render omits any CTA button by design
  (the platform shows its own) — the server enforces this; you don't need to ask.
- **Credits.** Each render is billed to the workspace's Great Ads credits (your admin org and
  dev are free). On insufficient credits the API returns `402` with `required`/`balance` —
  relay that and point the user to top up in the dashboard. Failed renders are auto-refunded.
- **One angle, multiple styles.** The strong default is ONE angle rendered across the styles
  the user picks — variety comes from the styles, not from diluting the angle.
- **No local keys.** If `render.py` reports a missing key, the user generates one in the
  dashboard → Settings → Integrations → **Connect to Claude**, then pastes the ready-made env
  block into `~/.config/great-marketing-ai/great-marketing-ai.env`.
