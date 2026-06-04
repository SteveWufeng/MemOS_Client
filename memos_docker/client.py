from __future__ import annotations

import os
from typing import Any

import httpx

from .models import (
    AddResponse,
    ChatCompleteResponse,
    DeleteMemoryResponse,
    FeedbackResponse,
    GetMemoryResponse,
    SearchResponse,
)
from .types import AddResult, ChatResponse, DeleteResult, HealthStatus, Memory, SearchResults

_DEFAULT_BASE_URL = "http://localhost:8000"


def _memory_from_dict(m: dict[str, Any]) -> Memory:
    md = m.get("metadata", {}) or {}
    return Memory(
        id=m.get("id", ""),
        content=m.get("memory"),
        score=m.get("score") or md.get("confidence"),
        metadata=md,
        created_at=md.get("created_at"),
        memory_type=md.get("memory_type") or m.get("memory_type"),
    )


class MemOSClient:
    """Client for the MemOS Docker API.

    Communicates with a running MemOS container at ``base_url``.
    Defaults to ``http://localhost:8000``.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("MEMOS_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    # ── raw request helpers ────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/product/{endpoint.lstrip('/')}"
        r = self._client.post(url, json=payload or {})
        r.raise_for_status()
        return r.json()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        r = self._client.get(url, params=params)
        r.raise_for_status()
        return r.json()

    # ── health ─────────────────────────────────────────────────────────────

    def health(self) -> HealthStatus:
        data = self._get("health")
        return HealthStatus(
            status=data.get("status", "unknown"),
            service=data.get("service", ""),
            version=data.get("version", ""),
        )

    # ── search ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        include_preference: bool = True,
        pref_top_k: int = 6,
        search_tool_memory: bool = True,
        tool_mem_top_k: int = 6,
        include_skill_memory: bool = True,
        skill_mem_top_k: int = 3,
        readable_cube_ids: list[str] | None = None,
        session_id: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> SearchResults:
        payload: dict[str, Any] = {
            "query": query,
            "user_id": user_id,
            "top_k": top_k,
            "include_preference": include_preference,
            "pref_top_k": pref_top_k,
            "search_tool_memory": search_tool_memory,
            "tool_mem_top_k": tool_mem_top_k,
            "include_skill_memory": include_skill_memory,
            "skill_mem_top_k": skill_mem_top_k,
        }
        if readable_cube_ids is not None:
            payload["readable_cube_ids"] = readable_cube_ids
        if session_id is not None:
            payload["session_id"] = session_id
        if filter is not None:
            payload["filter"] = filter

        resp = SearchResponse(self._post("search", payload))
        return SearchResults(results=[_memory_from_dict(m) for m in resp.memories])

    # ── add memory ─────────────────────────────────────────────────────────

    def add_memory(
        self,
        user_id: str,
        messages: list[dict[str, Any]] | None = None,
        memory_content: str | None = None,
        session_id: str | None = None,
        writable_cube_ids: list[str] | None = None,
        async_mode: str = "async",
        custom_tags: list[str] | None = None,
        info: dict[str, Any] | None = None,
    ) -> AddResult:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "async_mode": async_mode,
        }
        if messages is not None:
            payload["messages"] = messages
        if memory_content is not None:
            payload["memory_content"] = memory_content
        if session_id is not None:
            payload["session_id"] = session_id
        if writable_cube_ids is not None:
            payload["writable_cube_ids"] = writable_cube_ids
        if custom_tags is not None:
            payload["custom_tags"] = custom_tags
        if info is not None:
            payload["info"] = info

        resp = AddResponse(self._post("add", payload))
        return AddResult(success=resp.success, memory_ids=resp.memory_ids)

    # ── chat ───────────────────────────────────────────────────────────────

    def chat(
        self,
        user_id: str,
        query: str,
        history: list[dict[str, Any]] | None = None,
        readable_cube_ids: list[str] | None = None,
        writable_cube_ids: list[str] | None = None,
        system_prompt: str | None = None,
        top_k: int = 10,
        include_preference: bool = True,
        pref_top_k: int = 6,
        session_id: str | None = None,
        model_name: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        internet_search: bool = False,
        add_message_on_answer: bool = True,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "query": query,
            "top_k": top_k,
            "include_preference": include_preference,
            "pref_top_k": pref_top_k,
            "internet_search": internet_search,
            "add_message_on_answer": add_message_on_answer,
        }
        if history is not None:
            payload["history"] = history
        if readable_cube_ids is not None:
            payload["readable_cube_ids"] = readable_cube_ids
        if writable_cube_ids is not None:
            payload["writable_cube_ids"] = writable_cube_ids
        if system_prompt is not None:
            payload["system_prompt"] = system_prompt
        if session_id is not None:
            payload["session_id"] = session_id
        if model_name is not None:
            payload["model_name_or_path"] = model_name
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        resp = ChatCompleteResponse(self._post("chat/complete", payload))
        return ChatResponse(response=resp.response)

    # ── get memories ───────────────────────────────────────────────────────

    def get_memories(
        self,
        mem_cube_id: str,
        user_id: str | None = None,
        include_preference: bool = True,
        include_tool_memory: bool = True,
        include_skill_memory: bool = True,
        page: int | None = None,
        page_size: int | None = None,
        filter: dict[str, Any] | None = None,
    ) -> SearchResults:
        payload: dict[str, Any] = {
            "mem_cube_id": mem_cube_id,
            "include_preference": include_preference,
            "include_tool_memory": include_tool_memory,
            "include_skill_memory": include_skill_memory,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        if page is not None:
            payload["page"] = page
        if page_size is not None:
            payload["page_size"] = page_size
        if filter is not None:
            payload["filter"] = filter

        resp = GetMemoryResponse(self._post("get_memory", payload))
        return SearchResults(results=[_memory_from_dict(m) for m in resp.memories])

    # ── delete memory ──────────────────────────────────────────────────────

    def delete_memory(
        self,
        memory_ids: list[str] | None = None,
        writable_cube_ids: list[str] | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        filter: dict[str, Any] | None = None,
    ) -> DeleteResult:
        payload: dict[str, Any] = {}
        if memory_ids is not None:
            payload["memory_ids"] = memory_ids
        if writable_cube_ids is not None:
            payload["writable_cube_ids"] = writable_cube_ids
        if user_id is not None:
            payload["user_id"] = user_id
        if session_id is not None:
            payload["session_id"] = session_id
        if filter is not None:
            payload["filter"] = filter

        resp = DeleteMemoryResponse(self._post("delete_memory", payload))
        return DeleteResult(success=resp.success)

    # ── feedback ───────────────────────────────────────────────────────────

    def add_feedback(
        self,
        user_id: str,
        history: list[dict[str, Any]],
        feedback_content: str,
        session_id: str | None = None,
        writable_cube_ids: list[str] | None = None,
        async_mode: str = "async",
        corrected_answer: bool = False,
        info: dict[str, Any] | None = None,
    ) -> AddResult:
        payload: dict[str, Any] = {
            "user_id": user_id,
            "history": history,
            "feedback_content": feedback_content,
            "async_mode": async_mode,
            "corrected_answer": corrected_answer,
        }
        if session_id is not None:
            payload["session_id"] = session_id
        if writable_cube_ids is not None:
            payload["writable_cube_ids"] = writable_cube_ids
        if info is not None:
            payload["info"] = info

        resp = FeedbackResponse(self._post("feedback", payload))
        return AddResult(success=resp.success)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MemOSClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
