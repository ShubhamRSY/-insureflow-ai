#!/usr/bin/env python3
"""Create or refresh the Rytera master admin (CUO + enterprise tier).

Reads credentials from environment variables (never commit passwords):

  BOOTSTRAP_ADMIN_USERNAME   default: Shubham
  BOOTSTRAP_ADMIN_EMAIL      default: shubham@ryterainc.com
  BOOTSTRAP_ADMIN_PASSWORD     required
  BOOTSTRAP_ADMIN_FULL_NAME  default: Shubham yedekar
  BOOTSTRAP_ADMIN_COMPANY    default: Rytera

Usage:
  BOOTSTRAP_ADMIN_PASSWORD='...' python scripts/bootstrap_master_admin.py
  BOOTSTRAP_ADMIN_PASSWORD='...' python scripts/bootstrap_master_admin.py --force
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from insureflow.auth import Role  # noqa: E402
from insureflow.auth.jwt import hash_password  # noqa: E402
from insureflow.auth.models import User  # noqa: E402
from insureflow.auth.store import PostgresUserStore, get_user_store  # noqa: E402
from insureflow.auth.validation import validate_password, validate_username  # noqa: E402
from insureflow.pricing.engine import PricingEngine  # noqa: E402


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def bootstrap(*, force: bool) -> int:
    username = _env("BOOTSTRAP_ADMIN_USERNAME", "Shubham")
    email = _env("BOOTSTRAP_ADMIN_EMAIL", "shubham@ryterainc.com")
    password = _env("BOOTSTRAP_ADMIN_PASSWORD")
    full_name = _env("BOOTSTRAP_ADMIN_FULL_NAME", "Shubham yedekar")
    company_name = _env("BOOTSTRAP_ADMIN_COMPANY", "Rytera")

    if not password:
        print("ERROR: set BOOTSTRAP_ADMIN_PASSWORD", file=sys.stderr)
        return 1

    username_check = validate_username(username)
    password_check = validate_password(password)
    if not username_check.valid or not password_check.valid:
        errors = username_check.errors + password_check.errors
        print("ERROR:", "; ".join(errors), file=sys.stderr)
        return 1

    store = get_user_store()
    existing = store.get(username)
    if existing and not force:
        print(f"User '{username}' already exists. Re-run with --force to update password and role.")
        return 1

    org_id = "rytera"
    if isinstance(store, PostgresUserStore) and company_name:
        created = store.get_or_create_org(company_name)
        if created:
            org_id = created

    store[username] = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=Role.CUO,
        full_name=full_name,
        org_id=org_id,
        company_name=company_name,
    )

    upgrade = PricingEngine().upgrade_tier(org_id, "enterprise")
    if upgrade.get("error"):
        print("WARNING: pricing tier upgrade failed:", upgrade["error"], file=sys.stderr)
    else:
        print(f"Pricing tier: {upgrade.get('previous_tier')} -> {upgrade.get('new_tier')}")

    print(f"Master admin ready: username={username!r} email={email!r} role=cuo org={org_id!r}")
    print("Log in at /dashboard — logged-in users bypass the free preview banner.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap Rytera master admin (CUO + enterprise).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update password/role if the user already exists",
    )
    args = parser.parse_args()
    raise SystemExit(bootstrap(force=args.force))


if __name__ == "__main__":
    main()
