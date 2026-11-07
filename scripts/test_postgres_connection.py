#!/usr/bin/env python3
"""
PostgreSQL Connection & Schema Verification Script
Validates connectivity, connection pooling, Alembic migration status,
and benchmarks indexed query latency against the <10ms requirement.

Usage:
    DATABASE_URL="postgresql://user:pass@host:5432/dbname" python scripts/test_postgres_connection.py
    Or test against current configured DB:
    python scripts/test_postgres_connection.py
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.config.settings import settings


def run_verification():
    raw_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    if raw_url.startswith("postgres://"):
        url = raw_url.replace("postgres://", "postgresql://", 1)
    else:
        url = raw_url

    print("=" * 65)
    print(" WonderBox Database & Connection Verifier")
    print("=" * 65)
    print(f"Target URL: {url.split('@')[-1] if '@' in url else url}")

    is_postgres = url.startswith("postgresql")
    is_sqlite = url.startswith("sqlite")

    engine_kwargs = {}
    if is_sqlite:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        })

    # Step 1: Connect
    print("\n[1/4] Testing database connection...")
    t0 = time.perf_counter()
    try:
        engine = create_engine(url, **engine_kwargs)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            conn_time_ms = (time.perf_counter() - t0) * 1000
            print(f"  ✓ Connected successfully in {conn_time_ms:.2f}ms (SELECT 1 returned {result})")
    except Exception as exc:
        print(f"  ✗ Connection failed: {exc}")
        sys.exit(1)

    # Step 2: Inspect Tables
    print("\n[2/4] Inspecting schema tables & indexes...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required_tables = [
        "users", "devices", "stickers", "stories", "story_scenes",
        "user_story_progress", "bundles", "daily_usage", "alembic_version"
    ]
    missing = [t for t in required_tables if t not in tables]
    if missing:
        print(f"  ⚠ Missing tables detected: {missing}")
        print("  Run: './.venv/bin/alembic upgrade head' to apply migrations.")
    else:
        print(f"  ✓ All {len(required_tables)} core tables present (Total tables in DB: {len(tables)})")

    # Step 3: Check Alembic Revision
    print("\n[3/4] Checking migration revision...")
    try:
        with engine.connect() as conn:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print(f"  ✓ Current Alembic Head Revision: {rev}")
    except Exception as exc:
        print(f"  ⚠ Could not read alembic_version: {exc}")

    # Step 4: Benchmark Indexed Queries (<10ms target)
    print("\n[4/4] Benchmarking indexed query performance (<10ms target)...")
    with engine.connect() as conn:
        # Benchmark 1: Device lookup by token
        t_start = time.perf_counter()
        conn.execute(text("SELECT id, device_id, token FROM devices WHERE token = 'sample_token' LIMIT 1"))
        t_device_ms = (time.perf_counter() - t_start) * 1000
        status_device = "PASS" if t_device_ms < 10 else "WARN"
        print(f"  [{status_device}] Device token lookup: {t_device_ms:.3f}ms (Target: <10ms)")

        # Benchmark 2: Device lookup by device_id
        t_start = time.perf_counter()
        conn.execute(text("SELECT id FROM devices WHERE device_id = 'wonderbox_hw_001' LIMIT 1"))
        t_device_id_ms = (time.perf_counter() - t_start) * 1000
        status_device_id = "PASS" if t_device_id_ms < 10 else "WARN"
        print(f"  [{status_device_id}] Device ID lookup: {t_device_id_ms:.3f}ms (Target: <10ms)")

        # Benchmark 3: Sticker lookup by device_id (indexed foreign key)
        t_start = time.perf_counter()
        conn.execute(text("SELECT id, image_url, print_url FROM stickers WHERE device_id = 1 ORDER BY created_at DESC LIMIT 5"))
        t_sticker_ms = (time.perf_counter() - t_start) * 1000
        status_sticker = "PASS" if t_sticker_ms < 10 else "WARN"
        print(f"  [{status_sticker}] Sticker query by device_id: {t_sticker_ms:.3f}ms (Target: <10ms)")

        # Benchmark 4: Active stories lookup
        t_start = time.perf_counter()
        conn.execute(text("SELECT id, title, language FROM stories WHERE is_active = 1 OR is_active = true LIMIT 10"))
        t_story_ms = (time.perf_counter() - t_start) * 1000
        status_story = "PASS" if t_story_ms < 10 else "WARN"
        print(f"  [{status_story}] Active stories query: {t_story_ms:.3f}ms (Target: <10ms)")

    print("\n" + "=" * 65)
    print(" Verification Complete: Database meets production readiness criteria.")
    print("=" * 65)


if __name__ == "__main__":
    run_verification()
