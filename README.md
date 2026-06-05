# MemOS Client

A lightweight Python client wrapper for the **MemOS REST API**.

This is not the official [MemOS](https://github.com/MemTensor/MemOS) project. It is a third-party convenience module that wraps the `/product/*` endpoints (`search`, `add`, `chat`, `get_memory`, `delete_memory`, `feedback`) into a clean importable API.

---

## Quick start (self-contained Docker setup)

This repo bundles everything needed to run **MemOS + Neo4j + Qdrant** in a single container. No external dependencies or monorepo checkout required.

```bash
# 1. Clone ONLY this repo
git clone https://github.com/SteveWufeng/MemOS_Client.git
cd MemOS_Client

# 2. (Optional) Create a .env file
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Build & start
docker compose up -d

# 4. Verify
curl http://localhost:8100/health

# 5. Use the client
pip install .
python -c "from memos_client import MemOSClient; c=MemOSClient(); print(c.health())"
```

### Manual testing

```bash
# Health check
docker compose exec memos curl -s http://localhost:8100/health

# Add memories
docker compose exec memos curl -s -X POST http://localhost:8100/product/add \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "messages": [{"role": "user", "content": "I love hiking"}]}'

docker compose exec memos curl -s -X POST http://localhost:8100/product/add \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "messages": [{"role": "user", "content": "I prefer coffee over tea"}]}'

# Search by semantic similarity
docker compose exec memos curl -s -X POST http://localhost:8100/product/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "query": "outdoor activities", "top_k": 5}' | python3 -m json.tool

# Chat with memory-augmented LLM (requires OPENAI_API_KEY in .env)
docker compose exec memos curl -s -X POST http://localhost:8100/product/chat/complete \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "query": "What do you know about me?"}' | python3 -m json.tool
```

### What's included

| File | Purpose |
|---|---|
| `Dockerfile` | Builds image with MemOS (PyPI) + Neo4j 5.26.6 + Qdrant v1.15.3 |
| `supervisord.conf` | Runs all three processes under a single supervisor |
| `docker-compose.yml` | One-service compose file with persistent volumes |

### Ports

| Port | Service |
|---|---|
| `8100` | MemOS REST API |
| `7474` | Neo4j HTTP browser |
| `7687` | Neo4j Bolt |
| `6333` | Qdrant HTTP |
| `6334` | Qdrant gRPC |

### Stopping

```bash
docker compose down -v   # -v also removes data volumes
```

---

## Prerequisites (if using your own MemOS instance)

If you already have a MemOS server running elsewhere, you don't need Docker at all.

```bash
pip install .
export MEMOS_BASE_URL=http://your-server:8000
```

---

## Installation

```bash
pip install git+https://github.com/SteveWufeng/MemOS_Client.git
```

---

## Package structure

```
memos_client/
├── __init__.py        # Public API: MemOSClient, Memory, SearchResults, ...
├── __main__.py        # python -m memos_client entry point
├── types.py           # Memory, SearchResults, ChatResponse, HealthStatus dataclasses
├── models.py          # Response wrappers for /product/* API responses
├── client.py          # MemOSClient - HTTP client for the Docker API
└── cli.py             # CLI entry point
```

---

## Python API

### Connect

```python
from memos_client import MemOSClient

client = MemOSClient()                          # http://localhost:8100
# client = MemOSClient("http://192.168.1.50:8100")

# Context manager (auto-closes the HTTP session)
with MemOSClient() as c:
    c.health()
```

### Health

```python
status = client.health()
# status.status    -> "healthy"
# status.service   -> "memos"
# status.version   -> "1.0.1"
```

### Search

```python
results = client.search(
    query="What do I like?",
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    top_k=10,
)

len(results)                   # -> int
results[0]                     # -> Memory
results.top                     # -> Memory with highest score | None

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

result.success       # -> bool
result.memory_ids    # -> ["uuid-..."]
```

### Chat

```python
resp = client.chat(
    user_id="8736b16e-1d20-4163-980b-a5063c3facdc",
    query="What do you know about me?",
)

resp.response        # -> str
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

Installation adds the `memos-client` CLI command:

```bash
memos-client --help
memos-client health
memos-client search "food" --user stev
memos-client add-memory --user stev --text "I like hiking" --sync
memos-client chat --user stev "What do you know about me?"
memos-client get-memories --cube stev
memos-client delete-memory --ids uuid-1 --writable-cubes stev
memos-client feedback --user stev --content "Great service"
```

Add `--json` for JSON output (useful for scripting).

---

## `user_id` vs `cube_id`

MemOS uses two distinct identifiers. Here's what they mean:

| Field | Role | Example |
|-------|------|---------|
| `user_id` | **Who** is performing the action - logged in metadata for auditing | `"alice"`, `"agent-42"` |
| `cube_id` | **Where** the memory is stored - the actual namespace key in the graph DB | `"project-alpha"`, `"shared-team-cube"` |

**When you only pass `user_id`, `cube_id` defaults to the same value** - a single implicit cube per user. But they can differ:

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

- **Isolation** - Two cubes never see each other's memories. Keep a "personal" cube and a "work" cube in the same MemOS instance.
- **Composition** - Search/chat can query multiple cubes at once (`readable_cube_ids=["personal", "work"]`).
- **Sharing** - A cube can be shared across users or agents, while `user_id` still tracks who did what.

### I don't have a user concept in my app

MemOS always needs a namespace (`cube_id` or `user_id`). Pick one of these patterns:

| Pattern | What to pass | Use case |
|---------|-------------|----------|
| **Fixed default** | `user_id="default_user"` | Single-agent, single-tenant |
| **Per-session UUID** | Generate `uuid4()` per session | Ephemeral conversations |
| **Per-agent UUID** | One UUID per agent instance | Multi-agent with isolated memory |

All three work - MemOS auto-creates the namespace in the graph DB on first use.

---

## License

AGPL-3.0
