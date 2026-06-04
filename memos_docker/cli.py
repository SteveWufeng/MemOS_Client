#!/usr/bin/env python3
"""memos-docker — CLI for a running MemOS Docker container.

Usage:
  memos-docker health                              Check container health
  memos-docker search <query> --user <id>          Search memories
  memos-docker add-memory --user <id> --text <t>   Add a text memory
  memos-docker chat --user <id> <query>            Chat with MemOS
  memos-docker get-memories --cube <id>            List stored memories
  memos-docker delete-memory --ids <id>...         Delete memories by ID
  memos-docker feedback --user <id> --content <c>  Send feedback

Options:
  --url URL         MemOS server URL (default: http://localhost:8000)
  --json            Output raw JSON
"""
from __future__ import annotations

import argparse
import json
import sys

from .client import MemOSClient


def cmd_health(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        h = client.health()
        if args.json:
            print(json.dumps({"status": h.status, "service": h.service, "version": h.version}, indent=2))
            return
        print(f"status:  {h.status}")
        print(f"service: {h.service}")
        print(f"version: {h.version}")


def cmd_search(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        results = client.search(args.query, user_id=args.user, top_k=args.top_k)
        if args.json:
            _dump_json(results)
            return
        if not results:
            print("[search] No results found")
            return
        print(f"[search] {len(results)} result(s):")
        for m in results:
            flag = f"  score={m.score:.4f}" if m.score is not None else ""
            content = (m.content or "")[:120]
            print(f"  {m.id:<36} {content}  {flag}")


def cmd_add_memory(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        messages = [{"type": "text", "text": args.text}]
        result = client.add_memory(
            user_id=args.user,
            messages=messages,
            async_mode="sync" if args.sync else "async",
        )
        if args.json:
            print(json.dumps({"success": result.success, "memory_ids": result.memory_ids}, indent=2))
            return
        if result.success:
            msg = f"[add] success  memory_ids={result.memory_ids}"
            print(msg)
        else:
            print("[add] failed", file=sys.stderr)
            sys.exit(1)


def cmd_chat(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        resp = client.chat(
            user_id=args.user,
            query=args.query,
            system_prompt=args.system_prompt,
        )
        if args.json:
            print(json.dumps({"response": resp.response}, indent=2))
            return
        print(resp.response)


def cmd_get_memories(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        results = client.get_memories(
            mem_cube_id=args.cube,
            user_id=args.user,
            page=args.page,
            page_size=args.page_size,
        )
        if args.json:
            _dump_json(results)
            return
        if not results:
            print("[get-memories] No memories found")
            return
        print(f"[get-memories] {len(results)} memory(ies):")
        for m in results:
            content = (m.content or "")[:120]
            print(f"  {m.id:<36} {content}")


def cmd_delete_memory(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        result = client.delete_memory(
            memory_ids=args.ids,
            writable_cube_ids=args.writable_cubes,
        )
        if args.json:
            print(json.dumps({"success": result.success}, indent=2))
            return
        if result.success:
            print(f"[delete] {len(args.ids)} memory(ies) deleted")
        else:
            print("[delete] failed", file=sys.stderr)


def cmd_feedback(args: argparse.Namespace) -> None:
    with MemOSClient(base_url=args.url) as client:
        history = [{"role": "user", "content": args.content}]
        result = client.add_feedback(
            user_id=args.user,
            history=history,
            feedback_content=args.content,
        )
        if args.json:
            print(json.dumps({"success": result.success}, indent=2))
            return
        if result.success:
            print("[feedback] success")
        else:
            print("[feedback] failed", file=sys.stderr)


def _dump_json(results) -> None:
    out = []
    for m in results:
        out.append({
            "id": m.id,
            "content": m.content,
            "score": m.score,
            "created_at": m.created_at,
            "memory_type": m.memory_type,
        })
    print(json.dumps(out, indent=2, default=str))


def _get_gallery_path(path: str | None):
    pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="memos-docker — CLI for a running MemOS Docker container",
    )
    parser.add_argument("--url", default="http://localhost:8000", help="MemOS server URL")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p = sub.add_parser("health")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--user", required=True)
    p.add_argument("--top-k", type=int, default=10)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("add-memory")
    p.add_argument("--user", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--sync", action="store_true", help="Wait for processing")
    p.set_defaults(func=cmd_add_memory)

    p = sub.add_parser("chat")
    p.add_argument("--user", required=True)
    p.add_argument("query")
    p.add_argument("--system-prompt")
    p.set_defaults(func=cmd_chat)

    p = sub.add_parser("get-memories")
    p.add_argument("--cube", required=True, help="Memory cube ID (often same as user_id)")
    p.add_argument("--user", help="Optional user filter")
    p.add_argument("--page", type=int)
    p.add_argument("--page-size", type=int)
    p.set_defaults(func=cmd_get_memories)

    p = sub.add_parser("delete-memory")
    p.add_argument("--ids", nargs="+", required=True)
    p.add_argument("--writable-cubes", nargs="*", help="Writable cube IDs")
    p.set_defaults(func=cmd_delete_memory)

    p = sub.add_parser("feedback")
    p.add_argument("--user", required=True)
    p.add_argument("--content", required=True)
    p.set_defaults(func=cmd_feedback)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
