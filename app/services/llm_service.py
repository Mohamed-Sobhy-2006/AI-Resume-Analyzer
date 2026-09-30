"""Google Gemini client (REST API, standard library only).

Every failure is converted into an LLMError with a safe, user-friendly message so
that an AI problem can never crash the application.
"""
import json
import logging
import re
import socket
import urllib.error
import urllib.request

from app.config import PLACEHOLDER_KEYS, settings

logger = logging.getLogger(__name__)
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(Exception):
    def __init__(self, user_message: str, technical: str = ""):
        super().__init__(technical or user_message)
        self.user_message = user_message


class LLMNotConfigured(LLMError):
    pass


class LLMUnavailable(LLMError):
    pass


class LLMBadResponse(LLMError):
    pass


def parse_json_text(text: str) -> dict:
    """Parse JSON from an LLM answer (handles ```json fences and extra text)."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    for candidate in (cleaned, cleaned[cleaned.find("{"): cleaned.rfind("}") + 1]):
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            continue
    raise LLMBadResponse("The AI service returned an unreadable answer.", "JSON parse failure")


class LLMService:
    def is_configured(self) -> bool:
        return settings.GEMINI_API_KEY.strip().lower() not in PLACEHOLDER_KEYS

    def generate(self, prompt: str, system: str = "", json_mode: bool = False, temperature: float = 0.3) -> str:
        if not self.is_configured():
            raise LLMNotConfigured("AI service is not configured.")
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        if json_mode:
            body["generationConfig"]["responseMimeType"] = "application/json"
        request = urllib.request.Request(
            API_URL.format(model=settings.GEMINI_MODEL),
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": settings.GEMINI_API_KEY},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            logger.error("Gemini HTTP error %s: %s", exc.code, exc.read()[:300])
            if exc.code in (400, 401, 403):
                raise LLMUnavailable("AI service rejected the request (check your GEMINI_API_KEY).") from exc
            if exc.code == 429:
                raise LLMUnavailable("AI service quota exceeded. Please try again later.") from exc
            raise LLMUnavailable("AI service is temporarily unavailable.") from exc
        except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
            logger.error("Gemini network error: %s", exc)
            raise LLMUnavailable("AI service is unavailable (network problem or timeout).") from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMBadResponse("The AI service returned an unreadable answer.") from exc
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected Gemini response: %s", str(data)[:300])
            raise LLMBadResponse("The AI service returned an empty or blocked answer.") from exc

    def generate_json(self, prompt: str, system: str = "") -> dict:
        return parse_json_text(self.generate(prompt, system=system, json_mode=True, temperature=0.2))


llm_service = LLMService()
