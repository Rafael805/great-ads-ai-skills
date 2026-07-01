#!/usr/bin/env python3
"""
Thin client for the Great Ads AI hosted /static-ad API.

This script does NO image generation and needs NO AI provider keys. It only talks
to the Great Ads AI API with your one workspace key:

  - `brand <slug>`  -> the brand's voice/ICP/guards (so Claude can write on-brand copy)
  - `styles`        -> your Style Library options (so the user can pick a look)
  - `generate ...`  -> render a finished 4:5 + 9:16 static ad on Great Ads AI's hosted
                       AI, save it as a Ready-For-Review pipeline card, and bill credits

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
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            # Don't retry other bases on a real 4xx (auth/scope/validation/credits).
            if 400 <= e.code < 500:
                sys.exit(f"API {e.code}: {detail}")
            last_err = f"{e.code}: {detail}"
        except urllib.error.URLError as e:
            last_err = str(e)
    sys.exit(f"Request to {path} failed: {last_err}")


def cmd_brand(args, cfg):
    print(json.dumps(_request("GET", f"/api/internal/brand-context/{args.slug}", cfg), indent=2))


def cmd_styles(args, cfg):
    print(json.dumps(_request("GET", "/api/internal/creative-styles", cfg), indent=2))


def cmd_generate(args, cfg):
    body = {
        "brand": args.brand,
        "headline": args.headline,
        "prompt": args.prompt,
        "ratios": [r.strip() for r in args.ratios.split(",") if r.strip()],
        "resolution": args.resolution,
        "model": args.model,
    }
    if args.style:
        body["styleId"] = args.style
    if args.subheadline:
        body["subheadline"] = args.subheadline
    if args.product_url:
        body["productImageUrl"] = args.product_url
    res = _request("POST", "/api/internal/creative/static-ad", cfg, body)
    data = res.get("data", res)
    print(json.dumps(data, indent=2))
    if data.get("reviewUrl"):
        print(f"\nReview: {data['reviewUrl']}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Great Ads AI static-ad thin client")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("brand", help="Print a brand's voice/ICP/guards")
    b.add_argument("slug")
    b.set_defaults(func=cmd_brand)

    s = sub.add_parser("styles", help="List the workspace's creative styles")
    s.set_defaults(func=cmd_styles)

    g = sub.add_parser("generate", help="Render + save a static ad (bills credits)")
    g.add_argument("--brand", required=True, help="Brand slug")
    g.add_argument("--headline", required=True, help="Headline baked into the ad")
    g.add_argument("--prompt", required=True, help="On-brand angle / art direction")
    g.add_argument("--style", help="creative_styles id to anchor the look")
    g.add_argument("--subheadline", help="Optional secondary line")
    g.add_argument("--ratios", default="4:5,9:16", help="Comma list: 4:5,9:16")
    g.add_argument("--resolution", default="2k", choices=["1k", "2k", "4k"])
    g.add_argument(
        "--model",
        default="gemini-3-pro-image-preview",
        choices=[
            "gemini-3-pro-image-preview",
            "gemini-3.1-flash-image-preview",
            "gpt-image-2",
        ],
    )
    g.add_argument("--product-url", help="Optional product/screenshot URL to feature")
    g.set_defaults(func=cmd_generate)

    args = p.parse_args()
    args.func(args, load_config())


if __name__ == "__main__":
    main()
