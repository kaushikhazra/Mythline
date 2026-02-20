# Docker MCP Integration Research

**Date:** 2026-02-21
**Status:** Research Complete

---

## 1. Docker MCP Catalog / Registry

### What Is It?

The Docker MCP Catalog is a curated, verified registry of MCP servers packaged and distributed as Docker container images via Docker Hub under the `mcp/` namespace. It hosts 200+ containerized MCP servers from partners including New Relic, Stripe, Grafana, and others.

The Docker MCP ecosystem has **three core components**:

1. **MCP Catalog** - A curated collection of verified MCP servers as container images on Docker Hub, with versioning, provenance, SBOM metadata, and continuous security maintenance.
2. **MCP Toolkit** - A GUI within Docker Desktop for discovering, configuring, and managing MCP servers through a unified interface.
3. **MCP Gateway** - The open-source foundation that manages MCP containers and provides a single endpoint exposing enabled servers to multiple AI applications.

### How Discovery Works

- Browse via Docker Desktop MCP Toolkit UI
- Search Docker Hub under `mcp/` namespace
- CLI: `docker mcp server enable <server-name>`
- Each catalog entry includes tool descriptions, version history, available tools, and agent integration configs

### Server Types in Catalog

- **Local servers** - Containerized apps running on host machine, signed by Docker, work offline (whale icon)
- **Remote servers** - Hosted services connecting to external platforms (GitHub, Notion, Linear), many use OAuth (cloud icon)

### Registering Custom MCP Servers

Two submission paths to the official registry (`github.com/docker/mcp-registry`):

**Option A: Docker-Built Images (Recommended)**
- Submit metadata via PR, Docker handles build/sign/publish
- Published to `mcp/your-server-name` on Docker Hub
- Includes cryptographic signatures, provenance, SBOMs
- Available within 24 hours of approval

**Option B: Self-Provided Pre-Built Images**
- Provide pre-built container image directly
- Benefits from container isolation but lacks Docker's enhanced security features

### Private/Enterprise Catalogs

Organizations can build custom private catalogs:
1. Fork Docker's MCP Catalog repo
2. Host images in private registry
3. Publish a private catalog with your own servers
4. Expose via MCP Gateway with controlled access
- Catalogs are OCI artifacts - image scanning, Cosign signing, and registry access controls all work natively
- Harbor, Artifactory, and other registries support this

---

## 2. Docker MCP Toolkit

### What It Is

Management interface integrated into Docker Desktop that lets you set up, manage, and run containerized MCP servers and connect them to AI agents. Free feature in Docker Desktop.

### How It Works

- Docker packages MCP servers as containers, eliminating isolation and environment difference issues
- No dependency management, runtime configuration, or manual setup required
- MCP tools run either within the same container as the server or in dedicated containers for better isolation

### Setup Steps

1. Install latest Docker Desktop
2. Settings > Beta features > Enable Docker MCP Toolkit
3. Open MCP Toolkit, browse Catalog tab
4. Add servers (click + icon) or CLI: `docker mcp server enable <name>`
5. Complete OAuth authentication if needed

### Client Connection

Supported clients: Claude Desktop, Claude Code, VS Code Copilot, Cursor, Gemini, Continue, and others.

Connection methods:
- **Docker Desktop Clients tab** - GUI configuration
- **CLI**: `docker mcp gateway run` - starts the gateway for external clients
- **Claude Code**: verify with `claude mcp list` to confirm "MCP_DOCKER" server
- **VS Code**: via `.vscode/mcp.json` or global user settings

### Security

- All images under `mcp/` are built by Docker and digitally signed
- Include SBOM for full transparency
- MCP tools run in their own container restricted to 1 CPU
- Resource limits prevent computing resource misuse

---

## 3. Docker MCP Gateway

### Architecture

```
AI Client --> MCP Gateway --> MCP Server Containers
   (stdio/SSE/streaming)    (isolated Docker containers)
```

The Gateway acts as a centralized proxy between clients and servers, managing configuration, credentials, and access control.

### Lifecycle Management

When an AI app needs a tool:
1. Request sent to Gateway
2. Gateway identifies which server handles the tool
3. If server not running, starts it as a Docker container
4. Injects required credentials, applies security restrictions
5. Forwards request to server
6. Returns result through Gateway to AI app

### Supported Transports

- **stdio** - Standard I/O (single client, default, port 8811)
- **streaming** - TCP-based (multiple clients, `--transport streaming --port 8811`)
- **SSE** - Server-Sent Events (multiple clients, `--transport sse --port 8811`)

### Docker Compose Configuration

Minimal setup:
```yaml
services:
  gateway:
    image: docker/mcp-gateway
    command:
      - --servers=duckduckgo
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "8811:8811"
```

Agent connecting to gateway:
```yaml
services:
  client:
    build: .
    environment:
      - MCP_HOST=http://gateway:8811/mcp
    depends_on:
      - gateway
  gateway:
    image: docker/mcp-gateway
    command:
      - --servers=duckduckgo
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    ports:
      - "8811:8811"
```

### Container Security Constraints

Gateway automatically applies to spawned MCP containers:
- `--security-opt no-new-privileges`
- `--cpus 1`
- `--memory 2Gb`

### Secrets Management

```yaml
services:
  gateway:
    command:
      - --secrets=docker-desktop:/run/secrets/mcp_secret
    secrets:
      - mcp_secret
secrets:
  mcp_secret:
    file: .env
```

### Configuration Files

Located in `~/.docker/mcp/`:
- `docker-mcp.yaml` - Server catalog definitions
- `registry.yaml` - Enabled servers list
- `config.yaml` - Per-server runtime settings
- `tools.yaml` - Enabled tools per server

### Production Configuration

```yaml
command:
  - --catalog=/mcp/catalogs/docker-mcp.yaml
  - --config=/mcp/config.yaml
  - --registry=/mcp/registry.yaml
  - --secrets=docker-desktop
  - --watch=true      # live config reload
  - --transport=sse
  - --port=8080
```

### Docker-in-Docker (CI/CD)

```yaml
services:
  gateway:
    image: docker/mcp-gateway:dind
    privileged: true
    ports:
      - "8080:8080"
    command:
      - --transport=sse
      - --servers=fetch
      - --memory=512Mb
```

---

## 4. Pydantic AI + Docker MCP Integration

### Connection Methods

Pydantic AI supports three MCP connection transports:

1. **MCPServerStreamableHTTP** (Recommended for containerized servers)
   ```python
   from pydantic_ai.mcp import MCPServerStreamableHTTP
   server = MCPServerStreamableHTTP('http://localhost:8000/mcp')
   ```

2. **MCPServerSSE** (Deprecated, use Streamable HTTP instead)
   ```python
   from pydantic_ai.mcp import MCPServerSSE
   server = MCPServerSSE('http://localhost:3001/sse')
   ```

3. **MCPServerStdio** (Runs server as subprocess)
   ```python
   from pydantic_ai.mcp import MCPServerStdio
   server = MCPServerStdio('python', args=['mcp_server.py'])
   ```

### Connecting to Docker MCP Gateway

Use MCPServerStdio with socat bridge pattern:
```python
server = MCPServerStdio(
    "docker",
    args=["run", "-i", "--rm", "alpine/socat", "STDIO", "TCP:host.docker.internal:8811"]
)
```

Or directly via Streamable HTTP if gateway exposes HTTP:
```python
server = MCPServerStreamableHTTP('http://localhost:8811/mcp')
```

### Agent Pattern with MCP

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP

server = MCPServerStreamableHTTP('http://mcp-server:8000/mcp')
agent = Agent('openai:gpt-4o', toolsets=[server])

async def main():
    async with agent:
        result = await agent.run('Do something')
        print(result.output)
```

### Key Configuration Options

- **tool_prefix** - Prevents naming conflicts: `MCPServerStreamableHTTP('url', tool_prefix='weather')`
- **client_info** - Implementation metadata identifying your app
- **http_client** - Custom httpx.AsyncClient for TLS/SSL, mTLS, proxy
- **allow_sampling** - Controls server's ability to make LLM calls through client
- **load_mcp_servers('mcp_config.json')** - Load from JSON config with env var expansion

### Important: MCPServerStreamableHTTP requires the MCP server to already be running and accepting HTTP connections before the agent starts. Pydantic AI does not manage the server lifecycle.

### Container-to-Container Connection

When both agent and MCP server are in Docker:
```yaml
services:
  agent:
    build: ./agent
    environment:
      - MCP_SERVER_URL=http://mcp-server:8000/mcp
    depends_on:
      - mcp-server
  mcp-server:
    build: ./mcp-server
    ports:
      - "8000:8000"
```

Agent code uses Docker service name as hostname:
```python
server = MCPServerStreamableHTTP('http://mcp-server:8000/mcp')
```

---

## 5. FastMCP Server Containerization

### Dockerfile Pattern

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "server"]
```

### FastMCP HTTP Server

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP(name="My Server", port=8000)

@server.tool()
async def my_tool(query: str) -> str:
    return f"Result for {query}"

# Health check endpoint
@server.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy"})

if __name__ == '__main__':
    server.run(transport='streamable-http', host='0.0.0.0', port=8000)
```

### Transport Options for Docker

- **streamable-http** (Recommended) - `server.run(transport='streamable-http', host='0.0.0.0', port=8000)`
- **sse** - `server.run(transport='sse', host='0.0.0.0', port=8000)`
- Must bind to `0.0.0.0` not `localhost` inside container

### Production with Uvicorn

```python
app = server.http_app(path="/mcp")
# Run: uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Stateless Mode for Horizontal Scaling

```python
server = FastMCP("Server", stateless_http=True)
```
Eliminates session affinity requirements behind load balancers.

---

## 6. Docker Compose Best Practices for Multiple MCP Servers

### Multi-Service Configuration

```yaml
services:
  mcp-web-search:
    build: ./mcp_servers/web_search
    ports:
      - "8000:8000"
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  mcp-knowledge-base:
    build: ./mcp_servers/knowledge_base
    ports:
      - "8003:8003"
    depends_on:
      qdrant:
        condition: service_healthy
    networks:
      - mcp-network

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - mcp-network

  agent:
    build: ./agent
    environment:
      - MCP_WEB_SEARCH_URL=http://mcp-web-search:8000/mcp
      - MCP_KB_URL=http://mcp-knowledge-base:8003/mcp
    depends_on:
      mcp-web-search:
        condition: service_healthy
      mcp-knowledge-base:
        condition: service_healthy
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge

volumes:
  qdrant_data:
```

### Best Practices Summary

1. **Use specific version tags** - Never `latest` in production
2. **Lean base images** - Alpine or slim variants
3. **Non-root users** - Run as unprivileged user
4. **Health checks** - On every service
5. **Secrets management** - Docker secrets, not env vars in production
6. **Named networks** - Explicit network definitions
7. **Resource limits** - CPU and memory constraints
8. **depends_on with condition** - Use `service_healthy` not just `service_started`
9. **Bind to 0.0.0.0** - Inside containers, never localhost
10. **Service name as hostname** - Containers reference each other by service name on shared network

---

## 7. Agent Container to MCP Container Networking

### Docker Internal Networking

On a shared Docker network, containers resolve each other by service name:
- Agent at `agent` connects to `http://mcp-server:8000/mcp`
- No port mapping needed for inter-container communication
- Only expose ports externally if needed for debugging

### Connection Patterns

**Pattern 1: Direct Streamable HTTP**
Agent directly connects to each MCP server via HTTP.
```
Agent Container --> http://mcp-web-search:8000/mcp
                --> http://mcp-kb:8003/mcp
                --> http://mcp-filesystem:8002/mcp
```

**Pattern 2: Via MCP Gateway**
Agent connects to single gateway, gateway routes to MCP servers.
```
Agent Container --> http://gateway:8811/mcp --> MCP Server Containers
```

**Pattern 3: Stdio via socat bridge**
For clients that only support stdio transport.
```
Agent --> docker run socat STDIO TCP:gateway:8811
```

### host.docker.internal

When agent runs on host (not containerized) and MCP servers are in containers:
- Use `localhost:<exposed-port>` from host
- Use `host.docker.internal` from inside a container to reach host services

---

## 8. Relevance to Mythline

### Current Architecture

Mythline currently runs MCP servers as local processes:
- mcp_web_search (port 8000)
- mcp_web_crawler (port 8001)
- mcp_filesystem (port 8002)
- mcp_knowledge_base (port 8003)

### Potential Dockerization Path

1. **Containerize each MCP server** using FastMCP Dockerfile pattern
2. **Use Docker Compose** to orchestrate all MCP servers + Qdrant
3. **Agent code change**: Update `mcp_config.json` URLs from `localhost` to Docker service names
4. **Two deployment modes**:
   - Development: Agent runs on host, MCP servers in containers (use localhost:<port>)
   - Production: Everything containerized (use service names)
5. **Alternative**: Use Docker MCP Gateway as single proxy point instead of direct connections

### Mythline-Specific Considerations

- Knowledge base MCP depends on Qdrant - already a natural Docker service
- File system MCP needs volume mounts to access story files
- Web search/crawler MCPs are stateless - easy to containerize
- Agent memory files (`.mythline/`) need shared volume or external storage
- Current `start_*.bat` scripts would be replaced by `docker compose up`

---

## Sources

- Docker MCP Catalog and Toolkit Docs: https://docs.docker.com/ai/mcp-catalog-and-toolkit/
- Docker MCP Catalog: https://docs.docker.com/ai/mcp-catalog-and-toolkit/catalog/
- Docker MCP Toolkit: https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/
- Docker MCP Gateway: https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/
- Docker MCP Gateway GitHub: https://github.com/docker/mcp-gateway
- Docker MCP Registry GitHub: https://github.com/docker/mcp-registry
- Docker MCP Best Practices: https://www.docker.com/blog/mcp-server-best-practices/
- Build Custom MCP Catalog: https://www.docker.com/blog/build-custom-mcp-catalog/
- Docker MCP Gateway in Container: https://www.ajeetraina.com/running-docker-mcp-gateway-in-a-docker-container/
- Pydantic AI MCP Client Docs: https://ai.pydantic.dev/mcp/client/
- Pydantic AI MCP Overview: https://ai.pydantic.dev/mcp/overview/
- Pydantic AI MCP API Reference: https://ai.pydantic.dev/api/mcp/
- Pydantic AI + Docker MCP Tutorial: https://blog.syndevs.com/posts/how-to-build-smart-agents-with-docker-mcp-pydantic-ai/
- FastMCP HTTP Deployment: https://gofastmcp.com/deployment/http
- Community MCP Registry: https://github.com/modelcontextprotocol/registry
- Docker MCP AI Agent Setup: https://www.docker.com/blog/docker-mcp-ai-agent-developer-setup/
