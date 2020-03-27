"""
Adopted from https://github.com/everilae/sqlite_json/blob/master/sqlite_json/__init__.py
"""

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.mysql.json import JSONIndexType, JSONPathType
from sqlalchemy.engine import CreateEnginePlugin

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy import types as sqltypes
from sqlalchemy.sql.operators import json_getitem_op, json_path_getitem_op

__all__ = [
    "JSON",
    "JsonPlugin"
]

_json_serializer = None
_json_deserializer = None


class JSON(sqltypes.JSON):
    """SQLite JSON type.

    SQLite supports JSON as of version 3.9 through its JSON1_ extension.
    Note that JSON1_ is a `loadable extension`_ and as such may not be
    available, or may require run-time loading.

    .. _JSON1: https://www.sqlite.org/json1.html
    .. _`loadable extension`: https://www.sqlite.org/loadext.html
    """


class JSONB(postgresql.JSONB):
    pass


@compiles(JSON, "sqlite")
@compiles(sqltypes.JSON, "sqlite")
def compile_json_type(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
@compiles(postgresql.JSONB, "sqlite")
def compile_json_type(element, compiler, **kw):
    return "JSON"


@compiles(BinaryExpression, "sqlite")
def compile_binary(binary, compiler, override_operator=None, **kw):
    operator = override_operator or binary.operator

    if operator is json_getitem_op:
        return visit_json_getitem_op_binary(
            compiler, binary, operator, override_operator=override_operator,
            **kw)

    if operator is json_path_getitem_op:
        return visit_json_path_getitem_op_binary(
            compiler, binary, operator, override_operator=override_operator,
            **kw)

    return compiler.visit_binary(binary, override_operator=override_operator, **kw)


def visit_json_getitem_op_binary(compiler, binary, operator, **kw):
    return "JSON_QUOTE(JSON_EXTRACT(%s, %s))" % (
        compiler.process(binary.left, **kw),
        compiler.process(binary.right, **kw))


def visit_json_path_getitem_op_binary(compiler, binary, operator, **kw):
    return "JSON_QUOTE(JSON_EXTRACT(%s, %s))" % (
        compiler.process(binary.left, **kw),
        compiler.process(binary.right, **kw))


def monkeypatch_dialect(dialect):
    if not hasattr(dialect, "_json_serializer"):
        dialect._json_serializer = _json_serializer

    if not hasattr(dialect, "_json_deserializer"):
        dialect._json_deserializer = _json_deserializer

    if sqltypes.JSON not in dialect.colspecs:
        dialect.colspecs = dialect.colspecs.copy()
        dialect.colspecs[sqltypes.JSON] = JSON
        dialect.colspecs[sqltypes.JSON.JSONIndexType] = JSONIndexType
        dialect.colspecs[sqltypes.JSON.JSONPathType] = JSONPathType

    if postgresql.JSONB not in dialect.colspecs:
        dialect.colspecs = dialect.colspecs.copy()
        dialect.colspecs[postgresql.JSONB] = JSONB
        dialect.colspecs[postgresql.JSONB.JSONIndexType] = JSONIndexType
        dialect.colspecs[postgresql.JSONB.JSONPathType] = JSONPathType

    if "JSON" not in dialect.ischema_names:
        dialect.ischema_names = dialect.ischema_names.copy()
        dialect.ischema_names["JSON"] = JSON

    if "JSONB" not in dialect.ischema_names:
        dialect.ischema_names = dialect.ischema_names.copy()
        dialect.ischema_names["JSONB"] = JSONB


class JsonPlugin(CreateEnginePlugin):

    def engine_created(self, engine):
        monkeypatch_dialect(engine.dialect)