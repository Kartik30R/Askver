import os
from typing import Any

from app.core.config import settings


class BaseLLMProvider:
    """Thin wrapper around the concrete LangChain chat model provider used by nodes."""

    def __init__(self, model: str, temperature: float = 0.1, **kwargs: Any):
        self.model = model
        self.temperature = temperature
        self.kwargs = kwargs

    def build(self) -> Any:
        raise NotImplementedError


class GeminiChatLLM(BaseLLMProvider):
    """Creates a Gemini-backed LangChain chat model using the existing project settings."""

    def build(self) -> Any:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - defensive dependency guard
            raise RuntimeError(
                "langchain-google-genai is not installed. Install it with: pip install langchain-google-genai"
            ) from exc

        api_key = self.kwargs.pop("api_key", None) or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required to use Gemini models.")

        return ChatGoogleGenerativeAI(
            model=self.model,
            temperature=self.temperature,
            google_api_key=api_key,
            **self.kwargs,
        )


class NvidiaNIMChatLLM(BaseLLMProvider):
    """Creates an NVIDIA NIM chat model using the OpenAI-compatible API contract."""

    def build(self) -> Any:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
        except ImportError as exc:  # pragma: no cover - defensive dependency guard
            raise RuntimeError(
                "langchain-nvidia-ai-endpoints is not installed. Install it with: pip install langchain-nvidia-ai-endpoints"
            ) from exc

        api_key = self.kwargs.pop("api_key", None) or settings.NVIDIA_API_KEY or os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY is required to use NVIDIA NIM models.")

        base_url = self.kwargs.pop("base_url", None) or settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1"
        if not base_url.rstrip("/").endswith("/v1"):
            base_url = f"{base_url.rstrip('/')}/v1"

        return ChatNVIDIA(
            model=self.model,
            temperature=self.temperature,
            api_key=api_key,
            base_url=base_url,
            **self.kwargs,
            timeout=180,
           
        )


def get_llm(model: str | None = None, provider: str | None = None, **kwargs: Any) -> Any:
    """Return a provider-specific LangChain chat model without breaking the nodes when a provider is unavailable."""
    normalized_provider = (provider or settings.LLM_PROVIDER or "gemini").lower()
    resolved_model = model or settings.LLM_MODEL or "gemini-2.0-flash"

    if normalized_provider in {"gemini", "google"}:
        return GeminiChatLLM(model=resolved_model, **kwargs).build()

    if normalized_provider in {"nvidia", "nim", "nvidia-nim"}:
        return NvidiaNIMChatLLM(model=resolved_model, **kwargs).build()

    raise ValueError(f"Unsupported LLM provider: {provider}. Use 'gemini' or 'nvidia'.")
