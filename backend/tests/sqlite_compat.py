"""Temporary PostgreSQL-type adaptation for isolated SQLite test fixtures.

The production schema remains PostgreSQL JSONB/UUID. These fixture helpers
swap only the selected table columns while SQLite creates and exercises its
in-memory tables, then restore SQLAlchemy metadata during teardown.
"""
from sqlalchemy import JSON, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.schema import DefaultClause
from sqlalchemy.types import Uuid


def utiliser_types_sqlite(tables):
    sauvegardes = []
    for table in tables:
        for column in table.columns:
            if isinstance(column.type, JSONB):
                sauvegardes.append((column, "type", column.type))
                column.type = JSON()
            elif isinstance(column.type, PostgreSQLUUID):
                sauvegardes.append((column, "type", column.type))
                column.type = Uuid(as_uuid=True)
            default = column.server_default
            if default is not None and "::jsonb" in str(default.arg).lower():
                sauvegardes.append((column, "server_default", default))
                column.server_default = DefaultClause(text(str(default.arg).replace("::jsonb", "")))

    def restaurer():
        for column, attribute, value in reversed(sauvegardes):
            setattr(column, attribute, value)

    return restaurer
