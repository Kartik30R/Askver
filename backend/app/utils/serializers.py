from __future__ import annotations

import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

try:
    # pydantic v2
    from pydantic import BaseModel
except Exception:
    try:
        # pydantic v1
        from pydantic import BaseModel  # type: ignore
    except Exception:
        BaseModel = None  # type: ignore


def to_primitive(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable primitives.

    Handles Pydantic models (.model_dump or .dict), datetimes, Decimals, UUIDs,
    lists, tuples, and dicts.
    """
    if obj is None:
        return None

    # Pydantic BaseModel (v2 uses model_dump)
    try:
        if BaseModel is not None and isinstance(obj, BaseModel):
            dump = getattr(obj, "model_dump", None) or getattr(obj, "dict", None)
            if callable(dump):
                return to_primitive(dump())
    except Exception:
        pass

    # dict
    if isinstance(obj, dict):
        return {k: to_primitive(v) for k, v in obj.items()}

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        return [to_primitive(v) for v in obj]

    # datetime
    if isinstance(obj, (datetime.datetime, datetime.date)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)

    # Decimal
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return str(obj)

    # UUID
    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, Enum):
        return obj.value

    # Fallback: primitive types (int, float, str, bool) or unknown objects
    return obj
