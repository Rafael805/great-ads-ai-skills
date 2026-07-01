#!/usr/bin/env python3
"""
Thin client for the Great Ads AI hosted brand-knowledge API.

Reads and updates ONE brand's own knowledge (voice, ICP, guardrails, offers copy)
— the exact context the Great Ads AI skills read when they generate ads. It talks
only to the Great Ads AI API with your one workspace key; nothing runs locally.

  - `show <slug>`             -> print the brand's current knowledge (voice/ICP/guards)
  - `update <slug> --json …`  -> update the changed fields, then print the new knowledge

Editable fields (all optional — send only what changes) in the --json object:
  name, one_liner, what_you_do, website, industry, tone, values, aesthetic,
  colors (list of hex), preferred_words (list), avoid_words (list),
  icp (a string, or an object, or null to clear)

Config: reads GREAT_ADS_INTERNAL_API_KEY + GREAT_ADS_INTERNAL_BASE_URL from
~/.config/great-marketing-ai/great-marketing-ai.env (or great-ads.env), then a .env
walking up from the cwd, then the process environment. Stdlib only — no pip installs.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "great-marketing-ai"

# Keys the hosted PATCH endpoint accepts. Sending anything else is rejected (400),
# so we filter client-side and fail loudly with a helpful message.
ALLOWED_FIELDS = {
    "name",
    "one_liner",
    "what_you_do",
    "website",
    "industry",
    "tone",
    "values",
    "aesthetic",
    "colors",
    "preferred_words",
    "avoid_words",
    "icp",
}


def _parse_env_file(path: Path) -> dict:
    out = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_config() -> dict:
    """Config-dir files first, then a project .env walking up, then os.environ.
    Already-set values are never overridden (matches the team env precedence)."""
    cfg: dict = {}
    candidates = [CONFIG_DIR / "great-marketing-ai.env", CONFIG_DIR / "great-ads.env"]
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / ".env").exists() or (parent / ".env.local").exists():
            candidates += [parent / ".env.local", parent / ".env"]
            break
    for f in candidates:
        for k, v in _parse_env_file(f).items():
            cfg.setdefault(k, v)
    for k, v in os.environ.items():
        cfg.setdefault(k, v)
    return cfg


def _bases(cfg: dict) -> list:
    raw = cfg.get("GREAT_ADS_INTERNAL_BASE_URL", "https://www.greatads.io")
    return [b.strip().rstrip("/") for b in raw.split(",") if b.strip()]


def _key(cfg: dict) -> str:
    key = cfg.get("GREAT_ADS_INTERNAL_API_KEY", "").strip()
    if not key:
        sys.exit(
            "Missing GREAT_ADS_INTERNAL_API_KEY. Generate one in the Great Ads AI "
            "dashboard → Settings → Integrations → Connect to Claude, then add it to "
            f"{CONFIG_DIR / 'great-marketing-ai.env'}"
        )
    return key


def _request(method: str, path: str, cfg: dict, body: dict | None = None) -> dict:
    key = _key(cfg)
    data = json.dumps(body).encode() if body is not None else None
    last_err = None
    for base in _bases(cfg):
        req = urllib.request.Request(
            f"{base}{path}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            # Don't retry other bases on a real 4xx (auth/scope/validation/not-found).
            if 400 <= e.code < 500:
                sys.exit(f"API {e.code}: {detail}")
            last_err = f"{e.code}: {detail}"
        except urllib.error.URLError as e:
            last_err = str(e)
    sys.exit(f"Request to {path} failed: {last_err}")


def cmd_show(args, cfg):
    print(json.dumps(_request("GET", f"/api/internal/brand-context/{args.slug}", cfg), indent=2))


def cmd_update(args, cfg):
    raw = args.json
    if raw == "-" or raw is None:
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"--json is not valid JSON: {e}")
    if not isinstance(payload, dict) or not payload:
        sys.exit("--json must be a non-empty JSON object of the fields to change.")

    unknown = sorted(set(payload) - ALLOWED_FIELDS)
    if unknown:
        sys.exit(
            f"Unknown field(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
        )

    res = _request("PATCH", f"/api/internal/brand-context/{args.slug}", cfg, payload)
    print(json.dumps(res.get("profile", res), indent=2))
    print("\nBrand updated.", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Great Ads AI brand-knowledge thin client")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("show", help="Print a brand's current knowledge")
    s.add_argument("slug")
    s.set_defaults(func=cmd_show)

    u = sub.add_parser("update", help="Update the changed brand fields (then print the result)")
    u.add_argument("slug")
    u.add_argument(
        "--json",
        help="JSON object of the fields to change (or '-' / omit to read from stdin)",
    )
    u.set_defaults(func=cmd_update)

    args = p.parse_args()
    args.func(args, load_config())


if __name__ == "__main__":
    main()
