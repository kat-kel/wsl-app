#!/bin/sh
# Creates the role Alembic and the load job connect as: it can create tables
# and write rows, nothing more.
#
# POSTGRES_USER is the bootstrap superuser the Postgres image itself creates
# to run these scripts; nothing application-level connects with it from here
# on. app_writer and api_reader (01-api-reader-role.sh) are the two roles
# anything actually uses -- explicit siblings with exactly the privileges
# their job needs, instead of one declared role and one ambient superuser.
#
# CREATE on the schema is what lets Alembic issue DDL; owning the tables it
# creates is what gives it SELECT/INSERT/UPDATE/DELETE on them automatically,
# so there is no separate table-privilege grant to keep in sync as models
# change.
#
# Runs once, against a fresh data volume -- `just db-reset` is what re-applies
# a change here locally. The password is a trivial, committed local-dev
# value, the same tier as the POSTGRES_PASSWORD default already in
# .env.example. A deployed environment creates its own role out of band, with
# a real secret from Secret Manager.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE ROLE app_writer LOGIN PASSWORD 'app_writer';

	GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO app_writer;
	GRANT USAGE, CREATE ON SCHEMA public TO app_writer;
SQL
