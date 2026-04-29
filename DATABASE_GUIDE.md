# Database Guide (SQLite + PostgreSQL)

This project supports running on either SQLite (local dev / lightweight) or PostgreSQL (recommended for production).

## Switch databases

The backend selects the database at runtime using environment variables:

- `DB_ENGINE`
  - `sqlite` / `sqlite3` → SQLite
  - `postgres` / `postgresql` → PostgreSQL
  - `django.db.backends.sqlite3` or `django.db.backends.postgresql` are also accepted
- `DB_NAME`
  - SQLite: file path (relative paths resolve from `backend/`)
  - PostgreSQL: database name
- PostgreSQL connection (only when `DB_ENGINE=postgres`)
  - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`

### SQLite example

```bash
export DB_ENGINE=sqlite
export DB_NAME=db.sqlite3
python manage.py migrate
python manage.py runserver
```

### PostgreSQL example

```bash
export DB_ENGINE=postgres
export DB_NAME=medisync
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
python manage.py migrate
python manage.py runserver
```

## Migrate data from SQLite to PostgreSQL

This repo includes a management command that migrates by exporting from SQLite (JSON dump) and importing into PostgreSQL.

```bash
python manage.py migrate_sqlite_to_postgres --sqlite-name db.sqlite3
```

Optional PostgreSQL overrides (otherwise the command uses `DB_*` env vars):

```bash
python manage.py migrate_sqlite_to_postgres \
  --sqlite-name db.sqlite3 \
  --postgres-name medisync \
  --postgres-host localhost \
  --postgres-port 5432 \
  --postgres-user postgres \
  --postgres-password postgres
```

## Testing with both engines

By default, `backend/test_settings.py` uses SQLite in-memory.

### SQLite tests (default)

```bash
DJANGO_SETTINGS_MODULE=backend.test_settings python manage.py test
```

### PostgreSQL tests

Create a separate PostgreSQL database for tests, then:

```bash
export TEST_DB_ENGINE=postgres
export TEST_DB_NAME=medisync_test
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
DJANGO_SETTINGS_MODULE=backend.test_settings python manage.py test
```

