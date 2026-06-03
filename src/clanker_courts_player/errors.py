from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StructuredValidationError(ValueError):
    errors: list[dict[str, str]]

    def __str__(self) -> str:
        return str(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"ok": False, "errors": self.errors}
