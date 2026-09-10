"""Forward-only schema migrations (NFR-33).

Applies every `migrations/*.sql` not yet recorded, in filename order, each in its own transaction
together with its tracking row. Applied files are checksummed: forward-only means an applied
migration is never edited, and the only way to enforce that is to notice.

There is no downgrade path, by design. A mistake is corrected by a new migration.

Usage:  py -3 db/migrate.py            apply pending migrations
        py -3 db/migrate.py --status   list applied and pending, change nothing
        py -3 db/migrate.py --selftest run the self-check against a scratch database
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

DSN = os.environ.get("DATABASE_URL", "postgresql://nova:nova@127.0.0.1:5432/nova")
MIGRATIONS = Path(__file__).parent / "migrations"
LOCK_KEY = 0x4E4F5641  # "NOVA". Any concurrent runner waits rather than racing.

TRACKING = """
CREATE TABLE IF NOT EXISTS schema_migration (
    version    text PRIMARY KEY,
    checksum   text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


class MigrationError(RuntimeError):
    pass


def discover() -> list[Path]:
    files = sorted(MIGRATIONS.glob("*.sql"), key=lambda p: p.name)
    if not files:
        raise MigrationError(f"no migrations found in {MIGRATIONS}")
    return files


def _recorded(conn: psycopg.Connection[Any]) -> dict[str, str]:
    return dict(conn.execute("SELECT version, checksum FROM schema_migration").fetchall())


def count(conn: psycopg.Connection[Any], sql: str) -> int:
    row = conn.execute(sql).fetchone()
    assert row is not None
    return int(row[0])


def checksum(path: Path) -> str:
    # Text mode with a normalized line ending: the repository is checked out with LF, but a Windows
    # editor that rewrites the file as CRLF must not read as a tampered migration.
    return hashlib.sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode()).hexdigest()


def apply(dsn: str = DSN, quiet: bool = False) -> list[str]:
    """Apply pending migrations. Returns the versions applied by this call."""
    say = (lambda *a: None) if quiet else print
    applied_now: list[str] = []

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(TRACKING)
        conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
            recorded = _recorded(conn)

            for path in discover():
                version, digest = path.stem, checksum(path)

                if version in recorded:
                    if recorded[version] != digest:
                        raise MigrationError(
                            f"{version} was applied as {recorded[version][:12]} but the file now "
                            f"hashes to {digest[:12]}. Migrations are forward-only: restore the "
                            f"file and correct it in a new migration."
                        )
                    continue

                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute(
                        "INSERT INTO schema_migration (version, checksum) VALUES (%s, %s)",
                        (version, digest),
                    )
                applied_now.append(version)
                say(f"  applied  {version}")
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))

    say(f"{len(applied_now)} applied, database up to date" if applied_now else "already up to date")
    return applied_now


def status(dsn: str = DSN) -> int:
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(TRACKING)
        recorded = _recorded(conn)
    pending = 0
    for path in discover():
        version = path.stem
        if version not in recorded:
            print(f"  pending  {version}")
            pending += 1
        elif recorded[version] != checksum(path):
            print(f"  ALTERED  {version}  (applied checksum does not match the file)")
            pending += 1
        else:
            print(f"  applied  {version}")
    return pending


def selftest(dsn: str = DSN) -> None:
    """Apply the real migrations to a scratch database, twice, then tamper with the record.

    Needs a reachable server. It creates and drops its own database and touches nothing else.
    """
    scratch = "nova_migrate_selftest"
    admin = psycopg.connect(dsn, autocommit=True)
    with admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{scratch}"')
    scratch_dsn = psycopg.conninfo.make_conninfo(dsn, dbname=scratch)

    try:
        first = apply(scratch_dsn, quiet=True)
        assert first, "first run applied nothing"

        second = apply(scratch_dsn, quiet=True)
        assert second == [], f"second run was not a no-op: {second}"

        with psycopg.connect(scratch_dsn, autocommit=True) as conn:
            assert count(conn, "SELECT count(*) FROM tenant") == 1, "tenant missing"
            assert count(conn, "SELECT count(*) FROM pg_extension WHERE extname = 'vector'") == 1, (
                "vector extension missing"
            )

            # An applied migration whose file has changed must stop the run, not be re-applied.
            conn.execute(
                "UPDATE schema_migration SET checksum = 'tampered' WHERE version = %s", (first[0],)
            )
        try:
            apply(scratch_dsn, quiet=True)
        except MigrationError as exc:
            assert "forward-only" in str(exc), f"wrong error: {exc}"
        else:
            raise AssertionError("a checksum mismatch was not detected")

        print(f"selftest ok: {len(first)} migration(s) applied, idempotent, tampering detected")
    finally:
        with psycopg.connect(dsn, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{scratch}" WITH (FORCE)')


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if arg == "--selftest":
            selftest()
        elif arg == "--status":
            sys.exit(1 if status() else 0)
        elif arg:
            sys.exit(f"unknown argument: {arg}")
        else:
            apply()
    except (MigrationError, psycopg.Error) as exc:
        sys.exit(f"migration failed: {exc}")
