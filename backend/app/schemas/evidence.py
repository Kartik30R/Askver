"""Evidence layer: every claim downstream must point at Source IDs, never at free-text URLs."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# 1 = regulatory filing, 2 = company IR / official site, 3 = reputable news, 4 = everything else
SourceTier = Literal[1, 2, 3, 4]


class Source(BaseModel):
    id: str                                   # "S" + hash(url); stable across runs, dedupes automatically
    title: str
    url: Optional[str] = None
    snippet: str
    tier: int = 4
    published_date: Optional[str] = None
    collected_by: str = ""                    # which agent fetched it
    query: str = ""


class Fact(BaseModel):
    """One atomic, checkable claim. Extraction agents emit these; framework/playbook nodes consume them."""
    id: str = Field(default="", description="Leave empty; assigned in code")
    claim: str = Field(description="One sentence, one assertion, self-contained")
    category: str = Field(description="FINANCIAL, STRATEGY, TECHNOLOGY, LEADERSHIP, INDUSTRY, COMPETITOR, TRIGGER, REGULATORY")
    value: Optional[str] = Field(default=None, description="Number or named entity if the claim has one, e.g. '72.5M'")
    period: Optional[str] = Field(default=None, description="e.g. 'FY25', 'Q2 2026'")
    source_ids: List[str] = Field(description="IDs from the provided source list ONLY")
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"


class FactList(BaseModel):
    facts: List[Fact]


# --- LangGraph reducers: parallel nodes write dicts keyed by id, merged without clobbering -----------
def merge_sources(left: Optional[Dict[str, dict]], right: Optional[Dict[str, dict]]) -> Dict[str, dict]:
    merged = dict(left or {})
    for k, v in (right or {}).items():
        if k not in merged or v.get("tier", 4) < merged[k].get("tier", 4):
            merged[k] = v
    return merged


def merge_facts(left: Optional[Dict[str, dict]], right: Optional[Dict[str, dict]]) -> Dict[str, dict]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged