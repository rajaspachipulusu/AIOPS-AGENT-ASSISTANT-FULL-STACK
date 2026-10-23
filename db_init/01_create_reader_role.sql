-- Runs automatically on first container start (postgres image convention:
-- any .sql/.sh file in /docker-entrypoint-initdb.d/ is executed once, when
-- the data directory is empty).
--
-- Creates the restricted, read-only role used by the Text-to-SQL feature.
-- Table creation + seeding of sample data happens separately, via
-- `python -m app.seed` (run once after the backend container is up), since
-- it uses the app's SQLAlchemy models as the source of truth for schema.

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aiops_reader') THEN
      CREATE ROLE aiops_reader LOGIN PASSWORD 'readonly_dev_pw';
   END IF;
END
$$;

GRANT CONNECT ON DATABASE aiops TO aiops_reader;
GRANT USAGE ON SCHEMA public TO aiops_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO aiops_reader;
ALTER ROLE aiops_reader SET statement_timeout = '5s';
ALTER ROLE aiops_reader SET default_transaction_read_only = on;
