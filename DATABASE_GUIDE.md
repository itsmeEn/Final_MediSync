# Database Guide (PostgreSQL)

This project is configured to run on PostgreSQL only.

## Configuration

You can configure the database using either:

- `DATABASE_URL` (recommended for platforms that provide it)
  - Format: `postgresql://USER:PASSWORD@HOST:PORT/DBNAME`
- Or explicit variables:
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

## Local development

```bash
export DB_NAME=medisync
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
python manage.py migrate
python manage.py runserver
```

## Tests

Tests use PostgreSQL and require the following variables (or their `DB_*` equivalents):

- `TEST_DB_NAME`, `TEST_DB_HOST`, `TEST_DB_PORT`, `TEST_DB_USER`, `TEST_DB_PASSWORD`

```bash
export TEST_DB_NAME=medisync_test
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
DJANGO_SETTINGS_MODULE=backend.test_settings python manage.py test
```
