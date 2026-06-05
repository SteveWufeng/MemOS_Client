# =============================================================================
# MemOS All-in-One Docker Image
# =============================================================================
# Runs MemOS API + Neo4j (graph DB) + Qdrant (vector DB) in a single
# container via supervisord.  No separate containers needed.
# =============================================================================

FROM python:3.11-slim

# ------------------------------------------------------------------
# System dependencies
# ------------------------------------------------------------------
#   gcc/g++/build-essential/libffi   -- Python C-extension build deps
#   curl/wget                        -- download Neo4j & Qdrant
#   default-jre-headless             -- Neo4j requires a JRE
# ------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    gcc g++ build-essential libffi-dev python3-dev curl wget \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------
# Process supervisor
# ------------------------------------------------------------------
RUN pip install supervisor

# ------------------------------------------------------------------
# Neo4j 5.26.6 (community edition)
# ------------------------------------------------------------------
#   Disables auth for simplicity (single-user local setup).
#   Override via NEO4J_AUTH env-var if needed.
# ------------------------------------------------------------------
RUN wget -q https://dist.neo4j.org/neo4j-community-5.26.6-unix.tar.gz \
    && tar -xzf neo4j-community-5.26.6-unix.tar.gz \
    && mv neo4j-community-5.26.6 /opt/neo4j \
    && rm neo4j-community-5.26.6-unix.tar.gz
ENV NEO4J_HOME=/opt/neo4j
RUN ln -s /opt/neo4j/bin/neo4j /usr/bin/neo4j
RUN echo "dbms.security.auth_enabled=false" >> /opt/neo4j/conf/neo4j.conf

# ------------------------------------------------------------------
# Qdrant v1.15.3 (vector database)
# ------------------------------------------------------------------
RUN wget -q https://github.com/qdrant/qdrant/releases/download/v1.15.3/qdrant-aarch64-unknown-linux-musl.tar.gz \
    && tar -xzf qdrant-aarch64-unknown-linux-musl.tar.gz \
    && mv qdrant /usr/local/bin/qdrant \
    && rm qdrant-aarch64-unknown-linux-musl.tar.gz \
    && mkdir -p /qdrant/storage

WORKDIR /app

# ------------------------------------------------------------------
# MemOS application (installed from PyPI)
# ------------------------------------------------------------------
ENV HF_ENDPOINT=https://hf-mirror.com

RUN pip install --upgrade pip \
    && pip install --no-cache-dir MemoryOS==2.0.17 "qdrant-client~=1.15.0" langchain-text-splitters neo4j chonkie jieba redis cachetools "rank-bm25" pika

# Ports: 8000 (API) | 7474 (Neo4j HTTP) | 7687 (Neo4j Bolt)
#        6333 (Qdrant HTTP) | 6334 (Qdrant gRPC)
EXPOSE 8100 7474 7687 6333 6334

# ------------------------------------------------------------------
# Supervisor config + entrypoint
# ------------------------------------------------------------------
COPY supervisord.conf /etc/supervisord.conf
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
