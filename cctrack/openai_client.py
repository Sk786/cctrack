"""Fetch token usage from the OpenAI Usage API.

Endpoint: GET /v1/organization/usage/completions
Requires an API key with usage.read scope.

Docs: https://platform.openai.com/docs/api-reference/usage
"""
import urllib.request
import urllib.error
import json
from datetime import date, timedelta, timezone, datetime

from .parser import TokenEntry


_BASE = "https://api.openai.com/v1/organization/usage/completions"
_PROJECT_LABEL = "openai"


def _build_url(start: date, end: date, page_token: str | None = None) -> str:
    params = [
        f"start_time={int(datetime.combine(start, datetime.min.time().replace(tzinfo=timezone.utc)).timestamp())}",
        f"end_time={int(datetime.combine(end + timedelta(days=1), datetime.min.time().replace(tzinfo=timezone.utc)).timestamp())}",
        "bucket_width=1d",
        "limit=30",
    ]
    if page_token:
        params.append(f"page={page_token}")
    return f"{_BASE}?{'&'.join(params)}"


def fetch_openai_usage(api_key: str, days: int = 30) -> list[TokenEntry]:
    """Return TokenEntry list covering the last `days` days from the OpenAI Usage API."""
    end = date.today()
    start = end - timedelta(days=days - 1)

    entries: list[TokenEntry] = []
    page_token: str | None = None
    seen: set[str] = set()

    while True:
        url = _build_url(start, end, page_token)
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenAI API error {exc.code}: {exc.read().decode()}") from exc

        for bucket in body.get("data", []):
            ts_epoch: int = bucket.get("start_time", 0)
            ts = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
            for result in bucket.get("results", []):
                model = result.get("model_id", "unknown")
                input_toks = result.get("input_tokens", 0)
                output_toks = result.get("output_tokens", 0)
                # OpenAI reports cached reads separately
                cached_input = result.get("input_cached_tokens", 0)

                session_id = f"openai:{ts.date().isoformat()}:{model}"
                key = session_id
                if key in seen:
                    continue
                seen.add(key)

                entries.append(TokenEntry(
                    session_id=session_id,
                    timestamp=ts,
                    model=model,
                    project=_PROJECT_LABEL,
                    input_tokens=input_toks - cached_input,
                    output_tokens=output_toks,
                    cache_write_tokens=0,
                    cache_read_tokens=cached_input,
                    provider="openai",
                ))

        if body.get("has_more") and body.get("next_page"):
            page_token = body["next_page"]
        else:
            break

    return entries
