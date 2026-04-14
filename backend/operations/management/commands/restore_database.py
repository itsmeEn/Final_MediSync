from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connections


class Command(BaseCommand):
    help = "Restore a database backup created by backup_database (SQLite .sqlite3, JSON .json.gz, or PostgreSQL .sql)"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        if not options["force"]:
            raise SystemExit("Refusing to restore without --force (this will overwrite existing data).")

        src = Path(str(options["input"]))
        if not src.exists() or not src.is_file():
            raise SystemExit(f"Input file not found: {src}")

        db = settings.DATABASES.get("default") or {}
        engine = str(db.get("ENGINE") or "")

        if src.suffix == ".sql":
            if "postgresql" not in engine:
                raise SystemExit("SQL restore is only supported for PostgreSQL.")
            self._psql_restore(db, src)
            self.stdout.write(self.style.SUCCESS("Restore completed."))
            return

        if src.suffix == ".sqlite3":
            if "sqlite3" not in engine:
                raise SystemExit("SQLite restore is only supported when DB_ENGINE is sqlite3.")
            self._sqlite_restore(db, src)
            self.stdout.write(self.style.SUCCESS("Restore completed."))
            return

        if src.name.endswith(".json.gz"):
            self._json_restore(src)
            self.stdout.write(self.style.SUCCESS("Restore completed."))
            return

        raise SystemExit("Unsupported input format. Use a .sql or .json.gz backup.")

    def _psql_restore(self, db: dict, src: Path):
        if not shutil.which("psql"):
            raise SystemExit("psql not found in PATH.")

        env = dict(os.environ)
        password = str(db.get("PASSWORD") or "")
        if password:
            env["PGPASSWORD"] = password

        host = str(db.get("HOST") or "")
        port = str(db.get("PORT") or "")
        user = str(db.get("USER") or "")
        name = str(db.get("NAME") or "")

        cmd = ["psql", "--set", "ON_ERROR_STOP=on", "--dbname", name, "--file", str(src)]
        if host:
            cmd.extend(["--host", host])
        if port:
            cmd.extend(["--port", port])
        if user:
            cmd.extend(["--username", user])

        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            msg = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"psql restore failed: {msg}")

    def _json_restore(self, src: Path):
        tmp = src.with_suffix("").with_suffix(".json")
        try:
            with gzip.open(src, "rb") as gz, tmp.open("wb") as out:
                shutil.copyfileobj(gz, out)
            call_command("flush", "--noinput")
            call_command("loaddata", str(tmp))
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _sqlite_restore(self, db: dict, src: Path):
        dst = Path(str(db.get("NAME") or "")).expanduser()
        if not dst:
            raise SystemExit("SQLite DB_NAME is empty.")
        dst.parent.mkdir(parents=True, exist_ok=True)
        connections.close_all()
        shutil.copy2(src, dst)
