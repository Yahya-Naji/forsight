"""The single place the pipeline talks to a language model.

Everything neural in this system goes through `structured()` or `text()`, so the
provider is one file rather than three call sites. The symbolic layer never
touches this module at all — that separation is the point of the architecture.

Provider: Azure OpenAI, Responses API.

Deployments (Azure calls a DEPLOYMENT NAME, not a model name):
  AZURE_OPENAI_DEPLOYMENT       reasoning work — synthesis, generation, verification
  AZURE_OPENAI_DEPLOYMENT_FAST  high-volume mechanical work — extraction

Extraction runs over every document and verification runs per sentence, so those
use the cheaper deployment. Synthesis and generation get the stronger one.
"""
from __future__ import annotations

import os
from typing import Optional, Type, TypeVar

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

load_dotenv()

T = TypeVar("T", bound=BaseModel)

DEFAULT_API_VERSION = "2025-04-01-preview"
_client: Optional[AzureOpenAI] = None


def _endpoint() -> str:
    """Accept either the bare resource URL or a full Responses URL with query
    string — the portal hands out the latter and it is easy to paste verbatim."""
    raw = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").strip()
    if not raw:
        raise RuntimeError(
            "AZURE_OPENAI_ENDPOINT is not set. Copy it from Azure AI Foundry → "
            "your resource → Keys and Endpoint.")
    return raw.split("/openai/")[0].rstrip("/")


def _api_version() -> str:
    raw = (os.environ.get("AZURE_OPENAI_ENDPOINT") or "")
    if "api-version=" in raw:                       # pasted full URL — honour it
        return raw.split("api-version=")[1].split("&")[0]
    return os.environ.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)


def client() -> AzureOpenAI:
    global _client
    if _client is None:
        key = (os.environ.get("AZURE_OPENAI_KEY")
               or os.environ.get("AZURE_OPENAI_API_KEY") or "").strip()
        if not key:
            raise RuntimeError("AZURE_OPENAI_KEY is not set.")
        _client = AzureOpenAI(api_key=key, azure_endpoint=_endpoint(),
                              api_version=_api_version(), timeout=300.0, max_retries=3)
    return _client


def deployment(fast: bool = False) -> str:
    if fast:
        name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_FAST")
        if name:
            return name
    name = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    if not name:
        raise RuntimeError(
            "AZURE_OPENAI_DEPLOYMENT is not set. This is the DEPLOYMENT NAME you "
            "chose in Azure AI Foundry, not the model id — a resource with no "
            "deployment returns 404 for every model name.")
    return name


def _reasoning_unsupported(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "reasoning" in msg and ("unsupported" in msg or "not supported" in msg
                                   or "unknown" in msg or "invalid" in msg)


def structured(prompt: str, schema: Type[T], *, fast: bool = False,
               effort: str = "high", max_output_tokens: int = 16000,
               instructions: Optional[str] = None) -> T:
    """Return a validated instance of `schema`.

    Validation happens at the API layer, so a malformed response is retried by
    the provider rather than silently parsed into something wrong. This is what
    lets the pipeline treat model output as a typed contract.
    """
    kwargs = dict(model=deployment(fast), input=prompt, text_format=schema,
                  max_output_tokens=max_output_tokens)
    if instructions:
        kwargs["instructions"] = instructions

    try:
        resp = client().responses.parse(reasoning={"effort": effort}, **kwargs)
    except Exception as exc:
        if not _reasoning_unsupported(exc):
            raise
        resp = client().responses.parse(**kwargs)   # non-reasoning deployment

    parsed = getattr(resp, "output_parsed", None)
    if parsed is None:
        raise RuntimeError("model returned no parsable output (status=%s)"
                           % getattr(resp, "status", "?"))
    return parsed


def text(prompt: str, *, fast: bool = False, effort: str = "high",
         max_output_tokens: int = 16000,
         instructions: Optional[str] = None) -> str:
    """Plain prose. Used only by generate.py, which needs markdown, not JSON."""
    kwargs = dict(model=deployment(fast), input=prompt,
                  max_output_tokens=max_output_tokens)
    if instructions:
        kwargs["instructions"] = instructions

    try:
        resp = client().responses.create(reasoning={"effort": effort}, **kwargs)
    except Exception as exc:
        if not _reasoning_unsupported(exc):
            raise
        resp = client().responses.create(**kwargs)

    out = getattr(resp, "output_text", None)
    if out:
        return out.strip()

    chunks = []                                      # older shapes
    for item in getattr(resp, "output", []) or []:
        for block in getattr(item, "content", []) or []:
            piece = getattr(block, "text", None)
            if piece:
                chunks.append(piece)
    return "".join(chunks).strip()


def check() -> None:
    """Fail loudly and usefully before a long run starts."""
    print("endpoint   : %s" % _endpoint())
    print("api-version: %s" % _api_version())
    print("deployment : %s  (fast: %s)"
          % (deployment(), os.environ.get("AZURE_OPENAI_DEPLOYMENT_FAST") or "—"))

    class Ping(BaseModel):
        ok: bool
        note: str

    got = structured('Reply with ok=true and note="reachable".', Ping,
                     max_output_tokens=2000, effort="low")
    print("response   : ok=%s note=%s" % (got.ok, got.note))
    print("✅ provider reachable")


if __name__ == "__main__":
    check()
