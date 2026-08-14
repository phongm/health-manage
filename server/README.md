# 后端服务

Python 3.11 + FastAPI + SQLAlchemy 2（async）+ PostgreSQL。

```bash
cp .env.example .env
uv run alembic upgrade head
uv run python -m app.tools.seed_foods
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8100
uv run pytest
```

接口前缀：`/api/health/v1`，与 Nginx 分流路径一致。健康检查：`GET /healthz`。
