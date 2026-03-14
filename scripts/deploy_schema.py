"""Deploy database schema to Supabase.

Usage:
    python scripts/deploy_schema.py

Reads the SQL migration file and executes it against your Supabase project.
You can also copy/paste the SQL into the Supabase SQL Editor in the dashboard.
"""

import sys
from pathlib import Path


def deploy() -> None:
    """Read and print all schema migration SQL for deployment."""
    migrations_dir = (
        Path(__file__).parent.parent
        / "packages"
        / "database"
        / "src"
        / "sharpedge_db"
        / "migrations"
    )

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print(f"No migration files found in: {migrations_dir}")
        sys.exit(1)

    print("=" * 60)
    print("SharpEdge Database Schema")
    print("=" * 60)
    print()
    print("Paste each SQL block into the Supabase SQL Editor in order:")
    print("https://supabase.com/dashboard/project/<YOUR_PROJECT>/sql/new")
    print()
    print(f"Migrations to run ({len(migration_files)} total):")
    for i, f in enumerate(migration_files, 1):
        print(f"  {i}. {f.name}")
    print()

    for migration_file in migration_files:
        try:
            sql = migration_file.read_text()
        except PermissionError:
            print(f"ERROR: Cannot read {migration_file.name} (permission denied)")
            sys.exit(1)

        print("=" * 60)
        print(f"Migration: {migration_file.name}")
        print("=" * 60)
        print(sql)
        print()

    print("After running all migrations, verify tables were created in the")
    print(
        "Table Editor: "
        "https://supabase.com/dashboard/project/<YOUR_PROJECT>/editor"
    )


if __name__ == "__main__":
    deploy()
