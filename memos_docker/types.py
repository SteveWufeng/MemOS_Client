from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Memory:
    id: str
    content: str | None = None
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    memory_type: str | None = None


@dataclass
class SearchResults:
    results: list[Memory] = field(default_factory=list)

    def __bool__(self) -> bool:
        return len(self.results) > 0

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, idx: int) -> Memory:
        return self.results[idx]

    @property
    def top(self) -> Memory | None:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.score or 0.0)


@dataclass
class ChatResponse:
    response: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    status: str
    service: str
    version: str


@dataclass
class AddResult:
    success: bool
    memory_ids: list[str] = field(default_factory=list)


@dataclass
class DeleteResult:
    success: bool
