from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def line_env() -> tuple[str, str, str]:
    channel_id = (os.getenv("LINE_CHANNEL_ID") or "").strip()
    channel_secret = (os.getenv("LINE_CHANNEL_SECRET") or "").strip()
    redirect_uri = (os.getenv("LINE_REDIRECT_URI") or "").strip()
    return channel_id, channel_secret, redirect_uri


def build_authorize_url(*, channel_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": channel_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "profile openid",
        "bot_prompt": "normal",
    }
    return "https://access.line.me/oauth2/v2.1/authorize?" + urlencode(params)


def http_json(req: Request) -> dict[str, Any]:
    with urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body) if body else {}
        if not isinstance(data, dict):
            raise ValueError("Expected JSON object.")
        return data


def exchange_code_for_access_token(
    *,
    code: str,
    channel_id: str,
    channel_secret: str,
    redirect_uri: str,
) -> str:
    token_body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": channel_id,
            "client_secret": channel_secret,
        }
    ).encode("utf-8")
    token_req = Request(
        "https://api.line.me/oauth2/v2.1/token",
        data=token_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    token_data = http_json(token_req)
    return str(token_data.get("access_token") or "").strip()


def fetch_line_profile(access_token: str) -> dict[str, Any]:
    profile_req = Request(
        "https://api.line.me/v2/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    return http_json(profile_req)
