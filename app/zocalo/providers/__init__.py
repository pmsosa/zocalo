"""Model providers. Each one can list its models and complete a prompt. Keys never leave this module in clear."""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass

import httpx

from .. import db
from ..security import decrypt

TIMEOUT = httpx.Timeout(90.0, connect=15.0)


class ProviderError(Exception):
    """A provider call failed. `retry` says whether trying again later might work (rate limits, overload)."""

    def __init__(self, msg: str, retry: bool = False, status: int | None = None):
        super().__init__(msg)
        self.retry = retry
        self.status = status


@dataclass
class Completion:
    text: str
    tokens_in: int
    tokens_out: int


# kind → display name, default base URL, whether a key is required
KINDS = {
    "gemini": {"name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta", "key": True},
    "anthropic": {"name": "Anthropic", "base_url": "https://api.anthropic.com/v1", "key": True},
    "openai": {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "key": True},
    "litellm": {"name": "LiteLLM proxy", "base_url": "http://localhost:4000/v1", "key": False},
    "openai_compat": {"name": "OpenAI-compatible (OpenRouter, Ollama, vLLM, Groq…)", "base_url": "", "key": False},
}


def _raise_for(resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        body = resp.json()
        msg = body.get("error", {}).get("message") if isinstance(body.get("error"), dict) else body.get("error")
        msg = msg or body.get("message") or resp.text[:300]
    except ValueError:
        msg = resp.text[:300]
    retry = resp.status_code in (408, 409, 429, 500, 502, 503, 504, 529)
    raise ProviderError(f"{resp.status_code}: {msg}", retry=retry, status=resp.status_code)


# ---------- listing models ----------
async def list_models(kind: str, key: str, base_url: str | None) -> list[dict]:
    base = (base_url or KINDS[kind]["base_url"]).rstrip("/")
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        if kind == "gemini":
            out, token = [], None
            for _ in range(10):
                params = {"pageSize": 1000}
                if token:
                    params["pageToken"] = token
                r = await c.get(f"{base}/models", params=params, headers={"x-goog-api-key": key})
                _raise_for(r)
                body = r.json()
                for m in body.get("models", []):
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        mid = m["name"].split("/", 1)[-1]
                        out.append({"id": mid, "label": m.get("displayName") or mid})
                token = body.get("nextPageToken")
                if not token:
                    break
            return out
        if kind == "anthropic":
            r = await c.get(f"{base}/models", params={"limit": 1000},
                            headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            _raise_for(r)
            return [{"id": m["id"], "label": m.get("display_name") or m["id"]} for m in r.json().get("data", [])]
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        r = await c.get(f"{base}/models", headers=headers)
        _raise_for(r)
        data = r.json().get("data", [])
        models = [{"id": m["id"], "label": m["id"]} for m in data]
        if kind == "openai":  # hide embeddings, audio, image and moderation models
            models = [m for m in models if re.match(r"^(gpt|o\d|chatgpt)", m["id"])
                      and not re.search(r"audio|realtime|image|transcribe|tts|search|embedding", m["id"])]
        return sorted(models, key=lambda m: m["id"])


# ---------- completing ----------
async def complete(kind: str, key: str, base_url: str | None, model: str, system: str, user: str | list[dict],
                   json_mode: bool = True, max_tokens: int = 600, temperature: float | None = None) -> Completion:
    """`user` is one message, or a list of {"role": "user"|"assistant", "content": str} turns."""
    base = (base_url or KINDS[kind]["base_url"]).rstrip("/")
    turns = [{"role": "user", "content": user}] if isinstance(user, str) else user
    async with httpx.AsyncClient(timeout=TIMEOUT) as c:
        if kind == "gemini":
            body: dict = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "model" if t["role"] == "assistant" else "user", "parts": [{"text": t["content"]}]}
                             for t in turns],
                "generationConfig": {"maxOutputTokens": max_tokens},
            }
            if json_mode:
                body["generationConfig"]["responseMimeType"] = "application/json"
            if temperature is not None:
                body["generationConfig"]["temperature"] = temperature
            # Thinking models spend output tokens on hidden reasoning; keep it minimal for role-play answers.
            if re.search(r"gemini-(2\.5|3)", model) and "pro" not in model:
                body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
            r = await c.post(f"{base}/models/{model}:generateContent", json=body, headers={"x-goog-api-key": key})
            _raise_for(r)
            data = r.json()
            cands = data.get("candidates") or []
            if not cands:
                reason = data.get("promptFeedback", {}).get("blockReason", "no answer")
                raise ProviderError(f"blocked: {reason}")
            text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought"))
            u = data.get("usageMetadata", {})
            return Completion(text, u.get("promptTokenCount", 0),
                              u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0))
        if kind == "anthropic":
            body = {"model": model, "max_tokens": max_tokens, "system": system, "messages": turns}
            if temperature is not None:
                body["temperature"] = temperature
            if json_mode:  # prefill the opening brace so the reply is JSON
                body["messages"] = turns + [{"role": "assistant", "content": "{"}]
            r = await c.post(f"{base}/messages", json=body,
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            _raise_for(r)
            data = r.json()
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            if json_mode:
                text = "{" + text
            u = data.get("usage", {})
            return Completion(text, u.get("input_tokens", 0), u.get("output_tokens", 0))
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        body = {"model": model, "messages": [{"role": "system", "content": system}] + turns}
        if kind == "openai" and re.match(r"^(o\d|gpt-5)", model):
            body["max_completion_tokens"] = max(max_tokens, 2000)  # reasoning models count hidden tokens
        else:
            body["max_tokens"] = max_tokens
            if temperature is not None:
                body["temperature"] = temperature
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = await c.post(f"{base}/chat/completions", json=body, headers=headers)
        if r.status_code == 400 and json_mode and "response_format" in r.text:
            body.pop("response_format")  # some compatible servers don't support JSON mode
            r = await c.post(f"{base}/chat/completions", json=body, headers=headers)
        _raise_for(r)
        data = r.json()
        text = data["choices"][0]["message"].get("content") or ""
        u = data.get("usage", {}) or {}
        return Completion(text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0))


# ---------- helpers bound to stored providers ----------
def provider_row(provider_id: int) -> dict:
    row = db.q1("SELECT * FROM providers WHERE id=?", provider_id)
    if not row:
        raise ProviderError("provider not found")
    return row


def model_row(model_ref: str) -> dict:
    """model_ref is 'models.id' as a string."""
    row = db.q1("SELECT m.*, p.kind, p.base_url, p.key_enc, p.label AS provider_label FROM models m "
                "JOIN providers p ON p.id=m.provider_id WHERE m.id=?", int(model_ref))
    if not row:
        raise ProviderError(f"model {model_ref} not found")
    return row


def model_name(model_ref: str) -> str:
    try:
        r = model_row(model_ref)
        return f"{r['provider_label']} · {r['label']}"
    except (ProviderError, ValueError):
        return str(model_ref)


async def complete_ref(model_ref: str, system: str, user, *, json_mode=True, max_tokens=600, temperature=None,
                       retries: int = 4) -> tuple[Completion, dict]:
    m = model_row(model_ref)
    key = decrypt(m["key_enc"])
    delay = 2.0
    for attempt in range(retries + 1):
        try:
            comp = await complete(m["kind"], key, m["base_url"], m["model_id"], system, user,
                                  json_mode=json_mode, max_tokens=max_tokens, temperature=temperature)
            return comp, m
        except (ProviderError, httpx.TransportError) as e:
            retry = isinstance(e, httpx.TransportError) or e.retry
            if not retry or attempt == retries:
                raise ProviderError(str(e)) from e
            await asyncio.sleep(delay)
            delay *= 2
    raise ProviderError("unreachable")


def cost_of(m: dict, tokens_in: int, tokens_out: int) -> float:
    pin, pout = m.get("price_in") or 0.0, m.get("price_out") or 0.0
    return (tokens_in * pin + tokens_out * pout) / 1_000_000


def parse_json(text: str) -> dict:
    """Pull a JSON object out of a reply, tolerating code fences and stray text."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        v = json.loads(t)
        return v if isinstance(v, dict) else {"value": v}
    except ValueError:
        pass
    start, depth = t.find("{"), 0
    if start >= 0:
        for i in range(start, len(t)):
            if t[i] == "{":
                depth += 1
            elif t[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start:i + 1])
                    except ValueError:
                        break
    raise ValueError("reply was not JSON")
