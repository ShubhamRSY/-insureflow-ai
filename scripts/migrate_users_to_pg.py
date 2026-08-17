#!/usr/bin/env python3
"""One-shot migration: Redis/file user store → PostgreSQL.

Usage:
    DATABASE_URL=postgresql://user:pass@localhost:5432/insureflow \
        python -m scripts.migrate_users_to_pg

Reads users from the legacy Redis/file store and inserts them into PostgreSQL.
Organizations are auto-created from unique org_id values.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _load_legacy_users() -> dict[str, dict[str, object]]:
    users: dict[str, dict[str, object]] = {}

    redis_url = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL", "")
    if redis_url and redis_url.startswith("redis"):
        try:
            import redis as _redis

            client = _redis.from_url(redis_url, socket_connect_timeout=3, socket_timeout=3)
            client.ping()
            raw = client.get("rytera:auth:users")
            if raw:
                data = json.loads(raw)
                users.update(data)
                print(f"Loaded {len(data)} users from Redis")
                return users
        except Exception as exc:
            print(f"Redis unavailable: {exc}")

    path = Path.cwd() / ".insureflow" / "auth_users.json"
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        users.update(data)
        print(f"Loaded {len(data)} users from {path}")
    else:
        print(f"No legacy user store found at {path}")

    return users


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Please set it to your PostgreSQL connection string.")
        print("Example: DATABASE_URL=postgresql://user:pass@localhost:5432/insureflow")
        sys.exit(1)

    os.environ["DATABASE_URL"] = database_url

    from insureflow.auth.db import Base, OrgRow, UserRow, get_engine, get_session_factory
    from insureflow.auth.models import User

    engine = get_engine()
    if engine is None:
        print("ERROR: Could not connect to PostgreSQL. Check your DATABASE_URL.")
        sys.exit(1)

    Base.metadata.create_all(engine)
    print("PostgreSQL tables created/verified")

    legacy_users = _load_legacy_users()
    if not legacy_users:
        print("No users to migrate.")
        return

    session_factory = get_session_factory()
    if session_factory is None:
        print("ERROR: Could not create PostgreSQL session.")
        sys.exit(1)

    session = session_factory()
    org_cache: dict[str, str] = {}
    migrated = 0
    skipped = 0

    for username, user_data in legacy_users.items():
        try:
            user = User.model_validate(user_data)
        except Exception as exc:
            print(f"  SKIP {username}: invalid data ({exc})")
            skipped += 1
            continue

        existing = session.query(UserRow).filter(UserRow.username == username).first()
        if existing:
            print(f"  SKIP {username}: already exists in PostgreSQL")
            skipped += 1
            continue

        org_id = None
        org_name = user.org_id or "default"
        if org_name and org_name != "default":
            if org_name in org_cache:
                org_id = org_cache[org_name]
            else:
                org = session.query(OrgRow).filter(OrgRow.name == org_name).first()
                if not org:
                    org = OrgRow(name=org_name)
                    session.add(org)
                    session.flush()
                    print(f"  Created org: {org_name} (id={org.id})")
                org_id = str(org.id)
                org_cache[org_name] = org_id

        row = UserRow(
            username=username,
            email=user.email or "",
            hashed_password=user.hashed_password,
            role=user.role.value,
            org_id=org_id,
            company_name=user.company_name or org_name,
            department=user.department,
            team=user.team,
            office_location=user.office_location,
            disabled=user.disabled,
            full_name=user.full_name or username,
        )
        session.add(row)
        migrated += 1
        print(f"  Migrated: {username} (role={user.role.value}, org={org_name})")

    session.commit()
    session.close()
    print(f"\nMigration complete: {migrated} users migrated, {skipped} skipped")


if __name__ == "__main__":
    main()
