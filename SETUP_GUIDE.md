# Quick Setup Guide

## Prerequisites
- Python 3.10+
- Docker & Docker Compose
- PostgreSQL, Elasticsearch, Redis, Milvus

## Step 1: Start Services

```bash
# Start Redis
cd deploy/redis
docker-compose up -d

# Start Milvus (if needed)
cd ../milvus
docker-compose up -d

# Start PostgreSQL & Elasticsearch
# (adjust based on your setup)
```

## Step 2: Configure Environment

Create `.env` file:
```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_DB=shop_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432

# Elasticsearch
ELASTIC_HOST=localhost
ELASTIC_PORT=9200

# Redis (NEW!)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Milvus
MILVUS_HOST=localhost:19530
MILVUS_USER=root
MILVUS_PASSWORD=Milvus
```

## Step 3: Initialize Database

```bash
# Run init script (includes timestamps)
psql -U postgres -d shop_db -f deploy/db_es_redis/init_db.sql
```

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 5: Start MCP Server

```bash
# Start salesperson MCP server (with auto-sync)
python -m src.my_mcp.salesperson.server_salesperson_tool
```

## Verify Setup

```python
# Test connections
python -c "
from src.data.postgres.connection import db_connection
from src.data.elasticsearch.connection import es_connection
from src.data.redis.connection import redis_connection

print('PostgreSQL:', 'OK' if db_connection.get_session() else 'FAIL')
print('Elasticsearch:', 'OK' if es_connection.get_client().ping() else 'FAIL')
print('Redis:', 'OK' if redis_connection.health_check() else 'FAIL')
"

# Test sync
python -c "
from src.data.elasticsearch.sync import sync_products_to_elastic, get_sync_statistics

sync_products_to_elastic()
print(get_sync_statistics())
"
```

## Common Commands

```bash
# Force full resync
python -c "from src.data.elasticsearch.sync import force_full_resync; force_full_resync()"

# Clear Redis sync state
python -c "from src.data.redis.sync_tracker import clear_sync_state; clear_sync_state()"

# Check sync stats
python -c "from src.data.elasticsearch.sync import get_sync_statistics; print(get_sync_statistics())"
```

## Troubleshooting

### Redis not connecting
```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli ping
```

### Database not initialized
```bash
# Check if tables exist
psql -U postgres -d shop_db -c "\dt"

# Re-run init if needed
psql -U postgres -d shop_db -f deploy/db_es_redis/init_db.sql
```

### Sync issues
```bash
# Clear and resync
python -c "
from src.data.redis.sync_tracker import clear_sync_state
from src.data.elasticsearch.sync import force_full_resync

clear_sync_state()
force_full_resync()
"
```

## What's Next?

- Read `DATA_REFACTOR_REDIS_COMPLETE.md` for detailed architecture
- Check logs for sync status
- Monitor Redis with `redis-cli monitor`
- Enjoy 40-50x faster syncs! 🚀
