from openai import OpenAI

from tannhelse.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL


def _client() -> OpenAI:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Add it to .env.")
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def chat(messages: list[dict]) -> str:
    resp = _client().chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1200,
    )
    return resp.choices[0].message.content or ""
