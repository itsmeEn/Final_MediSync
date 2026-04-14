from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Create a database backup (SQLite file copy / PostgreSQL SQL when possible, otherwise JSON dumpdata)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=("auto", "sqlite", "sql", "json"),
            default="auto",
        )
        parser.add_argument(
            "--output-dir",
            default="",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=10,
        )
        parser.add_argument(
            "--exclude",
            action="append",
            default=["contenttypes", "auth.permission", "admin.logentry"],
        )

    def handle(self, *args, **options):
        fmt = options["format"]
        keep = int(options["keep"])
        excludes = list(options["exclude"] or [])

        out_dir_raw = (options.get("output_dir") or "").strip()
        out_dir = Path(out_dir_raw) if out_dir_raw else Path(settings.BASE_DIR) / "backups"
        out_dir.mkdir(parents=True, exist_ok=True)

        db = settings.DATABASES.get("default") or {}
        engine = str(db.get("ENGINE") or "")

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = f"medisync_backup_{ts}"

        if fmt == "auto":
            if "sqlite3" in engine:
                fmt = "sqlite"
            elif "postgresql" in engine and shutil.which("pg_dump"):
                fmt = "sql"
            else:
                fmt = "json"

        if fmt == "sqlite":
            if "sqlite3" not in engine:
                self.stdout.write(self.style.WARNING("SQLite backup requested but engine is not SQLite; falling back to JSON."))
                fmt = "json"
            else:
                src = Path(str(db.get("NAME") or "")).expanduser()
                if not src.exists():
                    self.stdout.write(self.style.WARNING("SQLite database file not found; falling back to JSON."))
                    fmt = "json"
                else:
                    out_path = out_dir / f"{prefix}.sqlite3"
                    shutil.copy2(src, out_path)
                    self.stdout.write(self.style.SUCCESS(f"Backup created: {out_path}"))
                    self._prune(out_dir, keep)
                    return

        if fmt == "sql":
            if "postgresql" not in engine:
                self.stdout.write(self.style.WARNING("SQL backup requested but engine is not PostgreSQL; falling back to JSON."))
                fmt = "json"
            elif not shutil.which("pg_dump"):
                self.stdout.write(self.style.WARNING("pg_dump not found; falling back to JSON."))
                fmt = "json"

        if fmt == "sql":
            out_path = out_dir / f"{prefix}.sql"
            self._pg_dump(db, out_path)
            self.stdout.write(self.style.SUCCESS(f"Backup created: {out_path}"))
            self._prune(out_dir, keep)
            return

        out_path = out_dir / f"{prefix}.json.gz"
        self._dumpdata_gz(out_path, excludes)
        self.stdout.write(self.style.SUCCESS(f"Backup created: {out_path}"))
        self._prune(out_dir, keep)

    def _pg_dump(self, db: dict, out_path: Path):
        env = dict(os.environ)
        password = str(db.get("PASSWORD") or "")
        if password:
            env["PGPASSWORD"] = password

        host = str(db.get("HOST") or "")
        port = str(db.get("PORT") or "")
        user = str(db.get("USER") or "")
        name = str(db.get("NAME") or "")

        cmd = ["pg_dump", "--no-owner", "--no-privileges", "--format=plain", "--file", str(out_path), name]
        if host:
            cmd.extend(["--host", host])
        if port:
            cmd.extend(["--port", port])
        if user:
            cmd.extend(["--username", user])

        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            msg = (res.stderr or res.stdout or "").strip()
            raise RuntimeError(f"pg_dump failed: {msg}")

    def _dumpdata_gz(self, out_path: Path, excludes: list[str]):
        tmp = out_path.with_suffix("").with_suffix(".json")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    "--natural-foreign",
                    "--natural-primary",
                    "--indent",
                    "2",
                    *[f"--exclude={x}" for x in excludes],
                    stdout=f,
                )
            with tmp.open("rb") as src, gzip.open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _prune(self, out_dir: Path, keep: int):
        if keep <= 0:
            return
        files = sorted(
            [p for p in out_dir.iterdir() if p.is_file() and p.name.startswith("medisync_backup_")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for p in files[keep:]:
            try:
                p.unlink()
            except Exception:
                pass
