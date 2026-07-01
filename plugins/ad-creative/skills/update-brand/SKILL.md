---
name: update-brand
description: Update your brand's knowledge in Great Ads AI — the voice, ICP, offers, and guardrails the skills read every time they generate an ad. Use when the user says "update my brand", "change my brand voice / tagline / one-liner", "add words to avoid", "fix my ICP / audience", "the brand info is wrong", "update the brand for <slug>", or "/update-brand". Reads the current brand knowledge, makes the change on Great Ads AI's servers, and shows the result. Runs entirely on the Great Ads AI API — no keys of your own beyond your one workspace key.
---

# Update Brand (hosted)

This skill edits the brand knowledge stored in the user's Great Ads AI workspace — the
same brand context the `/static-ad` and other skills read to write on-brand copy. You do
the conversational craft (understand what should change, keep the brand's own voice);
Great Ads AI stores it and serves it back to every skill.

All commands go through `scripts/brand.py` (stdlib-only; no pip installs). It reads
`GREAT_ADS_INTERNAL_API_KEY` + `GREAT_ADS_INTERNAL_BASE_URL` from
`~/.config/great-marketing-ai/great-marketing-ai.env`.

## Flow

1. **Read the current brand.** Always start here so you edit from the real state, never
   from a guess. Ask which brand (a slug in their workspace) if it's unclear.
   ```bash
   python scripts/brand.py show <brand-slug>
   ```
   Read back `identity`, `voice`, `audience` (ICP), and `guards` so you know what's there.

2. **Confirm the change.** Restate what you're about to change in plain terms and, for a
   non-trivial edit, confirm with the user first. Keep the brand's existing voice — you're
   editing THEIR brand, not imposing a new one. Only touch the fields that should change.

3. **Apply the update.** Send ONLY the changed fields as a JSON object:
   ```bash
   python scripts/brand.py update <brand-slug> --json '{"one_liner":"…","avoid_words":["…"]}'
   ```
   The script prints the brand's new knowledge (exactly what the skills will now read).

4. **Confirm the result.** Summarize what changed in one or two lines and point out that the
   next ad/content generation will use the new knowledge automatically.

## Editable fields

Send any subset in the `--json` object — only the keys you include change:

| Field | What it is |
|---|---|
| `name` | Brand / business name |
| `one_liner` | Short tagline / one-line positioning |
| `what_you_do` | Product / service description (a few sentences) |
| `website` | Brand website URL |
| `industry` | Industry / vertical |
| `tone` | Voice & tone description |
| `values` | Brand values |
| `aesthetic` | Visual aesthetic / look |
| `colors` | Brand colors — a list of hex strings, e.g. `["#0B5FFF","#111827"]` |
| `preferred_words` | Words/phrases to favor — a list of strings |
| `avoid_words` | Words/phrases to never use — a list of strings |
| `icp` | Ideal customer — a plain-text description, an object, or `null` to clear |

## Notes

- **Read before you write.** Never `update` without a `show` first — you could overwrite good
  copy. Edit from the current state.
- **Only send what changes.** Fields you omit are left exactly as they are. To clear a text
  field, send an empty string (`""`); to clear the ICP, send `null`.
- **Lists replace, not append.** `avoid_words`/`preferred_words`/`colors` overwrite the whole
  list — to add one, `show` first, then send the full new list.
- **Non-secret brand copy only.** This skill edits voice/positioning/guardrails, never tokens,
  billing, or credentials.
- **No local keys.** If `brand.py` reports a missing key, the user generates one in the
  dashboard → Settings → Integrations → **Connect to Claude**, then pastes the ready-made env
  block into `~/.config/great-marketing-ai/great-marketing-ai.env`. The key needs the
  **Brand editing** permission (the Connect-to-Claude key includes it).
