---
name: create-style
description: Create a new reusable STYLE in your Great Ads AI Style Library — a saved look (a reusable prompt + optional example images) that /static-ad and the other creative skills can pick to render on-brand ads in that exact look. You write the reusable prompt; Great Ads AI stores the style on its servers. Use when the user says "create a style", "make a new style", "add a style to my library", "save this look as a style", "new ad/content/thumbnail style", or "/create-style". Asks whether the style should be for one brand, all your brands, or public. Runs entirely on the Great Ads AI API — no keys of your own beyond your one workspace key.
---

# Create a Style (hosted)

This skill saves a new **Style Library** entry in the user's Great Ads AI workspace. A style is
a reusable look — a name, a reusable generation **prompt template**, and optional example
reference images — that every downstream generator (`/static-ad` and the other creative skills)
can then pick to render creatives in that exact look. You do the craft (understand the look,
write a strong reusable prompt); Great Ads AI stores it and serves it back to every skill.

There is **no local image generation here** and no AI-provider keys — this is a thin client for
the Great Ads AI hosted API, using the user's one workspace key. All commands go through
`scripts/create_style.py` (stdlib-only; no pip installs). It reads `GREAT_ADS_INTERNAL_API_KEY`
+ `GREAT_ADS_INTERNAL_BASE_URL` from `~/.config/great-marketing-ai/great-marketing-ai.env`.

## Flow

1. **Understand the look + the type.** Get the style idea (the vibe / format / palette) and map
   it to a **style type** — this decides which Style Library tab it lands under:

   | User says | `--style-type` | extra |
   |---|---|---|
   | static ad | `ad` | `--ad-format static` |
   | video ad | `ad` | `--ad-format video` |
   | meme | `meme` | |
   | carousel | `carousel` | |
   | reel cover | `reel_cover` | |
   | YouTube thumbnail | `thumbnail` | |

   If the type is genuinely ambiguous, ask; otherwise pick the obvious mapping and proceed.

2. **Ask the visibility (one decision).** Ask which of these three the style should be — present
   it as a short numbered pick-list and let them choose:

   1. **This brand only** — only one brand in your workspace sees it. (`--scope brand --brand <slug>`)
   2. **All my brands** *(default)* — every brand in your workspace can pick it. (`--scope global`)
   3. **Public** — a shared preset visible to **every** agency on Great Ads. (`--scope public`)

   **Public is admin-only.** Only an admin workspace can publish a cross-agency preset; a
   normal workspace key gets a 403. If a non-admin picks Public, tell them that and fall back
   to "All my brands."

3. **Write ONE strong reusable prompt.** This is the real craft. Write a `prompt_template` that
   **locks the look, not one specific ad** — describe:
   - **palette** (named colors + hex), **typography** treatment, **composition / layout**
     language, **lighting + mood**, and the **render style** (photoreal, editorial, 3D, flat…);
   - the **format** if it's structural (split-screen, chat bubbles, whiteboard, before/after).

   Use placeholders for the parts that change per ad — `{{headline}}`, `{{subheadline}}`,
   `{{cta}}`, and `{{subject}}` — so the one saved style is reusable across many ads.

   **Keep it ratio-agnostic.** Do NOT bake an aspect ratio or orientation into the prompt
   (`4:5`, `9:16`, `portrait`, `landscape`) — one style is reused across ratios, and every
   generator states its own ratio at render time. A ratio in the prompt only fights an
   off-ratio render.

4. **(Optional) attach example images.** The style works from the prompt alone, but a reference
   image anchors the look much better. If the user has example image files locally, pass each as
   `--image <path>` (they upload to Great Ads and become the style's reference images; the first
   is the cover). No local files? Create it text-only now — they can render a couple of ads in
   this style with `/static-ad` later and add those as references from the dashboard.

5. **Create it.**
   ```bash
   python scripts/create_style.py create \
     --name "Cream-Gold Editorial" \
     --style-type ad --ad-format static \
     --category editorial \
     --description "Warm cream + gold editorial look for feed ads" \
     --prompt-template "<the reusable prompt with {{headline}} placeholders>" \
     --scope global \
     [--brand <slug>] \
     [--platforms instagram,linkedin] \
     [--image ./look-1.png --image ./look-2.png]
   ```

6. **Share the result.** Print the returned `View:` link so the user can open the new style in
   their Style Library, plus which tab to find it under. From then on every `/static-ad` run can
   pick this style.

## Notes

- **You author the prompt; the server just stores it.** There's no rendering step here — this
  skill only writes the Style Library entry. To make an actual ad in the style, use `/static-ad`.
- **Scope maps to `--scope`.** `brand` (needs `--brand`) · `global` (default) · `public`
  (admin key only). When in doubt, `global`.
- **Retry without re-uploading.** If images uploaded but the create then failed, the script
  prints the uploaded URLs as `--reference-url <url>` flags — re-run with those instead of
  `--image` to finish with zero new uploads (no orphaned storage).
- **No local keys.** If the script reports a missing key, the user generates one in the
  dashboard → Settings → Integrations → **Connect to Claude**, then pastes the ready-made env
  block into `~/.config/great-marketing-ai/great-marketing-ai.env`. The key needs the
  **Content publishing** (`content:write`) permission (the Connect-to-Claude key includes it).
