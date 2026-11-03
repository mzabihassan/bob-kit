"""Parse Oracle and PostgreSQL DDL scripts into a schema model (plain dicts, JSON-serialisable).

Supported: CREATE TABLE (columns, inline and table constraints, identity, computed columns), ALTER TABLE
(add/drop/modify/rename columns, add/drop constraints, pg_dump forms), CREATE [UNIQUE] INDEX, CREATE SEQUENCE,
ALTER SEQUENCE ... OWNED BY, COMMENT ON, PostgreSQL CREATE TYPE ... AS ENUM and CREATE DOMAIN, and Oracle
triggers that fill a column from a sequence. Other statements are counted and ignored. Scripts are read in the
order given, so Flyway or Liquibase SQL migrations can be passed one after the other.
"""
import re


TYPE_ALIASES = {
    "character varying": "varchar", "varchar2": "varchar", "nvarchar2": "varchar", "nvarchar": "varchar",
    "national character varying": "varchar", "character": "char", "nchar": "char", "bpchar": "char",
    "int": "integer", "int4": "integer", "int8": "bigint", "int2": "smallint", "bool": "boolean",
    "float8": "double", "double precision": "double", "binary_double": "double", "float4": "real",
    "binary_float": "real", "decimal": "numeric", "dec": "numeric", "timestamptz": "timestamp with time zone",
    "timestamp without time zone": "timestamp", "timetz": "time with time zone", "time without time zone": "time",
    "serial4": "serial", "serial8": "bigserial", "serial2": "smallserial", "long raw": "blob", "long": "clob",
    "nclob": "clob", "character large object": "clob", "binary large object": "blob", "varbit": "bit varying",
}


class ParseError(Exception):
    pass


# ---------------------------------------------------------------------------------------------------- lexer

def tokenize(text):
    """Tokens: (kind, value). Kinds: word, qident, string, dollar, number, sym, slashline. Comments are dropped."""
    tokens, i, n = [], 0, len(text)
    line_start = True
    while i < n:
        c = text[i]
        if c == "\n":
            line_start = True
            i += 1
            continue
        if c in " \t\r\f":
            i += 1
            continue
        if c == "-" and text.startswith("--", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c == "/" and line_start:  # SQL*Plus block terminator: a line holding only "/"
            j = text.find("\n", i)
            rest = text[i + 1:(n if j < 0 else j)]
            if not rest.strip():
                tokens.append(("slashline", "/"))
                i = n if j < 0 else j
                continue
        line_start = False
        if c == "'":
            j, buf = i + 1, []
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    break
                buf.append(text[j])
                j += 1
            tokens.append(("string", "".join(buf)))
            i = j + 1
            continue
        if c == '"':
            j = text.find('"', i + 1)
            if j < 0:
                raise ParseError("unterminated quoted identifier")
            tokens.append(("qident", text[i + 1:j]))
            i = j + 1
            continue
        if c == "$":
            m = re.match(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$", text[i:])
            if m:
                tag = m.group(0)
                j = text.find(tag, i + len(tag))
                j = n if j < 0 else j
                tokens.append(("dollar", text[i + len(tag):j]))
                i = j + len(tag)
                continue
        if c.isalpha() or c == "_":
            m = re.match(r"[A-Za-z_][A-Za-z0-9_$#]*", text[i:])
            tokens.append(("word", m.group(0)))
            i += len(m.group(0))
            continue
        if c.isdigit():
            m = re.match(r"\d+(\.\d+)?([eE][+-]?\d+)?", text[i:])
            tokens.append(("number", m.group(0)))
            i += len(m.group(0))
            continue
        if text.startswith("::", i):
            tokens.append(("sym", "::"))
            i += 2
            continue
        for op in (">=", "<=", "<>", "!=", "||", "=>"):
            if text.startswith(op, i):
                tokens.append(("sym", op))
                i += len(op)
                break
        else:
            tokens.append(("sym", c))
            i += 1
    return tokens


def split_statements(tokens, dialect=None):
    """Split on ';' at depth 0. Oracle PL/SQL units (CREATE TRIGGER/PROCEDURE/FUNCTION/PACKAGE/TYPE BODY) contain
    ';' and end at a line holding only '/'. PostgreSQL bodies are dollar-quoted strings, so plain splitting works."""
    stmts, cur, depth, plsql = [], [], 0, False
    for tok in tokens:
        if tok[0] == "slashline":
            if cur:
                stmts.append(cur)
            cur, depth, plsql = [], 0, False
            continue
        cur.append(tok)
        if not plsql and dialect != "postgresql" and len(cur) <= 8 and _is_plsql_head(cur):
            plsql = True
        if plsql and (tok[0] == "dollar" or _pg_trigger(cur)):
            plsql = False  # PostgreSQL function or trigger after all: recompute the depth and split normally
            depth = sum(1 if t == ("sym", "(") else -1 if t == ("sym", ")") else 0 for t in cur)
        if plsql:
            continue
        if tok == ("sym", "("):
            depth += 1
        elif tok == ("sym", ")"):
            depth = max(0, depth - 1)
        elif tok == ("sym", ";") and depth == 0:
            cur.pop()
            if cur:
                stmts.append(cur)
            cur = []
    if cur:
        stmts.append(cur)
    return stmts


def _is_plsql_head(toks):
    words = [v.upper() for k, v in toks if k == "word"]
    if not words or words[0] != "CREATE":
        return False
    rest = [w for w in words[1:] if w not in ("OR", "REPLACE", "EDITIONABLE", "NONEDITIONABLE")]
    if not rest:
        return False
    if rest[0] == "TYPE":
        return len(rest) > 1 and rest[1] == "BODY"
    return rest[0] in ("TRIGGER", "PROCEDURE", "FUNCTION", "PACKAGE")


def _pg_trigger(toks):
    words = [v.upper() for k, v in toks[-3:] if k == "word"]
    return len(words) >= 2 and words[-2] == "EXECUTE" and words[-1] in ("FUNCTION", "PROCEDURE")


# ---------------------------------------------------------------------------------------------------- cursor

class Cursor:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        j = self.i + k
        return self.t[j] if j < len(self.t) else (None, None)

    def word(self, k=0):
        kind, val = self.peek(k)
        return val.upper() if kind == "word" else None

    def at(self, *words):
        return all(self.word(k) == w for k, w in enumerate(words))

    def accept(self, *words):
        if self.at(*words):
            self.i += len(words)
            return True
        return False

    def sym(self, s):
        if self.peek() == ("sym", s):
            self.i += 1
            return True
        return False

    def done(self):
        return self.i >= len(self.t)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def ident(self):
        kind, val = self.next()
        if kind == "word":
            return {"name": val, "quoted": False}
        if kind == "qident":
            return {"name": val, "quoted": True}
        raise ParseError(f"identifier expected, got {val!r}")

    def qualified(self):
        """[schema.]name -> (schema or None, ident)."""
        first = self.ident()
        if self.peek() == ("sym", "."):
            self.i += 1
            second = self.ident()
            return first["name"], second
        return None, first

    def balanced(self):
        """Consume a parenthesised group; return its inner tokens."""
        if not self.sym("("):
            raise ParseError("'(' expected")
        depth, out = 1, []
        while not self.done():
            tok = self.next()
            if tok == ("sym", "("):
                depth += 1
            elif tok == ("sym", ")"):
                depth -= 1
                if depth == 0:
                    return out
            out.append(tok)
        raise ParseError("unbalanced parentheses")

    def until_comma(self):
        """Tokens up to the next ',' or end at depth 0 (comma consumed)."""
        depth, out = 0, []
        while not self.done():
            tok = self.peek()
            if tok == ("sym", "(" ):
                depth += 1
            elif tok == ("sym", ")"):
                depth -= 1
            elif tok == ("sym", ",") and depth == 0:
                self.i += 1
                return out
            out.append(tok)
            self.i += 1
        return out


def split_commas(toks):
    parts, cur, depth = [], [], 0
    for tok in toks:
        if tok == ("sym", "("):
            depth += 1
        elif tok == ("sym", ")"):
            depth -= 1
        if tok == ("sym", ",") and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        parts.append(cur)
    return parts


def render(toks):
    out = []
    for kind, val in toks:
        if kind == "string":
            out.append("'" + val.replace("'", "''") + "'")
        elif kind == "qident":
            out.append('"' + val + '"')
        elif kind == "dollar":
            out.append("$$" + val + "$$")
        else:
            out.append(val)
    text = " ".join(out)
    text = re.sub(r"\s*([(),.])\s*", r"\1", text).replace(",", ", ")
    text = re.sub(r"\s*::\s*", "::", text)
    return text


def key(name):
    return name.lower()


# ---------------------------------------------------------------------------------------------------- schema

class Schema:
    def __init__(self):
        self.tables, self.sequences, self.enums, self.domains = {}, {}, {}, {}
        self.trigger_links, self.ignored, self.warnings = [], {}, []
        self.dialect_votes = {"oracle": 0, "postgresql": 0}

    def table(self, name, stmt_hint=""):
        t = self.tables.get(key(name))
        if t is None:
            self.warnings.append(f"{stmt_hint}: table {name} is not defined before this statement; ignored")
        return t

    def to_dict(self):
        return {"tables": list(self.tables.values()), "sequences": self.sequences, "enums": self.enums,
                "trigger_links": self.trigger_links, "ignored_statements": self.ignored, "warnings": self.warnings}


ORACLE_HINTS = {"VARCHAR2", "NVARCHAR2", "NUMBER", "CLOB", "BLOB", "NCLOB", "RAW", "SYSDATE", "SYSTIMESTAMP",
                "NEXTVAL", "BINARY_DOUBLE", "BINARY_FLOAT", "TABLESPACE", "NOCACHE", "SYS_GUID", "DUAL"}
PG_HINTS = {"SERIAL", "BIGSERIAL", "SMALLSERIAL", "TEXT", "JSONB", "BYTEA", "TIMESTAMPTZ", "UUID", "BOOLEAN",
            "INT4", "INT8", "INT2", "NOW", "GEN_RANDOM_UUID", "OWNED", "REGCLASS"}


def parse_scripts(texts):
    """texts: list of (label, sql). Returns Schema."""
    schema = Schema()
    for label, sql in texts:
        toks = tokenize(sql)
        for kind, val in toks:
            if kind == "word":
                u = val.upper()
                if u in ORACLE_HINTS:
                    schema.dialect_votes["oracle"] += 1
                elif u in PG_HINTS:
                    schema.dialect_votes["postgresql"] += 1
            elif kind == "dollar" or val == "::":
                schema.dialect_votes["postgresql"] += 1
        votes = schema.dialect_votes
        hint_dialect = None if votes["oracle"] == votes["postgresql"] else max(votes, key=votes.get)
        for n, stmt in enumerate(split_statements(toks, hint_dialect), 1):
            hint = f"{label} statement {n}"
            try:
                parse_statement(schema, stmt, hint)
            except ParseError as e:
                schema.warnings.append(f"{hint}: could not parse ({e}): {render(stmt)[:120]}")
    finalize(schema)
    return schema


def parse_statement(schema, stmt, hint):
    c = Cursor(stmt)
    head = [v.upper() for k, v in stmt[:8] if k == "word"]
    if c.accept("CREATE"):
        c.accept("OR", "REPLACE")
        while c.word() in ("GLOBAL", "LOCAL", "TEMPORARY", "TEMP", "UNLOGGED", "EDITIONABLE", "NONEDITIONABLE",
                           "PRIVATE", "SHARDED", "DUPLICATED", "IMMUTABLE", "BLOCKCHAIN"):
            if c.word() in ("TEMPORARY", "TEMP"):
                return _ignore(schema, "CREATE TEMPORARY TABLE")
            c.i += 1
        if c.accept("TABLE"):
            return parse_create_table(schema, c, hint)
        if c.at("UNIQUE", "INDEX") or c.at("INDEX") or c.at("BITMAP", "INDEX"):
            return parse_create_index(schema, c, hint)
        if c.accept("SEQUENCE"):
            return parse_create_sequence(schema, c)
        if c.accept("TYPE"):
            return parse_create_type(schema, c)
        if c.accept("DOMAIN"):
            return parse_create_domain(schema, c)
        if c.accept("TRIGGER"):
            return parse_trigger(schema, stmt, c)
        return _ignore(schema, "CREATE " + (c.word() or "?"))
    if c.accept("ALTER", "TABLE"):
        return parse_alter_table(schema, c, hint)
    if c.accept("ALTER", "SEQUENCE"):
        return parse_alter_sequence(schema, c)
    if c.accept("COMMENT", "ON"):
        return parse_comment(schema, c, hint)
    return _ignore(schema, " ".join(head[:2]) or "?")


def _ignore(schema, what):
    schema.ignored[what] = schema.ignored.get(what, 0) + 1


# ---------------------------------------------------------------------------------------------------- tables

def new_table(schema_name, ident):
    return {"schema": schema_name, "name": ident["name"], "quoted": ident["quoted"], "columns": [], "pk": None,
            "uniques": [], "fks": [], "checks": [], "indexes": [], "comment": None}


def parse_create_table(schema, c, hint):
    c.accept("IF", "NOT", "EXISTS")
    sch, ident = c.qualified()
    if c.at("AS") or c.at("OF") or c.at("PARTITION", "OF"):
        schema.warnings.append(f"{hint}: CREATE TABLE {ident['name']} AS/OF/PARTITION OF is not mapped")
        return
    table = new_table(sch, ident)
    body = c.balanced()
    for part in split_commas(body):
        pc = Cursor(part)
        if pc.word() in ("CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "EXCLUDE") or \
                (pc.word() == "PERIOD" and pc.word(1) == "FOR"):
            parse_table_constraint(table, pc)
        elif pc.word() == "LIKE":
            schema.warnings.append(f"{hint}: LIKE in CREATE TABLE {ident['name']} is not expanded")
        else:
            table["columns"].append(parse_column(schema, table, pc))
    rest = [v.upper() for k, v in c.t[c.i:] if k == "word"]
    if "INHERITS" in rest:
        schema.warnings.append(f"{hint}: table {ident['name']} uses INHERITS; inherited columns are not mapped")
    if key(ident["name"]) in schema.tables:
        schema.warnings.append(f"{hint}: table {ident['name']} defined twice; the last definition wins")
    schema.tables[key(ident["name"])] = table


MULTIWORD_STARTS = {"DOUBLE", "CHARACTER", "NATIONAL", "TIMESTAMP", "TIME", "INTERVAL", "LONG", "BIT", "CHAR",
                    "NCHAR", "BINARY"}
CONTINUATIONS = {"PRECISION", "VARYING", "CHARACTER", "WITH", "WITHOUT", "LOCAL", "TIME", "ZONE", "TO", "SECOND",
                 "MONTH", "DAY", "YEAR", "RAW", "LARGE", "OBJECT"}


def parse_type(schema, c):
    """Column type -> (type dict, domain check or None, domain NOT NULL)."""
    first = c.ident()
    if c.peek() == ("sym", "."):  # schema-qualified type (PostgreSQL enum or domain)
        c.i += 1
        first = c.ident()
    words, params, array = [first["name"]], [], False
    while not c.done():
        kind, val = c.peek()
        if (kind, val) == ("sym", "("):
            inner = [render(p).strip() for p in split_commas(c.balanced())]
            if not params:
                params = inner
            continue
        if (kind, val) == ("sym", "["):
            while not c.done() and c.next() != ("sym", "]"):
                pass
            array = True
            continue
        if kind == "word" and val.upper() == "ARRAY":
            c.i += 1
            array = True
            continue
        if kind == "word" and val.upper() in CONTINUATIONS and words[0].upper() in MULTIWORD_STARTS:
            words.append(val)
            c.i += 1
            continue
        break
    raw = " ".join(words).lower()
    length_semantics = None
    if params and params[-1].upper().endswith((" CHAR", " BYTE")):
        length_semantics = params[-1].split()[-1].upper()
        params[-1] = params[-1].split()[0]
    base = TYPE_ALIASES.get(raw, raw)
    base = TYPE_ALIASES.get(base, base)
    if base in schema.domains:
        dom = schema.domains[base]
        return dict(dom["type"], domain=base), dom.get("check"), dom.get("not_null", False)
    return {"base": base, "params": params, "array": array, "length_semantics": length_semantics,
            "raw": " ".join(words) + ("(" + ",".join(params) + ")" if params else "") + ("[]" if array else "")}, \
        None, False


def parse_column(schema, table, c):
    ident = c.ident()
    col = {"name": ident["name"], "quoted": ident["quoted"], "nullable": True, "default": None, "identity": None,
           "computed": None, "comment": None}
    type_info, dom_check, dom_not_null = parse_type(schema, c)
    col["type"] = type_info
    if dom_not_null:
        col["nullable"] = False
    if dom_check:
        table["checks"].append({"name": None, "expr": dom_check.replace("VALUE", col["name"]), "column": col["name"]})
    base = type_info["base"]
    if base in ("serial", "bigserial", "smallserial"):
        col["type"] = dict(type_info, base={"serial": "integer", "bigserial": "bigint", "smallserial": "smallint"}[base])
        col["identity"] = {"kind": "serial", "increment": 1}
        col["nullable"] = False
    cname = None
    while not c.done():
        w = c.word()
        if w == "CONSTRAINT":
            c.i += 1
            cname = c.ident()["name"]
            continue
        if c.accept("NOT", "NULL"):
            col["nullable"] = False
        elif c.accept("NULL"):
            pass
        elif c.accept("DEFAULT"):
            if c.accept("ON", "NULL"):
                pass
            col["default"] = render(_default_tokens(c))
        elif w == "GENERATED" or (w == "AS" and c.peek(1) == ("sym", "(")):
            parse_generated(col, c)
        elif c.accept("PRIMARY", "KEY"):
            table["pk"] = {"name": cname, "columns": [col["name"]]}
            col["nullable"] = False
            _skip_index_clause(c)
        elif c.accept("UNIQUE"):
            table["uniques"].append({"name": cname, "columns": [col["name"]], "source": "constraint"})
            _skip_index_clause(c)
        elif c.accept("REFERENCES"):
            fk = parse_references(c)
            fk.update({"name": cname, "columns": [col["name"]]})
            table["fks"].append(fk)
        elif c.accept("CHECK"):
            table["checks"].append({"name": cname, "expr": render(c.balanced()), "column": col["name"]})
            c.accept("NO", "INHERIT")
        elif c.accept("COLLATE"):
            c.next()
        elif w in ("ENABLE", "DISABLE", "VALIDATE", "NOVALIDATE", "RELY", "NORELY", "VISIBLE", "INVISIBLE",
                   "DEFERRABLE", "INITIALLY", "IMMEDIATE", "DEFERRED", "ENCRYPT", "SORT"):
            c.i += 1
            if w in ("NOT",):
                c.i += 1
        else:
            c.i += 1
            continue
        cname = None
    return col


def _default_tokens(c):
    out, depth = [], 0
    while not c.done():
        kind, val = c.peek()
        if depth == 0 and kind == "word" and val.upper() in ("NOT", "NULL", "CONSTRAINT", "PRIMARY", "UNIQUE",
                                                            "REFERENCES", "CHECK", "GENERATED", "COLLATE", "ENABLE"):
            break
        if (kind, val) == ("sym", "("):
            depth += 1
        elif (kind, val) == ("sym", ")"):
            depth -= 1
        out.append(c.next())
    return out


def parse_generated(col, c):
    c.accept("GENERATED")
    if c.accept("ALWAYS"):
        mode = "always"
    elif c.accept("BY", "DEFAULT"):
        mode = "by default"
        if c.accept("ON", "NULL"):
            mode = "by default on null"
    else:
        mode = "always"
    if c.accept("AS", "IDENTITY"):
        ident = {"kind": "identity", "mode": mode, "increment": 1, "start": 1}
        if c.peek() == ("sym", "("):
            opts = c.balanced()
            ident.update(_sequence_options(opts))
        col["identity"] = ident
        col["nullable"] = False
        return
    if c.accept("AS"):
        expr = render(c.balanced())
        stored = c.accept("STORED")
        c.accept("VIRTUAL")
        col["computed"] = {"expr": expr, "stored": stored}


def _sequence_options(toks):
    out = {}
    words = [v.upper() if k == "word" else v for k, v in toks]
    for i, w in enumerate(words):
        if w == "INCREMENT":
            j = i + 1 + (words[i + 1] == "BY" if i + 1 < len(words) else 0)
            if j < len(words):
                out["increment"] = _int(words[j], words[j - 1])
        if w == "START":
            j = i + 1 + (words[i + 1] == "WITH" if i + 1 < len(words) else 0)
            if j < len(words):
                out["start"] = _int(words[j], words[j - 1])
        if w == "NAME" and i > 0 and words[i - 1] == "SEQUENCE" and i + 1 < len(words):
            # pg_dump: SEQUENCE NAME public.x_seq
            parts = [p for p in words[i + 1:i + 4] if p != "."]
            out["sequence"] = toks[i + 3][1] if len(parts) > 1 and words[i + 2] == "." else toks[i + 1][1]
    return out


def _int(val, prev):
    try:
        v = int(val)
        return -v if prev == "-" else v
    except (TypeError, ValueError):
        return None


def _skip_index_clause(c):
    if c.accept("USING", "INDEX"):
        if c.peek() == ("sym", "("):
            c.balanced()
        else:
            while not c.done() and c.word() not in ("ENABLE", "DISABLE", "CONSTRAINT", "NOT", "NULL", "CHECK",
                                                  "REFERENCES", "DEFAULT", "UNIQUE", "PRIMARY"):
                c.i += 1


def parse_references(c):
    sch, ident = c.qualified()
    ref_cols = None
    if c.peek() == ("sym", "("):
        ref_cols = [render([t]) .strip('"') if t[0] != "qident" else t[1] for t in c.balanced() if t != ("sym", ",")]
    fk = {"ref_schema": sch, "ref_table": ident["name"], "ref_columns": ref_cols, "on_delete": None}
    while not c.done():
        if c.accept("ON", "DELETE"):
            if c.accept("CASCADE"):
                fk["on_delete"] = "CASCADE"
            elif c.accept("SET", "NULL"):
                fk["on_delete"] = "SET NULL"
            elif c.accept("SET", "DEFAULT"):
                fk["on_delete"] = "SET DEFAULT"
            elif c.accept("RESTRICT") or c.accept("NO", "ACTION"):
                fk["on_delete"] = None
        elif c.accept("ON", "UPDATE"):
            c.i += 1
            if c.word() in ("NULL", "DEFAULT", "ACTION"):
                c.i += 1
        elif c.accept("MATCH"):
            c.i += 1
        elif c.word() in ("DEFERRABLE", "INITIALLY", "IMMEDIATE", "DEFERRED", "ENABLE", "DISABLE", "VALIDATE",
                          "NOVALIDATE", "RELY", "NORELY") or c.at("NOT", "DEFERRABLE"):
            c.i += 2 if c.at("NOT", "DEFERRABLE") else 1
        else:
            break
    return fk


SORT_WORDS = {"ASC", "DESC", "NULLS", "FIRST", "LAST"}


def ident_list(toks):
    """Column list of a constraint or index: identifiers only (expressions become None)."""
    out = []
    for part in split_commas(toks):
        names = [t for t in part if not (t[0] == "word" and t[1].upper() in SORT_WORDS)]
        out.append(names[0][1] if len(names) == 1 and names[0][0] in ("word", "qident") else None)
    return out


def parse_table_constraint(table, c):
    name = None
    if c.accept("CONSTRAINT"):
        name = c.ident()["name"]
    if c.accept("PRIMARY", "KEY"):
        table["pk"] = {"name": name, "columns": ident_list(c.balanced())}
        for col in table["columns"]:
            if col["name"].lower() in [x.lower() for x in table["pk"]["columns"] if x]:
                col["nullable"] = False
    elif c.accept("UNIQUE"):
        c.accept("NULLS", "NOT", "DISTINCT")
        table["uniques"].append({"name": name, "columns": ident_list(c.balanced()), "source": "constraint"})
    elif c.accept("FOREIGN", "KEY"):
        cols = ident_list(c.balanced())
        if not c.accept("REFERENCES"):
            raise ParseError("REFERENCES expected")
        fk = parse_references(c)
        fk.update({"name": name, "columns": cols})
        table["fks"].append(fk)
    elif c.accept("CHECK"):
        table["checks"].append({"name": name, "expr": render(c.balanced()), "column": None})
    # EXCLUDE and others: ignored


def find_column(table, name):
    for col in table["columns"]:
        if (col["name"] == name) if col["quoted"] else (col["name"].lower() == name.lower()):
            return col
    for col in table["columns"]:
        if col["name"].lower() == name.lower():
            return col
    return None


# ---------------------------------------------------------------------------------------------------- alter

def parse_alter_table(schema, c, hint):
    c.accept("IF", "EXISTS")
    c.accept("ONLY")
    _, ident = c.qualified()
    table = schema.table(ident["name"], hint)
    if table is None:
        return
    for action in split_commas(c.t[c.i:]) if not _oracle_paren_add(c) else [c.t[c.i:]]:
        ac = Cursor(action)
        if ac.accept("ADD"):
            if ac.word() in ("CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK"):
                parse_table_constraint(table, ac)
                pk = table["pk"]
                if pk:
                    for col in table["columns"]:
                        if col["name"].lower() in [x.lower() for x in pk["columns"] if x]:
                            col["nullable"] = False
            elif ac.peek() == ("sym", "("):  # Oracle: ADD (col type, ...)
                for part in split_commas(ac.balanced()):
                    pc = Cursor(part)
                    if pc.word() in ("CONSTRAINT", "PRIMARY", "UNIQUE", "FOREIGN", "CHECK"):
                        parse_table_constraint(table, pc)
                    else:
                        table["columns"].append(parse_column(schema, table, pc))
            else:
                ac.accept("COLUMN")
                ac.accept("IF", "NOT", "EXISTS")
                table["columns"].append(parse_column(schema, table, ac))
        elif ac.accept("DROP"):
            if ac.accept("CONSTRAINT"):
                ac.accept("IF", "EXISTS")
                cname = ac.ident()["name"].lower()
                table["uniques"] = [u for u in table["uniques"] if (u["name"] or "").lower() != cname]
                table["fks"] = [f for f in table["fks"] if (f["name"] or "").lower() != cname]
                table["checks"] = [k for k in table["checks"] if (k["name"] or "").lower() != cname]
                if table["pk"] and (table["pk"]["name"] or "").lower() == cname:
                    table["pk"] = None
            elif ac.accept("PRIMARY", "KEY"):
                table["pk"] = None
            else:
                ac.accept("COLUMN")
                ac.accept("IF", "EXISTS")
                names = ([t[1] for t in ac.balanced() if t[0] in ("word", "qident")] if ac.peek() == ("sym", "(")
                         else [ac.ident()["name"]])
                for name in names:
                    _drop_column(table, name)
        elif ac.accept("RENAME", "COLUMN"):
            old = ac.ident()["name"]
            ac.accept("TO")
            new = ac.ident()
            col = find_column(table, old)
            if col:
                col["name"], col["quoted"] = new["name"], new["quoted"]
                _rename_refs(schema, table, old, new["name"])
        elif ac.accept("RENAME", "TO"):
            new = ac.ident()
            schema.tables.pop(key(table["name"]), None)
            old = table["name"]
            table["name"], table["quoted"] = new["name"], new["quoted"]
            schema.tables[key(new["name"])] = table
            for t in schema.tables.values():
                for fk in t["fks"]:
                    if fk["ref_table"].lower() == old.lower():
                        fk["ref_table"] = new["name"]
        elif ac.accept("MODIFY"):
            parts = split_commas(ac.balanced()) if ac.peek() == ("sym", "(") else [ac.t[ac.i:]]
            for part in parts:
                pc = Cursor(part)
                col = find_column(table, pc.ident()["name"])
                if col is None:
                    continue
                _modify_column(schema, table, col, pc)
        elif ac.accept("ALTER"):
            ac.accept("COLUMN")
            col = find_column(table, ac.ident()["name"])
            if col is None:
                continue
            if ac.accept("SET", "NOT", "NULL"):
                col["nullable"] = False
            elif ac.accept("DROP", "NOT", "NULL"):
                col["nullable"] = True
            elif ac.accept("SET", "DEFAULT"):
                col["default"] = render(_default_tokens(ac))
            elif ac.accept("DROP", "DEFAULT"):
                col["default"] = None
            elif ac.accept("SET", "DATA", "TYPE") or ac.accept("TYPE"):
                col["type"] = parse_type(schema, ac)[0]
            elif ac.word() == "ADD" and ac.word(1) == "GENERATED":
                ac.i += 1
                parse_generated(col, ac)
            elif ac.accept("DROP", "IDENTITY"):
                col["identity"] = None
        # OWNER TO, ENABLE TRIGGER, SET ...: ignored


def _oracle_paren_add(c):
    return c.word() in ("ADD", "MODIFY", "DROP") and c.peek(1) == ("sym", "(")


def _modify_column(schema, table, col, pc):
    if not pc.done() and pc.peek()[0] == "word" and pc.word() not in ("NOT", "NULL", "DEFAULT", "CONSTRAINT",
                                                                       "GENERATED", "CHECK", "UNIQUE", "PRIMARY"):
        col["type"] = parse_type(schema, pc)[0]
    while not pc.done():
        if pc.accept("NOT", "NULL"):
            col["nullable"] = False
        elif pc.accept("NULL"):
            col["nullable"] = True
        elif pc.accept("DEFAULT"):
            col["default"] = render(_default_tokens(pc))
        elif pc.word() == "GENERATED":
            parse_generated(col, pc)
        else:
            pc.i += 1


def _drop_column(table, name):
    low = name.lower()
    table["columns"] = [c for c in table["columns"] if c["name"].lower() != low]
    table["uniques"] = [u for u in table["uniques"] if low not in [x.lower() for x in u["columns"] if x]]
    table["indexes"] = [i for i in table["indexes"] if low not in [x.lower() for x in i["columns"] if x]]
    table["fks"] = [f for f in table["fks"] if low not in [x.lower() for x in f["columns"] if x]]
    table["checks"] = [k for k in table["checks"] if (k.get("column") or "").lower() != low]


def _rename_refs(schema, table, old, new):
    for group in (table["uniques"], table["indexes"], table["fks"]):
        for item in group:
            item["columns"] = [new if (x or "").lower() == old.lower() else x for x in item["columns"]]
    if table["pk"]:
        table["pk"]["columns"] = [new if (x or "").lower() == old.lower() else x for x in table["pk"]["columns"]]
    for chk in table["checks"]:
        if (chk.get("column") or "").lower() == old.lower():
            chk["column"] = new
        chk["expr"] = re.sub(r"\b%s\b" % re.escape(old), new, chk["expr"], flags=re.I)
    for t in schema.tables.values():
        for fk in t["fks"]:
            if fk["ref_table"].lower() == table["name"].lower() and fk["ref_columns"]:
                fk["ref_columns"] = [new if (x or "").lower() == old.lower() else x for x in fk["ref_columns"]]


# ---------------------------------------------------------------------------------------------------- others

def parse_create_index(schema, c, hint):
    unique = c.accept("UNIQUE")
    c.accept("BITMAP")
    c.accept("INDEX")
    c.accept("CONCURRENTLY")
    c.accept("IF", "NOT", "EXISTS")
    name = None
    if not c.at("ON"):
        name = c.qualified()[1]["name"]
    if not c.accept("ON"):
        raise ParseError("ON expected in CREATE INDEX")
    c.accept("ONLY")
    _, ident = c.qualified()
    table = schema.table(ident["name"], hint)
    if table is None:
        return
    if c.accept("USING"):
        c.next()
    cols = ident_list(c.balanced())
    partial = c.accept("WHERE") or any(v.upper() == "WHERE" for k, v in c.t[c.i:] if k == "word")
    table["indexes"].append({"name": name, "columns": cols, "unique": unique, "partial": partial})


def parse_create_sequence(schema, c):
    c.accept("IF", "NOT", "EXISTS")
    sch, ident = c.qualified()
    opts = _sequence_options(c.t[c.i:])
    schema.sequences[key(ident["name"])] = {"schema": sch, "name": ident["name"], "quoted": ident["quoted"],
                                            "increment": opts.get("increment") or 1, "start": opts.get("start") or 1,
                                            "owned_by": None}


def parse_alter_sequence(schema, c):
    c.accept("IF", "EXISTS")
    _, ident = c.qualified()
    seq = schema.sequences.get(key(ident["name"]))
    words = [v.upper() for k, v in c.t[c.i:] if k == "word"]
    if seq is None:
        return
    opts = _sequence_options(c.t[c.i:])
    if opts.get("increment"):
        seq["increment"] = opts["increment"]
    if "OWNED" in words:
        idents = [v for k, v in c.t[c.i:] if k in ("word", "qident") and v.upper() not in ("OWNED", "BY")]
        if len(idents) >= 2:
            seq["owned_by"] = {"table": idents[-2], "column": idents[-1]}


def parse_create_type(schema, c):
    _, ident = c.qualified()
    if c.accept("AS", "ENUM"):
        values = [v for k, v in c.balanced() if k == "string"]
        schema.enums[key(ident["name"])] = {"name": ident["name"], "values": values}
    else:
        _ignore(schema, "CREATE TYPE (non-enum)")


def parse_create_domain(schema, c):
    _, ident = c.qualified()
    c.accept("AS")
    type_info = parse_type(schema, c)[0]
    check, not_null = None, False
    while not c.done():
        if c.accept("CHECK"):
            check = render(c.balanced())
        elif c.accept("NOT", "NULL"):
            not_null = True
        else:
            c.i += 1
    schema.domains[key(ident["name"])] = {"type": type_info, "check": check, "not_null": not_null}


def parse_comment(schema, c, hint):
    if c.accept("TABLE"):
        _, ident = c.qualified()
        target = schema.table(ident["name"], hint)
        col = None
    elif c.accept("COLUMN"):
        parts = []
        while c.peek()[0] in ("word", "qident"):
            parts.append(c.next()[1])
            if not c.sym("."):
                break
        if len(parts) < 2:
            return
        target = schema.table(parts[-2], hint)
        col = parts[-1]
    else:
        return _ignore(schema, "COMMENT ON other")
    if not c.accept("IS") or target is None:
        return
    kind, text = c.next()
    if kind != "string":
        return
    if col is None:
        target["comment"] = text
    else:
        column = find_column(target, col)
        if column:
            column["comment"] = text


def parse_trigger(schema, stmt, c):
    """Oracle legacy identity: BEFORE INSERT trigger assigning seq.NEXTVAL to :NEW.col."""
    words = [(k, v) for k, v in stmt]
    table = None
    for i, (k, v) in enumerate(words):
        if k == "word" and v.upper() == "ON" and i + 1 < len(words):
            j = i + 1
            if j + 2 < len(words) and words[j + 1] == ("sym", "."):
                j += 2
            table = words[j][1]
            break
    seqs, targets = [], []
    for i, (k, v) in enumerate(words):
        if k == "word" and v.upper() == "NEXTVAL" and i >= 2 and words[i - 1] == ("sym", "."):
            seqs.append(words[i - 2][1])
        if (k, v) == ("sym", ":") and i + 3 < len(words) and words[i + 1][1].upper() == "NEW" and \
                words[i + 2] == ("sym", "."):
            targets.append(words[i + 3][1])
    if table and seqs and targets:
        text = render(stmt).upper()
        conditional = bool(re.search(r"IF\s*:\s*NEW\s*\.\s*%s\s+IS\s+NULL" % re.escape(targets[0].upper()), text))
        schema.trigger_links.append({"table": table, "column": targets[0], "sequence": seqs[0],
                                     "conditional": conditional})
    else:
        _ignore(schema, "CREATE TRIGGER")


def finalize(schema):
    """Unique indexes count as unique constraints; partial or expression indexes do not."""
    for t in schema.tables.values():
        for idx in t["indexes"]:
            if idx["unique"] and not idx["partial"] and None not in idx["columns"]:
                cols = [x.lower() for x in idx["columns"]]
                if not any([x.lower() for x in u["columns"] if x] == cols for u in t["uniques"]) and \
                        not (t["pk"] and [x.lower() for x in t["pk"]["columns"] if x] == cols):
                    t["uniques"].append({"name": idx["name"], "columns": idx["columns"], "source": "index"})


def detect_dialect(schema):
    votes = schema.dialect_votes
    if votes["oracle"] == votes["postgresql"]:
        return None
    return "oracle" if votes["oracle"] > votes["postgresql"] else "postgresql"
