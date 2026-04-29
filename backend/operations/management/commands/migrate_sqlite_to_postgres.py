from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from subprocess import run

from django.conf import settings
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Migrate data from SQLite to PostgreSQL using dumpdata/loaddata via backup_database + restore_database"

    def add_arguments(self, parser):
        parser.add_argument("--sqlite-name", default="", help="Path to SQLite database file (defaults to BASE_DIR/db.sqlite3)")
        parser.add_argument("--output-dir", default="", help="Directory to write the intermediate backup (defaults to BASE_DIR/backups)")
        parser.add_argument("--postgres-name", default="", help="PostgreSQL database name (optional; otherwise uses existing env DB_NAME)")
        parser.add_argument("--postgres-host", default="", help="PostgreSQL host (optional; otherwise uses existing env DB_HOST)")
        parser.add_argument("--postgres-port", default="", help="PostgreSQL port (optional; otherwise uses existing env DB_PORT)")
        parser.add_argument("--postgres-user", default="", help="PostgreSQL user (optional; otherwise uses existing env DB_USER)")
        parser.add_argument("--postgres-password", default="", help="PostgreSQL password (optional; otherwise uses existing env DB_PASSWORD)")

    def handle(self, *args, **options):
        sqlite_name_raw = str(options.get("sqlite_name") or "").strip()
        sqlite_name = Path(sqlite_name_raw) if sqlite_name_raw else Path(settings.BASE_DIR) / "db.sqlite3"

        if not sqlite_name.exists():
            raise SystemExit(f"SQLite database not found: {sqlite_name}")

        out_dir_raw = str(options.get("output_dir") or "").strip()
        out_dir = Path(out_dir_raw) if out_dir_raw else Path(settings.BASE_DIR) / "backups"
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        marker = f"migrate_sqlite_to_postgres_{ts}"

        manage_py = Path(settings.BASE_DIR).parent / "manage.py"
        if not manage_py.exists():
            manage_py = Path(settings.BASE_DIR) / "manage.py"
        if not manage_py.exists():
            raise SystemExit("manage.py not found; run this from the project root environment.")

        env_sqlite = dict(os.environ)
        env_sqlite["DB_ENGINE"] = "sqlite"
        env_sqlite["DB_NAME"] = str(sqlite_name)

        self.stdout.write("Step 1/3: Exporting SQLite data to JSON backup…")
        before = set(p.name for p in out_dir.glob("medisync_backup_*.json.gz"))
        res = run([sys.executable, str(manage_py), "backup_database", "--format=json", "--output-dir", str(out_dir)], env=env_sqlite)
        if res.returncode != 0:
            raise SystemExit("SQLite export failed.")

        after = sorted([p for p in out_dir.glob("medisync_backup_*.json.gz") if p.name not in before], key=lambda p: p.stat().st_mtime)
        if not after:
            raise SystemExit("No backup file produced.")
        backup_path = after[-1]
        renamed = out_dir / f"{marker}.json.gz"
        backup_path.rename(renamed)

        env_pg = dict(os.environ)
        env_pg["DB_ENGINE"] = "postgres"
        if options.get("postgres_name"):
            env_pg["DB_NAME"] = str(options["postgres_name"])
        if options.get("postgres_host"):
            env_pg["DB_HOST"] = str(options["postgres_host"])
        if options.get("postgres_port"):
            env_pg["DB_PORT"] = str(options["postgres_port"])
        if options.get("postgres_user"):
            env_pg["DB_USER"] = str(options["postgres_user"])
        if options.get("postgres_password"):
            env_pg["DB_PASSWORD"] = str(options["postgres_password"])

        self.stdout.write("Step 2/3: Ensuring PostgreSQL schema is migrated…")
        res = run([sys.executable, str(manage_py), "migrate", "--noinput"], env=env_pg)
        if res.returncode != 0:
            raise SystemExit("PostgreSQL migrate failed.")

        self.stdout.write("Step 3/3: Importing JSON backup into PostgreSQL…")
        res = run([sys.executable, str(manage_py), "restore_database", "--input", str(renamed), "--force"], env=env_pg)
        if res.returncode != 0:
            raise SystemExit("PostgreSQL import failed.")

        self.stdout.write(self.style.SUCCESS(f"Migration completed. Backup used: {renamed}"))

