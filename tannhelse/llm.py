from typing import Iterable, Literal

from tannhelse.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_MODEL

# (kind, token) — kind is "reasoning" for the model's chain-of-thought
# (deepseek-reasoner only), "answer" for the user-visible response.
StreamEvent = tuple[Literal["reasoning", "answer"], str]


def _client():
    # Lazy import keeps `import openai` (~12s cold start) off the import path
    # of any caller — it only runs when the user actually sends a query.
    from openai import OpenAI

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


def stream_chat(messages: list[dict]) -> Iterable[StreamEvent]:
    stream = _client().chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1200,
        stream=True,
    )
    for event in stream:
        if not event.choices:
            continue
        delta = event.choices[0].delta
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            yield "reasoning", reasoning
        answer = getattr(delta, "content", None)
        if answer:
            yield "answer", answer
