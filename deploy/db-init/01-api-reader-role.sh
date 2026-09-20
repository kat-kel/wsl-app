#!/bin/sh
# Creates the role the API connects as: SELECT only, nothing else.
#
# The official Postgres image runs every script in this directory once, the
# first time the container starts against an empty data volume -- so `just
# db-reset` (which drops the volume) is what picks up a change here locally.
# Runs after 00-app-writer-role.sh, whose role every future table will be
# owned by.
#
# The password is a trivial, committed local-dev value, the same tier as the
# POSTGRES_PASSWORD default already in .env.example. A deployed environment
# creates its own role out of band, with a real secret from Secret Manager.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE ROLE api_reader LOGIN PASSWORD 'api_reader';

	GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO api_reader;
	GRANT USAGE ON SCHEMA public TO api_reader;
	GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_reader;

	-- Every table Alembic creates from here on is owned by app_writer, so
	-- this makes api_reader's SELECT apply to it automatically -- no
	-- migration needs to remember to grant it by hand.
	ALTER DEFAULT PRIVILEGES FOR ROLE app_writer IN SCHEMA public
	    GRANT SELECT ON TABLES TO api_reader;
SQL
