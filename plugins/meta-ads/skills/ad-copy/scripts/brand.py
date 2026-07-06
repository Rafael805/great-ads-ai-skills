#!/usr/bin/env python3
"""
Thin client for the Great Ads AI hosted brand-context API.

This script does NO copy generation and needs NO AI provider keys. It only
reads your workspace's brand data with your one Great Ads API key:

  - `brands`        -> list the brands in your workspace (slug + name)
  - `brand <slug>`   -> one brand's voice/audience/guards/offers/ad_headlines,
                        so Claude can write on-brand copy instead of guessing

Config: reads GREAT_ADS_INTERNAL_API_KEY + GREAT_ADS_INTERNAL_BASE_URL from
~/.config/great-marketing-ai/great-marketing-ai.env (or great-ads.env), then a
.env walking up from the cwd, then the process environment. Stdlib only — no
pip installs.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "great-marketing-ai"


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


def _request(method: str, path: str, cfg: dict) -> dict:
    key = _key(cfg)
    last_err = None
    for base in _bases(cfg):
        req = urllib.request.Request(
            f"{base}{path}",
            method=method,
            headers={"Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            # Don't retry other bases on a real 4xx (auth/scope/validation).
            if 400 <= e.code < 500:
                sys.exit(f"API {e.code}: {detail}")
            last_err = f"{e.code}: {detail}"
        except urllib.error.URLError as e:
            last_err = str(e)
    sys.exit(f"Request to {path} failed: {last_err}")


def cmd_brands(args, cfg):
    print(json.dumps(_request("GET", "/api/internal/brands", cfg), indent=2))


def cmd_brand(args, cfg):
    print(json.dumps(_request("GET", f"/api/internal/brand-context/{args.slug}", cfg), indent=2))


def main():
    p = argparse.ArgumentParser(description="Great Ads AI brand-context thin client")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("brands", help="List the brands in your workspace").set_defaults(func=cmd_brands)

    b = sub.add_parser("brand", help="Print a brand's voice/audience/guards/offers")
    b.add_argument("slug")
    b.set_defaults(func=cmd_brand)

    args = p.parse_args()
    args.func(args, load_config())


if __name__ == "__main__":
    main()
