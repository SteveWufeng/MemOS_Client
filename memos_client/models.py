from __future__ import annotations

from typing import Any


class BaseResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self.code: int = data.get("code", 200)
        self.message: str = data.get("message", "")
        self._raw: Any = data.get("data")


class SearchResponse(BaseResponse):
    @property
    def memories(self) -> list[dict[str, Any]]:
        if not isinstance(self._raw, dict):
            return []
        text_mem = self._raw.get("text_mem", [])
        if not isinstance(text_mem, list):
            return []
        results = []
        for cube_entry in text_mem:
            if not isinstance(cube_entry, dict):
                continue
            for m in cube_entry.get("memories", []):
                if isinstance(m, dict):
                    results.append(m)
        return results


class AddResponse(BaseResponse):
    @property
    def success(self) -> bool:
        return self.code == 200

    @property
    def memory_ids(self) -> list[str]:
        if isinstance(self._raw, list):
            return [r.get("memory_id", "") for r in self._raw if isinstance(r, dict)]
        return []

    @property
    def status(self) -> str | None:
        return "completed" if self.code == 200 else None


class ChatCompleteResponse(BaseResponse):
    @property
    def response(self) -> str:
        if isinstance(self._raw, dict):
            return self._raw.get("response", "")
        return str(self._raw) if self._raw else ""


class GetMemoryResponse(BaseResponse):
    @property
    def memories(self) -> list[dict[str, Any]]:
        if not isinstance(self._raw, dict):
            return []
        # The get_memory endpoint returns text_mem / pref_mem structure
        # (same as search), not memory_detail_list.
        results = []
        for key in ("text_mem", "memory_detail_list"):
            group = self._raw.get(key, [])
            if not isinstance(group, list):
                continue
            for entry in group:
                if not isinstance(entry, dict):
                    continue
                for m in entry.get("memories", []):
                    if isinstance(m, dict):
                        results.append(m)
            if results:
                break
        return results


class DeleteMemoryResponse(BaseResponse):
    @property
    def success(self) -> bool:
        if isinstance(self._raw, dict):
            status = self._raw.get("status", "")
            return self.code == 200 and status == "success"
        return self.code == 200


class FeedbackResponse(BaseResponse):
    @property
    def success(self) -> bool:
        return self.code == 200
