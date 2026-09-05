#!/usr/bin/env python3
"""Emit an MCP-first Notion routing reminder without storing prompt text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

NOTION = re.compile(r"\bnotion\b", re.I)
PROMPT_KEYS = {"prompt", "message", "text", "input", "user_prompt", "instruction", "goal", "objective"}


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [part for item in value for part in strings(item)]
    if isinstance(value, dict):
        return [part for key, item in value.items() if str(key).lower() in PROMPT_KEYS for part in strings(item)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="UserPromptSubmit")
    parser.parse_args()
    payload = sys.stdin.read(262_144)
    try:
        prompt = "\n".join(strings(json.loads(payload)))
    except (json.JSONDecodeError, TypeError):
        prompt = payload
    if NOTION.search(prompt):
        print("NOTION_MCP_ROUTING_HOOK=required")
        print("notion_route=use_already_connected_mcp_tools")
        print("notion_auth=do_not_use_webview_browser_login_cookies_or_credentials")
        print("notion_action=inspect_connected_tool_list_and_schemas_before_calling")
        print("notion_fallback=record_gap_and_stop_if_mcp_is_unavailable_or_insufficient")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
