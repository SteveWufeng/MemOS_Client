# MemOS_Client

A lightweight Python client wrapper for the **MemOS Docker REST API**.

This is **not** the official [MemOS](https://github.com/MemTensor/MemOS) project. It is a third-party convenience module that wraps the `/product/*` endpoints (`search`, `add`, `chat`, `get_memory`, `delete_memory`, `feedback`) into a clean importable API — so your project can communicate with a running MemOS Docker container in a few lines of code.

---

## Prerequisites

You need a running **MemOS Docker stack** from the [official MemOS project](https://github.com/MemTensor/MemOS):

```bash
git clone https://github.com/MemTensor/MemOS.git
cd MemOS/docker
docker compose up -d
```

Verify it's alive:

```bash
curl http://localhost:8000/health
# {"status":"healthy","service":"memos","version":"1.0.1"}
```

---

## Installation

```bash
pip install git+https://github.com/SteveWufeng/MemOS_Client.git
```

---

## Package structure

```
memos_docker/
├── __init__.py        # Public API: MemOSClient, Memory, SearchResults, …
├── __main__.py        # python -m memos_docker entry point
├── types.py           # Memory, SearchResults, ChatResponse, HealthStatus dataclasses
├── models.py          # Response wrappers for /product/* API responses
├── client.py          # MemOSClient — HTTP client for the Docker API
└── cli.py             # CLI entry point
```

---

## Python API

### Connect

```python
from memos_docker import MemOSClient

client = MemOSClient()                          # http://localhost:8000
# client = MemOSClient("http://192.168.1.50:8000")

# Context manager (auto-closes the HTTP session)
with MemOSClient() as c:
    c.health()
```

### Health

```python
status = client.health()
# status.status    → "healthy"
# status.service   → "memos"
# status.version   → "1.0.1"
```

### Search

```python
results = client.search(
    query="What do I like?",
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    top_k=10,
)

len(results)                   # → int
results[0]                     # → Memory
results.top                     # → Memory with highest score | None

for m in results:
    print(m.id, m.content, m.score)
```

### Add a memory

```python
result = client.add_memory(
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    messages=[{"type": "text", "text": "I like strawberry"}],
    async_mode="sync",
)

result.success       # → bool
result.memory_ids    # → ["uuid-..."]
```

### Chat

```python
resp = client.chat(
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    query="What do you know about me?",
)

resp.response        # → str
```

### Get stored memories

```python
memories = client.get_memories(
    mem_cube_id="8736b16e-1d20-4163-980b-a5063c3facdc",
)
```

### Delete

```python
client.delete_memory(
    memory_ids=["uuid-1", "uuid-2"],
    writable_cube_ids=["8736b16e-1d20-4163-980b-a5063c3facdc"],
)
```

### Feedback

```python
client.add_feedback(
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    history=[{"role": "user", "content": "I like strawberry"}],
    feedback_content="Actually I prefer chocolate",
)
```

---

## CLI

Installation adds the `memos-docker` CLI command:

```bash
memos-docker --help
memos-docker health
memos-docker search "food" --user stev
memos-docker add-memory --user stev --text "I like hiking" --sync
memos-docker chat --user stev "What do you know about me?"
memos-docker get-memories --cube stev
memos-docker delete-memory --ids uuid-1 --writable-cubes stev
memos-docker feedback --user stev --content "Great service"
```

Add `--json` for JSON output (useful for scripting).

---

## `user_id` vs `cube_id`

MemOS uses two distinct identifiers. Here's what they mean:

| Field | Role | Example |
|-------|------|---------|
| `user_id` | **Who** is performing the action — logged in metadata for auditing | `"alice"`, `"agent-42"` |
| `cube_id` | **Where** the memory is stored — the actual namespace key in the graph DB | `"project-alpha"`, `"shared-team-cube"` |

**When you only pass `user_id`, `cube_id` defaults to the same value** — a single implicit cube per user. But they can differ:

```python
# Manager user writes into a project cube shared by the team
client.add_memory(
    user_id="manager-bob",
    writable_cube_ids=["project-alpha"],
    messages=[{"type": "text", "text": "Sprint goals updated"}],
)

# Any team member can read from it
client.search("goals", user_id="dev-carol", readable_cube_ids=["project-alpha"])
```

### Why use separate cubes?

- **Isolation** — Two cubes never see each other's memories. Keep a "personal" cube and a "work" cube in the same MemOS instance.
- **Composition** — Search/chat can query multiple cubes at once (`readable_cube_ids=["personal", "work"]`).
- **Sharing** — A cube can be shared across users or agents, while `user_id` still tracks who did what.

### I don't have a user concept in my app

MemOS always needs a namespace (`cube_id` or `user_id`). Pick one of these patterns:

| Pattern | What to pass | Use case |
|---------|-------------|----------|
| **Fixed default** | `user_id="default_user"` | Single-agent, single-tenant |
| **Per-session UUID** | Generate `uuid4()` per session | Ephemeral conversations |
| **Per-agent UUID** | One UUID per agent instance | Multi-agent with isolated memory |

All three work — MemOS auto-creates the namespace in the graph DB on first use.

---

## License

AGPL-3.0
