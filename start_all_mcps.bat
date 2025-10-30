@echo off
echo Starting all MCP servers...

start "Web Search MCP" cmd /c "python -m src.mcp_servers.mcp_web_search.server"
start "Web Crawler MCP" cmd /c "python -m src.mcp_servers.mcp_web_crawler.server"
start "Filesystem MCP" cmd /c "python -m src.mcp_servers.mcp_filesystem.server"
start "Knowledge Base MCP" cmd /c "python -m src.mcp_servers.mcp_knowledge_base.server"

echo All MCP servers started in background windows.
pause
