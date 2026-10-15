"""Shared LLM helper for the research agent using the app-wide provider configuration."""
import asyncio
import logging
from typing import Type, TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.services.llm_provider import get_llm

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


async def structured_call(schema: Type[T], system: str, user: str, retries: int = 2) -> T:
    """Call the configured app LLM and parse the answer into `schema`, retrying on transient/parse errors."""
    llm = get_llm(model=settings.LLM_MODEL, provider=settings.LLM_PROVIDER, temperature=0.1).with_structured_output(schema)
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            result = await llm.ainvoke([("system", system), ("human", user)])
            if isinstance(result, dict):
                result = schema.model_validate(result)
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("structured_call %s failed (attempt %s): %s", schema.__name__, attempt + 1, exc)
            await asyncio.sleep(1.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


GROUNDING_RULES = """
GROUNDING RULES (apply to every finding):
- Use ONLY the material provided. Never invent speakers, numbers, competitors, quotes or commitments.
- Every finding needs evidence: copy quotes VERBATIM from the source and include speaker/timestamp when present.
- Mark basis=STATED only if someone actually said it; otherwise basis=INFERRED.
- Set confidence honestly. If evidence is thin, say LOW rather than guessing.
- If a section has nothing supported by evidence, return an empty list. Empty is better than speculative.
- Be specific and concise. No generic sales advice that is not tied to this transcript.
""".strip()
