"""bifrost OpenAI client factory — shared by keyword_extract / filter / draft."""
import os

from openai import OpenAI


def client() -> OpenAI:
    base = os.environ["BIFROST_URL"].rstrip("/").removesuffix("/chat/completions")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return OpenAI(base_url=base, api_key=os.environ["BIFROST_KEY"])


def model() -> str:
    return os.environ["CAS_MODEL"]
