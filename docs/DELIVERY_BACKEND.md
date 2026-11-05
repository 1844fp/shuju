# Backend delivery

Implemented in backend/app.py and backend/test_backend.py:
- Optional FINAGENT_API_TOKEN Bearer authentication; FINAGENT_API_ROLE=reader rejects writes, admin default. No token retains local demo compatibility.
- Client organization header/query overrides rejected. This remains a single organization database, not tenant isolation.
- Structured request validation and storage dependency errors; malformed XLSX rejected as validation error.
- POST /api/v1/reports returns 202 task_id; GET /api/v1/reports/{task_id} returns persisted completed deterministic Markdown report. GET reports remains compatible.
- POST analysis remains truthful 503 model_not_configured; GET analysis/{task_id} returns 404 because no model jobs exist.

Actual validation on 2026-11-04: PYTHONPATH set to shared work/runtime; python backend/test_backend.py: 3 passed; python tests/test_finance.py: 8 passed. Sandbox dependency access initially failed, elevated test execution succeeded. Existing port 8000 service was not restarted. Tests use temporary SQLite databases.

Remaining integration: HTTP model adapter and actual analysis jobs are not implemented; no multi-tenant schema/RBAC or production authentication provider; ready checks current batch table rather than PostgreSQL migration ledger; report tasks have no retention cleanup. Runtime environment role/token values are read per request. Coordinate database migrations before enabling PostgreSQL: existing SQLite-compatible view creation is unchanged. No other role files or test_finance.py modified.
