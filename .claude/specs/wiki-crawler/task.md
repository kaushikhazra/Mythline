# Wiki Crawler Service — Tasks

## 1. Shared Crawl Utilities

- [x] Velasari extracts `CrawlVerdict`, `detect_blocked_content`, `DomainThrottle` from `a_world_lore_researcher/src/mcp_client.py` to `shared/crawl.py` — _WC-3, D5_
- [x] Velasari updates `a_world_lore_researcher/src/mcp_client.py` to import from `shared.crawl` — _D5_
- [x] Velasari runs WLR `test_mcp_client.py` to verify no regressions — _D5_

## 2. Storage MCP Extensions

- [x] Velasari adds `crawl_zone`, `crawl_page`, `crawl_domain` to `VALID_TABLES` in `mcp_storage/src/server.py` — _WC-5, D3_
- [x] Velasari adds `has_page`, `connected_to`, `links_to`, `from_domain` to `VALID_RELATIONS` in `mcp_storage/src/server.py` — _WC-5, D3_
- [x] Velasari adds crawl table and relation schema statements to `mcp_storage/src/schema.py` — _WC-5, D2_

## 3. Service Scaffolding, Models, and Config

- [x] Velasari creates `s_wiki_crawler/` folder structure (src/, config/, tests/, conftest.py, pyproject.toml, Dockerfile, .env.example) — _D1_
- [x] Velasari creates `config/crawl_scope.yml` with category definitions and search templates — _WC-2_
- [x] Velasari copies `config/sources.yml` from WLR with source tier definitions — _WC-2, D9_
- [x] Velasari implements `src/models.py` with all Pydantic models (CrawlJob, CrawlScope, PageMetadata, graph records, pipeline types) — _WC-1, WC-2, WC-4, WC-5_
- [x] Velasari implements `src/config.py` with env vars, YAML loaders, and domain tier lookup — _WC-2_
- [x] Velasari creates `tests/test_models.py` and `tests/test_config.py` with validation and loader tests — _WC-1, WC-2_

## 4. Crawler Module

- [x] Velasari implements `search_for_category` in `src/crawler.py` (Web Search MCP calls with query templates) — _WC-3_
- [x] Velasari implements `select_urls` with domain tier ranking and pattern filtering — _WC-2, WC-3_
- [x] Velasari implements `crawl_page` with crawl4ai `/crawl` endpoint, block detection, and circuit breaker — _WC-3, D6_
- [x] Velasari implements `_extract_internal_links` for sub-page discovery — _WC-3_
- [x] Velasari implements `extract_connected_zones` with regex patterns on markdown — _WC-6, D10_
- [x] Velasari creates `tests/test_crawler.py` covering URL selection, pattern filtering, block detection, link extraction, zone discovery — _WC-3, WC-6_

## 5. Storage Module

- [x] Velasari implements `store_page` in `src/storage.py` (filesystem write + sidecar + graph) — _WC-4, WC-5_
- [x] Velasari implements `store_page_with_change_detection` for refresh cycles — _WC-7_
- [x] Velasari implements `_url_to_slug` and `_url_to_record_id` helpers — _WC-4_
- [x] Velasari creates `tests/test_storage.py` covering filesystem writes, sidecar metadata, slug generation, change detection — _WC-4, WC-7_

## 6. Daemon

- [x] Velasari implements `CrawlerDaemon` class in `src/daemon.py` with RabbitMQ connection and queue declaration — _WC-1_
- [x] Velasari implements `_process_seed` with message parsing, freshness check, and zone crawl — _WC-1, WC-3_
- [x] Velasari implements `_refresh_oldest_zone` for round-robin refresh mode — _WC-7_
- [x] Velasari implements `_crawl_zone` orchestrating the per-zone crawl pipeline — _WC-3, WC-4, WC-5_
- [x] Velasari implements `_discover_and_publish_connected_zones` with queue publishing — _WC-6_
- [x] Velasari implements `src/logging_config.py` with structured JSON logging — _WC-8_
- [x] Velasari creates `tests/test_daemon.py` covering message parsing, freshness, crawl orchestration, zone publishing, error handling — _WC-1, WC-6, WC-7_

## 7. Docker Integration

- [x] Velasari adds `wiki-crawler` service to `docker-compose.yml` with volume, depends_on, and env vars — _D1_
- [x] Velasari runs full test suite across wiki-crawler, WLR, and Storage MCP — verifies no regressions — _WC-1 through WC-8_
