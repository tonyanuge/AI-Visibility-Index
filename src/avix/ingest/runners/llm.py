"""Live engine runners. Real HTTP clients, GATED by API keys in the environment.
With no key, .available is False and the app stays in manual mode (no crash)."""
import httpx
from .base import EngineRunner
from ... import config

class OpenAIRunner(EngineRunner):
    name = "ChatGPT"
    def __init__(self, model="gpt-4o"):
        self.key = config.env("OPENAI_API_KEY"); self.model = model
    @property
    def available(self): return bool(self.key)
    def run(self, prompt: str) -> str:
        r = httpx.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

class PerplexityRunner(EngineRunner):
    name = "Perplexity"
    def __init__(self, model="sonar"):
        self.key = config.env("PERPLEXITY_API_KEY"); self.model = model
    @property
    def available(self): return bool(self.key)
    def run(self, prompt: str) -> str:
        r = httpx.post("https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

class GeminiRunner(EngineRunner):
    name = "Gemini"
    def __init__(self, model="gemini-2.0-flash"):
        self.key = config.env("GEMINI_API_KEY"); self.model = model
    @property
    def available(self): return bool(self.key)
    def run(self, prompt: str) -> str:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.model}:generateContent?key={self.key}")
        r = httpx.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

def available_runners() -> list[EngineRunner]:
    out = []
    for cls in (OpenAIRunner, PerplexityRunner, GeminiRunner):
        try:
            inst = cls()
            if inst.available:
                out.append(inst)
        except Exception:
            pass
    return out
