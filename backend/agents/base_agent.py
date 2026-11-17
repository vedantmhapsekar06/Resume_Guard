import json
import logging
import re

import ollama
from json_repair import repair_json

from backend.config import MODEL_NAME, OLLAMA_HOST, LLM_NUM_CTX, LLM_NUM_PREDICT, MAX_INPUT_CHARS

logger = logging.getLogger(__name__)

_client = ollama.Client(host=OLLAMA_HOST)


class LLMOutputError(ValueError):
    """The model failed to return usable JSON (invalid, empty, or cut off)."""


def clip_text(text: str, limit: int = MAX_INPUT_CHARS) -> str:
    """
    Explicitly clips over-long input. Without this Ollama silently drops tokens that
    don't fit in num_ctx, and the model then answers from a partial document.
    """
    if len(text) <= limit:
        return text
    logger.warning("Input clipped from %d to %d characters before LLM call", len(text), limit)
    return text[:limit]


def _chat(system_prompt: str, user_prompt: str, temperature: float, num_predict: int, json_mode: bool):
    kwargs = dict(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={
            "temperature": temperature,
            "num_predict": num_predict,
            "num_ctx": LLM_NUM_CTX,
        },
    )
    if json_mode:
        kwargs["format"] = "json"   # constrains the model to emit syntactically valid JSON
    response = _client.chat(**kwargs)
    content = response["message"]["content"]
    truncated = response.get("done_reason") == "length"
    return content, truncated


def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
    """
    Sends a prompt to the local Ollama model and returns the raw text response.
    Low temperature by default since most agents need consistent, structured output.
    """
    content, truncated = _chat(system_prompt, user_prompt, temperature, LLM_NUM_PREDICT, json_mode=False)
    if truncated:
        logger.warning("LLM text response hit the token limit and was cut off")
    return content


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.2, retries: int = 1) -> dict:
    """
    Calls the LLM expecting a JSON object back.

    - Uses Ollama's JSON mode so the output is syntactically valid in the normal case.
    - If the output was CUT OFF by the token limit we do NOT 'repair' it (that would silently
      drop jobs/skills and look like a normal result). We retry once with a bigger budget and
      raise if it is still truncated.
    - json_repair is only used for genuine formatting slips on complete outputs.
    """
    num_predict = LLM_NUM_PREDICT
    last_raw = None

    for attempt in range(retries + 1):
        prompt = user_prompt
        if attempt > 0:
            prompt += "\n\nReturn ONLY one valid JSON object that follows the schema exactly."

        raw, truncated = _chat(system_prompt, prompt, temperature, num_predict, json_mode=True)
        last_raw = raw

        if truncated:
            logger.warning("LLM JSON output truncated at num_predict=%d (attempt %d)", num_predict, attempt + 1)
            num_predict = min(num_predict * 2, LLM_NUM_CTX // 2)
            continue

        cleaned = _strip_json_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                parsed = json.loads(repair_json(cleaned))
            except Exception:
                parsed = None

        if isinstance(parsed, dict) and parsed:
            return parsed

    raise LLMOutputError(
        "The local model did not return complete, valid JSON (the document may be too long "
        f"for the configured context). Last raw output:\n{last_raw}"
    )


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()
