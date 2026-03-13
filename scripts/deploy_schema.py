"""Deploy database schema to Supabase.

Usage:
    python scripts/deploy_schema.py

Reads the SQL migration file and executes it against your Supabase project.
You can also copy/paste the SQL into the Supabase SQL Editor in the dashboard.
"""

import os
import sys
from pathlib import Path


def deploy() -> None:
    """Read and print the schema SQL for deployment."""
    migration_path = (
        Path(__file__).parent.parent
        / "packages"
        / "database"
        / "src"
        / "sharpedge_db"
        / "migrations"
        / "001_initial_schema.sql"
    )

    if not migration_path.exists():
        print(f"Migration file not found: {migration_path}")
        sys.exit(1)

    sql = migration_path.read_text()

    print("=" * 60)
    print("SharpEdge Database Schema")
    print("=" * 60)
    print()
    print("Copy the SQL below and paste it into the Supabase SQL Editor:")
    print("https://supabase.com/dashboard/project/YOUR_PROJECT/sql/new")
    print()
    print("-" * 60)
    print(sql)
    print("-" * 60)
    print()
    print("After running the SQL, verify tables were created in the")
    print("Table Editor: https://supabase.com/dashboard/project/YOUR_PROJECT/editor")


if __name__ == "__main__":
    deploy()
