"""Start an embedded PostgreSQL server without Docker or sudo.

Uses the `pgserver` package, which bundles PostgreSQL binaries. Handy in
environments where Docker/apt are unavailable but you still want to test the
real PostgreSQL code path (JSONB, PL/pgSQL audit trigger, partial indexes).

Usage:
    python scripts/dev_db.py            # start (keeps running after script exits)
    python scripts/dev_db.py --stop     # stop the embedded server

Then export the printed URL, e.g.:
    export DATABASE_URL='postgresql+psycopg://postgres@/postgres?host=/abs/path/.devdata/pgdata'
    cd backend && alembic upgrade head

Requires: pip install pgserver psycopg[binary]   (Python <= 3.12)
"""
from __future__ import annotations

import argparse
import pathlib
import sys

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / ".devdata" / "pgdata"


def main() -> int:
    parser = argparse.ArgumentParser(description="Embedded PostgreSQL helper")
    parser.add_argument("--stop", action="store_true", help="stop the embedded server")
    parser.add_argument("--data", default=str(DATA_DIR), help="data directory")
    args = parser.parse_args()

    try:
        import pgserver
    except ImportError:
        print(
            "pgserver is not installed.\n"
            "  uv pip install pgserver 'psycopg[binary]'   (needs Python <= 3.12)",
            file=sys.stderr,
        )
        return 1

    data = pathlib.Path(args.data)
    if args.stop:
        server = pgserver.get_server(data, cleanup_mode="stop")
        server.cleanup()
        print("embedded postgres stopped")
        return 0

    # cleanup_mode=None leaves the server running after this process exits.
    server = pgserver.get_server(data, cleanup_mode=None)
    uri = server.get_uri()
    # psycopg/SQLAlchemy want the +psycopg driver prefix.
    sqlalchemy_url = uri.replace("postgresql://", "postgresql+psycopg://", 1)
    print("embedded PostgreSQL is running.")
    print()
    print("  DATABASE_URL=" + sqlalchemy_url)
    print()
    print("export DATABASE_URL='" + sqlalchemy_url + "'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
