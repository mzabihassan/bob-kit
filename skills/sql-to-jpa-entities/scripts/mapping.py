"""Turn a parsed schema into a JPA mapping plan: classes, fields, identifiers, associations, enums and warnings.

The plan is plain data. javagen.py renders it; the report lists every decision with its reason so that the agent
can review the few that need judgement (class names, inverse collections, Oracle DATE semantics, untyped NUMBER).
"""
import re

JAVA_KEYWORDS = {"abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
                 "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float", "for",
                 "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native", "new",
                 "package", "private", "protected", "public", "return", "short", "static", "strictfp", "super",
                 "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void", "volatile",
                 "while", "true", "false", "null", "record", "var", "yield", "sealed", "permits"}
RESERVED_CLASSES = {"Object", "String", "Class", "Integer", "Long", "Boolean", "Byte", "Short", "Double", "Float",
                    "Character", "Number", "Enum", "Record", "System", "Thread", "Void", "Math", "Override",
                    "Entity", "Table", "Column", "Id", "Index", "Version", "Lob", "Basic", "Embeddable",
                    "Transient", "Converter", "Convert", "Set", "List", "Map", "Optional", "UUID", "Instant",
                    "Duration", "LocalDate", "LocalDateTime", "LocalTime", "OffsetDateTime", "OffsetTime",
                    "BigDecimal", "BigInteger", "Objects", "Serializable", "Generated", "Repository", "Mapper"}
GENERIC_ENUM_FIELDS = {"status", "type", "state", "kind", "category", "level", "mode", "role", "code", "flag",
                       "nature", "class", "sort", "priority", "channel", "source", "reason", "result"}
VERSION_NAMES = {"version", "row_version", "rowversion", "lock_version", "opt_lock", "optlock", "optimistic_lock",
                 "entity_version", "record_version"}
CREATED_NAMES = {"created_at", "created_on", "creation_date", "created_date", "create_date", "date_created",
                 "insert_date", "inserted_at", "creation_time", "created_time", "create_time", "creation_ts",
                 "created_ts"}
UPDATED_NAMES = {"updated_at", "updated_on", "modified_at", "modified_on", "last_modified", "last_updated",
                 "modification_date", "update_date", "modified_date", "updated_date", "update_time",
                 "last_update", "last_modified_at", "last_modified_date", "updated_ts", "modified_ts"}
DATE_ONLY_HINTS = re.compile(r"(^|_)(date|day|birth|birthday|dob)(_|$)|_on$|^on_|_dt$|_d$")

KNOWN_CONFIG = {"dialect", "base_package", "entity_package", "dto_package", "mapper_package", "repository_package",
                "lombok", "mapper", "repositories", "dto", "schema_in_annotations", "strip_prefixes", "class_names",
                "field_names", "enum_names", "inverse", "many_to_many_as_entity", "exclude_tables", "oracle_date",
                "types", "timestamps", "only_tables"}


class ConfigError(Exception):
    pass


def default_config(dialect):
    return {"dialect": dialect, "base_package": "com.example.app", "entity_package": None, "dto_package": None,
            "mapper_package": None, "repository_package": None, "lombok": False, "mapper": "mapstruct",
            "repositories": True, "dto": True, "schema_in_annotations": False, "strip_prefixes": [],
            "class_names": {}, "field_names": {}, "enum_names": {}, "inverse": {}, "many_to_many_as_entity": [],
            "exclude_tables": [], "oracle_date": {}, "types": {}, "timestamps": "hibernate"}


def check_config(cfg):
    unknown = sorted(set(cfg) - KNOWN_CONFIG)
    if unknown:
        raise ConfigError(f"unknown configuration keys: {', '.join(unknown)}")
    if cfg.get("dialect") not in ("oracle", "postgresql"):
        raise ConfigError("dialect must be 'oracle' or 'postgresql'")
    if cfg.get("mapper") not in ("mapstruct", "manual", "none"):
        raise ConfigError("mapper must be 'mapstruct', 'manual' or 'none'")
    if cfg.get("timestamps") not in ("hibernate", "none"):
        raise ConfigError("timestamps must be 'hibernate' or 'none'")
    if not re.match(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$", cfg.get("base_package") or ""):
        raise ConfigError("base_package must be a lower-case Java package name")
    for k in ("oracle_date",):
        for col, v in (cfg.get(k) or {}).items():
            if v not in ("LocalDate", "LocalDateTime"):
                raise ConfigError(f"oracle_date[{col}] must be LocalDate or LocalDateTime")


# ---------------------------------------------------------------------------------------------------- names

def words_of(name):
    return [w for w in re.split(r"[^A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)) if w]


def camel(name):
    ws = [w.lower() for w in words_of(name)]
    if not ws:
        return "value"
    out = ws[0] + "".join(w.capitalize() for w in ws[1:])
    if out[0].isdigit():
        out = "v" + out
    return out + "Value" if out in JAVA_KEYWORDS else out


def pascal(name):
    c = camel(name)
    return c[0].upper() + c[1:]


def singular_lower(word):
    return singular(word).lower()


def singular(word):
    w = word.lower()
    if len(w) > 4 and w.endswith("ies"):
        return word[:-3] + ("Y" if word.isupper() else "y")
    for suffix in ("sses", "shes", "ches", "xes", "zzes"):
        if w.endswith(suffix):
            return word[:-2]
    if w.endswith("s") and not w.endswith(("ss", "us", "is", "os", "as", "ys")) and len(w) > 3:
        return word[:-1]
    return word


def plural(word):
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def class_name(table, cfg, taken):
    override = (cfg.get("class_names") or {}).get(table["name"]) or (cfg.get("class_names") or {}).get(
        table["name"].lower())
    if override:
        return override
    name = table["name"]
    for prefix in cfg.get("strip_prefixes") or []:
        if name.lower().startswith(prefix.lower()) and len(name) > len(prefix):
            name = name[len(prefix):]
            break
    ws = words_of(name)
    ws[-1] = singular(ws[-1])
    out = "".join(w.lower().capitalize() for w in ws)
    if out[0].isdigit():
        out = "T" + out
    if out in RESERVED_CLASSES or out in taken:
        out += "Entity"
    return out


# ---------------------------------------------------------------------------------------------------- checks

def _col_pattern(col):
    return r'(?:\(?\s*"?%s"?\s*\)?(?:::[a-z ]+)?)' % re.escape(col)


def check_values(expr, col):
    """Values allowed by a CHECK on col: IN list, = ANY (ARRAY[...]) (pg_dump) or OR-ed equalities."""
    e = expr.strip()
    while e.startswith("(") and e.endswith(")") and _balanced(e[1:-1]):
        e = e[1:-1].strip()
    cp = _col_pattern(col)
    m = re.fullmatch(cp + r"\s+IN\s*\((.*)\)", e, re.I | re.S)
    if not m:
        m = re.fullmatch(cp + r"\s*=\s*ANY\s*\(\s*\(?\s*ARRAY\s*\[(.*)\]\s*\)?(?:::[a-z ]+\[\])?\s*\)", e, re.I | re.S)
    if m:
        return _literals(m.group(1))
    parts = re.split(r"\s+OR\s+", e, flags=re.I)
    if len(parts) > 1:
        vals = []
        for p in parts:
            pm = re.fullmatch(r"\(?\s*" + cp + r"\s*=\s*('(?:[^']|'')*'|-?\d+)(?:::[a-z ]+)?\s*\)?", p.strip(), re.I)
            if not pm:
                return None
            vals.extend(_literals(pm.group(1)))
        return vals
    return None


def _balanced(s):
    depth = 0
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if depth < 0:
            return False
    return depth == 0


def _literals(text):
    out = []
    for m in re.finditer(r"'((?:[^']|'')*)'|(-?\d+(?:\.\d+)?)", text):
        out.append(m.group(1).replace("''", "'") if m.group(1) is not None else m.group(2))
    return out


def check_rule(expr, col):
    """Simple range rules usable as Bean Validation constraints on the DTO."""
    e = expr.strip().strip("()").strip()
    cp = _col_pattern(col)
    m = re.fullmatch(cp + r"\s*(>=|>)\s*(-?\d+(?:\.\d+)?)", e, re.I)
    if m:
        op, val = m.group(1), m.group(2)
        if val in ("0", "0.0"):
            return {"kind": "PositiveOrZero"} if op == ">=" else {"kind": "Positive"}
        return {"kind": "Min", "value": val, "inclusive": op == ">="}
    m = re.fullmatch(cp + r"\s*(<=|<)\s*(-?\d+(?:\.\d+)?)", e, re.I)
    if m:
        return {"kind": "Max", "value": m.group(2), "inclusive": m.group(1) == "<="}
    m = re.fullmatch(cp + r"\s+BETWEEN\s+(-?\d+(?:\.\d+)?)\s+AND\s+(-?\d+(?:\.\d+)?)", e, re.I)
    if m:
        return {"kind": "Range", "min": m.group(1), "max": m.group(2)}
    m = re.fullmatch(r"(?:char_)?length\s*\(\s*" + cp + r"\s*\)\s*(>=|>)\s*(\d+)", e, re.I)
    if m:
        n = int(m.group(2)) + (1 if m.group(1) == ">" else 0)
        return {"kind": "SizeMin", "value": n}
    if re.fullmatch(cp + r"\s+IS\s+JSON(\s+.*)?", e, re.I):
        return {"kind": "json"}
    return None


# ---------------------------------------------------------------------------------------------------- types

def sql_type_label(t):
    return t["raw"]


def java_type(col, table, dialect, cfg, enums_pg, checks, notes):
    """Return a dict describing the Java mapping of a column."""
    t = col["type"]
    base, params = t["base"], t["params"]
    full = f"{table['name']}.{col['name']}".lower()
    override = {k.lower(): v for k, v in (cfg.get("types") or {}).items()}.get(full)
    info = {"java": None, "length": None, "precision": None, "scale": None, "lob": False, "jdbc": None,
            "converter": None, "enum": None, "array_of": None, "json": False}
    values = None
    for chk in checks:
        vals = check_values(chk["expr"], col["name"])
        if vals is not None:
            values = vals
        rule = check_rule(chk["expr"], col["name"])
        if rule and rule["kind"] == "json":
            info["json"] = True
    if t.get("array"):
        elem = dict(col, type=dict(t, array=False))
        inner = java_type(elem, table, dialect, cfg, enums_pg, [], notes)
        info.update(java=f"List<{inner['java']}>", jdbc="ARRAY", array_of=inner["java"])
        notes.append(f"{full}: PostgreSQL array mapped as List<{inner['java']}> with @JdbcTypeCode(SqlTypes.ARRAY)")
        return info
    if override:
        info["java"] = override
        return info

    def num(p_default=None):
        p = params[0] if params else p_default
        s = params[1] if len(params) > 1 else "0"
        return p, s

    if base in enums_pg:
        info.update(java="ENUM", enum={"source": "pg", "type": base, "values": enums_pg[base]["values"]})
        return info
    if base in ("varchar", "string"):
        info.update(java="String", length=_int(params[0]) if params else None)
    elif base == "char":
        n = _int(params[0]) if params else 1
        if values and n == 1 and sorted(v.upper() for v in values) in (["N", "Y"], ["F", "T"]):
            info.update(java="Boolean", converter="YesNoConverter" if "Y" in [v.upper() for v in values]
                        else "TrueFalseConverter", boolean_values=values)
            return info
        info.update(java="String", length=n, jdbc="CHAR")
    elif base in ("text", "citext", "name"):
        info.update(java="String")
        if dialect == "postgresql":
            info["column_definition"] = base
    elif base in ("clob",):
        info.update(java="String", lob=True)
        if info["json"]:
            notes.append(f"{full}: JSON stored in a CLOB (IS JSON check): mapped as @Lob String; parse it in the "
                         f"service or use a native JSON column (Oracle 21c+) to map it with @JdbcTypeCode(JSON)")
    elif base in ("blob", "bytea", "longblob", "varbinary", "binary"):
        info.update(java="byte[]", lob=(base == "blob"))
    elif base == "raw":
        n = _int(params[0]) if params else None
        if n == 16:
            info.update(java="UUID")
            notes.append(f"{full}: RAW(16) mapped as UUID (Hibernate stores UUIDs as raw(16) on Oracle); use "
                         f"byte[] if the column holds something else")
        else:
            info.update(java="byte[]", length=n)
    elif base == "uuid":
        info.update(java="UUID")
    elif base in ("json", "jsonb"):
        info.update(java="String", jdbc="JSON", json=True)
    elif base == "boolean":
        info.update(java="Boolean")
    elif base in ("smallint",):
        if values and sorted(values) == ["0", "1"]:
            info.update(java="Boolean", converter="NumericBooleanConverter")
            return info
        info.update(java="Short")
    elif base in ("integer", "mediumint"):
        info.update(java="Integer")
    elif base == "bigint":
        info.update(java="Long")
    elif base in ("number", "numeric"):
        p, s = num()
        if not params or p in ("*",) and s in ("0", None):
            if not params and _is_pk(table, col):
                info.update(java="Long")
                notes.append(f"{full}: NUMBER without precision used as a key: mapped as Long (declare NUMBER(19))")
            elif params and p == "*":
                info.update(java="Long")
            else:
                info.update(java="BigDecimal")
                notes.append(f"DECISION {full}: {sql_type_label(t)} has no precision: mapped as BigDecimal; set "
                             f"types[\"{full}\"] to Long or Integer if it only holds integers")
            return info
        p_i, s_i = _int(p), _int(s)
        if s_i and s_i > 0:
            info.update(java="BigDecimal", precision=p_i, scale=s_i)
        elif p_i is not None and p_i <= 4 and values and sorted(values) == ["0", "1"]:
            # 0/1 flag: the converter keeps the numeric column (Oracle 23ai and PostgreSQL have a real BOOLEAN)
            info.update(java="Boolean", converter="NumericBooleanConverter")
        elif p_i is not None and p_i <= 4 and dialect == "postgresql":
            info.update(java="Short", precision=p_i, scale=0)
        elif p_i is not None and p_i <= 9:
            info.update(java="Integer", precision=p_i if base == "numeric" else None)
        elif p_i is not None and p_i <= 19:
            info.update(java="Long", precision=p_i if base == "numeric" else None)
        else:
            info.update(java="BigInteger", precision=p_i, scale=0)
    elif base in ("real",):
        info.update(java="Float")
    elif base in ("double", "float"):
        info.update(java="Double")
        if re.search(r"amount|price|balance|total|fee|rate|cost", col["name"], re.I):
            notes.append(f"{full}: binary floating point for a monetary-looking column: prefer NUMERIC/NUMBER "
                         f"with BigDecimal")
    elif base == "money":
        info.update(java="BigDecimal")
        notes.append(f"{full}: PostgreSQL money type: prefer numeric(19,2); mapped as BigDecimal")
    elif base == "date":
        if dialect == "oracle":
            choice = {k.lower(): v for k, v in (cfg.get("oracle_date") or {}).items()}.get(full)
            if not choice:
                choice = "LocalDate" if DATE_ONLY_HINTS.search(col["name"].lower()) else "LocalDateTime"
                notes.append(f"DECISION {full}: Oracle DATE also stores a time; mapped as {choice} from the column "
                             f"name; set oracle_date[\"{full}\"] if the other type fits")
            info.update(java=choice)
        else:
            info.update(java="LocalDate")
    elif base == "time":
        info.update(java="LocalTime")
    elif base == "time with time zone":
        info.update(java="OffsetTime")
    elif base == "timestamp":
        info.update(java="LocalDateTime")
    elif base == "timestamp with time zone":
        info.update(java="OffsetDateTime")
    elif base == "timestamp with local time zone":
        info.update(java="Instant")
    elif base in ("interval", "interval day to second"):
        info.update(java="Duration", jdbc="INTERVAL_SECOND")
    else:
        info.update(java="String")
        info["column_definition"] = t["raw"].lower()
        notes.append(f"{full}: type {sql_type_label(t)} has no standard JPA mapping: mapped as String with its "
                     f"column definition; check reads and writes")
    if values and info["java"] == "String":
        info.update(java="ENUM", enum={"source": "check", "values": values})
    return info


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _is_pk(table, col):
    return bool(table["pk"]) and col["name"].lower() in [c.lower() for c in table["pk"]["columns"] if c]


# ---------------------------------------------------------------------------------------------------- plan

JAVA_TYPE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(<[A-Za-z0-9_.,? <>]+>)?(\[\])?$")


def relation_keys(schema):
    """Configuration keys of the foreign keys: child_table.fk_column[+fk_column...]."""
    return [f"{t['name'].lower()}.{'+'.join(c.lower() for c in fk['columns'])}"
            for t in schema["tables"] for fk in t["fks"]]


def check_against_schema(schema, cfg):
    """Every table, column or relation named in the configuration must exist: a typo must not be ignored."""
    tables = {t["name"].lower(): t for t in schema["tables"]}
    columns = {f"{t['name'].lower()}.{c['name'].lower()}": c for t in schema["tables"] for c in t["columns"]}
    relations = relation_keys(schema)
    problems = []

    def unknown(key, names, valid, what):
        bad = [n for n in names if n.lower() not in valid]
        if bad:
            sample = ", ".join(sorted(valid)[:40])
            problems.append(f"{key}: unknown {what} {', '.join(map(str, bad))}; valid: {sample}")

    for key in ("class_names",):
        unknown(key, list((cfg.get(key) or {}).keys()), set(tables), "table")
    for key in ("exclude_tables", "only_tables", "many_to_many_as_entity", "strip_prefixes"):
        if key != "strip_prefixes":
            unknown(key, list(cfg.get(key) or []), set(tables), "table")
    for key in ("enum_names", "oracle_date", "types"):
        unknown(key, list((cfg.get(key) or {}).keys()), set(columns), "column (table.column)")
    unknown("field_names", list((cfg.get("field_names") or {}).keys()), set(columns) | set(relations),
            "column or foreign key (table.column or table.fk_col1+fk_col2)")
    unknown("inverse", list((cfg.get("inverse") or {}).keys()), set(relations),
            "relation (child_table.fk_column, as listed under INVERSE KEYS)")
    for k, v in (cfg.get("types") or {}).items():
        if not isinstance(v, str) or not JAVA_TYPE.match(v):
            problems.append(f"types[{k}] = {v!r} is not a Java type")
    for k, v in (cfg.get("inverse") or {}).items():
        if not isinstance(v, bool):
            problems.append(f"inverse[{k}] must be true or false")
    for k in (cfg.get("oracle_date") or {}):
        col = columns.get(k.lower())
        if col and (cfg.get("dialect") != "oracle" or col["type"]["base"] != "date"):
            problems.append(f"oracle_date[{k}] applies only to Oracle DATE columns")
    if problems:
        raise ConfigError("; ".join(problems))


def build_plan(schema, cfg):
    check_config(cfg)
    check_against_schema(schema, cfg)
    dialect = cfg["dialect"]
    tables = schema["tables"]
    exclude = {t.lower() for t in cfg.get("exclude_tables") or []}
    only = {t.lower() for t in cfg.get("only_tables") or []}
    by_key = {t["name"].lower(): t for t in tables}
    seqs = {k.lower(): v for k, v in schema["sequences"].items()}
    enums_pg = {k.lower(): v for k, v in schema["enums"].items()}
    plan = {"dialect": dialect, "entities": [], "enums": [], "converters": [], "warnings": list(schema["warnings"]),
            "decisions": [], "notes": [], "skipped": [], "relations": []}
    notes = []

    # 1. classify tables and name classes
    taken = set()
    classes = {}
    for t in tables:
        k = t["name"].lower()
        if k in exclude:
            plan["skipped"].append({"table": t["name"], "reason": "excluded by configuration"})
            continue
        pk = _pk_columns(t)
        if not pk:
            plan["skipped"].append({"table": t["name"], "reason": "no primary key and no NOT NULL unique key: "
                                                                  "not mappable as an entity (add a primary key, or "
                                                                  "map it as a read-only @Immutable entity by hand)"})
            continue
        if pk["from_unique"]:
            plan["warnings"].append(f"{t['name']}: no primary key; the NOT NULL unique key ({', '.join(pk['columns'])})"
                                    f" is used as the identifier. Add a primary key.")
        cname = class_name(t, cfg, taken)
        taken.add(cname)
        classes[k] = {"table": t, "class": cname, "pk": pk, "kind": "entity"}

    for k, info in classes.items():
        t = info["table"]
        if _is_pure_join(t, info["pk"]["columns"], classes) and k not in {x.lower() for x in
                                                                        cfg.get("many_to_many_as_entity") or []}:
            info["kind"] = "join"
    entities = {k: v for k, v in classes.items() if v["kind"] == "entity"}

    # 2. entities
    out = {}
    for k, info in entities.items():
        out[k] = _entity(info, classes, seqs, enums_pg, schema, cfg, plan, notes)

    # 3. many-to-many through pure join tables (owning side only)
    for k, info in classes.items():
        if info["kind"] != "join":
            continue
        t = info["table"]
        fk_a, fk_b = t["fks"]
        owner_fk, other_fk = (fk_a, fk_b)
        if t["name"].lower().startswith(fk_b["ref_table"].lower()) and \
                not t["name"].lower().startswith(fk_a["ref_table"].lower()):
            owner_fk, other_fk = fk_b, fk_a
        owner = out.get(owner_fk["ref_table"].lower())
        target = classes.get(other_fk["ref_table"].lower())
        if owner is None or target is None or target["kind"] != "entity":
            plan["warnings"].append(f"{t['name']}: join table whose referenced tables are not all mapped; skipped")
            continue
        fname = _unique_field(owner, camel(plural(target["class"])))
        rel_id = f"{t['name']}".lower()
        owner["many_to_many"].append({
            "name": fname, "target": target["class"], "join_table": t["name"], "join_table_quoted": t["quoted"],
            "schema": t["schema"],
            "join_columns": _join_cols(owner_fk), "inverse_join_columns": _join_cols(other_fk),
            "fk_name": owner_fk["name"], "inverse_fk_name": other_fk["name"],
            "target_id_type": _id_java_type(out.get(other_fk["ref_table"].lower()))})
        plan["relations"].append({"id": rel_id, "kind": "ManyToMany", "from": owner["class"], "field": fname,
                                  "to": target["class"], "why": f"{t['name']} only holds the two foreign keys"})
        plan["skipped"].append({"table": t["name"], "reason": f"join table mapped as {owner['class']}.{fname} "
                                                              f"(@ManyToMany)"})

    # 4. inverse collections for compositions
    for k, ent in out.items():
        for assoc in ent["associations"]:
            parent = out.get(assoc["target_key"])
            if parent is None or assoc["kind"] != "ManyToOne":
                continue
            rel_id = f"{ent['table'].lower()}.{'+'.join(c['name'].lower() for c in assoc['join_columns'])}"
            identifying = assoc.get("maps_id") is not None
            cascade_fk = assoc.get("on_delete") == "CASCADE"
            association_entity = identifying and ent["id"]["kind"] == "embedded" and \
                sum(1 for a in ent["associations"] if a.get("maps_id") is not None) >= 2
            default = cascade_fk or identifying
            wanted = (cfg.get("inverse") or {}).get(rel_id, default)
            assoc["relation_id"] = rel_id
            assoc["relation_kind"] = ("association entity" if association_entity else
                                      "composition" if (cascade_fk or identifying) else "reference")
            if not wanted:
                continue
            composition = (cascade_fk or identifying) and not association_entity
            base = camel(plural(ent["class"]))
            same_target = [a for a in ent["associations"] if a["target_key"] == assoc["target_key"]]
            if len(same_target) > 1:
                base = assoc["name"] + plural(ent["class"])
            name = _unique_field(parent, base)
            parent["inverse"].append({"name": name, "target": ent["class"], "mapped_by": assoc["name"],
                                      "composition": composition, "relation_id": rel_id})
            plan["relations"].append({
                "id": rel_id, "kind": "OneToMany", "from": parent["class"], "field": name, "to": ent["class"],
                "why": ("composition: " + ("ON DELETE CASCADE" if cascade_fk else "identifying foreign key")
                        + " -> cascade ALL + orphanRemoval") if composition else
                ("association entity: navigable from both sides, no cascade" if association_entity
                 else "requested in the configuration")})

    plan["entities"] = list(out.values())
    for ent in plan["entities"]:
        for a in ent["associations"]:
            if "relation_id" not in a:
                a["relation_id"] = f"{ent['table'].lower()}.{'+'.join(c['name'].lower() for c in a['join_columns'])}"
            plan["relations"].append({"id": a["relation_id"], "kind": a["kind"], "from": ent["class"],
                                      "field": a["name"], "to": a["target"], "why": a["why"]})
    _collect_enums(plan, cfg)
    for n in notes:
        (plan["decisions"] if n.startswith("DECISION ") else plan["notes"]).append(n.replace("DECISION ", "", 1))
    _schema_warnings(schema, classes, plan)
    if only:
        plan["entities"] = [e for e in plan["entities"] if e["table"].lower() in only]
    return plan


def _pk_columns(t):
    if t["pk"] and all(t["pk"]["columns"]):
        return {"columns": t["pk"]["columns"], "name": t["pk"]["name"], "from_unique": False}
    for u in t["uniques"]:
        cols = [c for c in u["columns"] if c]
        if cols and len(cols) == len(u["columns"]):
            if all(not _col(t, c)["nullable"] for c in cols if _col(t, c)):
                return {"columns": cols, "name": u["name"], "from_unique": True}
    return None


def _col(t, name):
    for c in t["columns"]:
        if c["name"].lower() == (name or "").lower():
            return c
    return None


def _is_pure_join(t, pk_cols, classes):
    if len(t["fks"]) != 2:
        return False
    fk_cols = [c.lower() for fk in t["fks"] for c in fk["columns"] if c]
    cols = [c["name"].lower() for c in t["columns"]]
    if sorted(fk_cols) != sorted(cols) or sorted(c.lower() for c in pk_cols) != sorted(cols):
        return False
    return all(fk["ref_table"].lower() in classes for fk in t["fks"])


def _join_cols(fk):
    return [{"name": c, "referenced": (fk["ref_columns"] or [None] * len(fk["columns"]))[i]}
            for i, c in enumerate(fk["columns"])]


def _unique_field(ent, base):
    names = {f["name"] for f in ent["fields"]} | {a["name"] for a in ent["associations"]} | \
            {m["name"] for m in ent["many_to_many"]} | {i["name"] for i in ent["inverse"]} | {"id"}
    name, n = base, 2
    while name in names:
        name, n = f"{base}{n}", n + 1
    return name


def _id_java_type(ent):
    if ent is None:
        return "Long"
    return ent["id"]["java"]


def _entity(info, classes, seqs, enums_pg, schema, cfg, plan, notes):
    t, dialect = info["table"], cfg["dialect"]
    tname = t["name"]
    pk_cols = [c.lower() for c in info["pk"]["columns"]]
    ent = {"class": info["class"], "table": tname, "quoted": t["quoted"], "schema": t["schema"],
           "comment": t["comment"], "fields": [], "associations": [], "many_to_many": [], "inverse": [],
           "uniques": [], "indexes": [], "id": None, "warnings": []}
    field_overrides = {k.lower(): v for k, v in (cfg.get("field_names") or {}).items()}

    # foreign keys to mapped entities become associations; others stay scalar columns
    fk_cols = set()
    mapped_fks = []
    for fk in t["fks"]:
        target = classes.get(fk["ref_table"].lower())
        if target is None:
            ent["warnings"].append(f"foreign key {fk['name'] or fk['columns']} references {fk['ref_table']}, which "
                                   f"is not mapped: its columns stay plain fields")
            continue
        if target["kind"] == "join":
            ent["warnings"].append(f"foreign key to join table {fk['ref_table']}: columns stay plain fields")
            continue
        ref_cols = fk["ref_columns"] or target["pk"]["columns"]
        fk = dict(fk, ref_columns=ref_cols)
        mapped_fks.append((fk, target))
        fk_cols.update(c.lower() for c in fk["columns"])

    # identifier
    id_info = _identifier(t, info, seqs, schema, cfg, ent, notes, enums_pg, mapped_fks)
    ent["id"] = id_info

    # scalar fields
    written = set(c.lower() for c in pk_cols) if id_info["kind"] == "simple" else set(pk_cols)
    for col in t["columns"]:
        low = col["name"].lower()
        if low in pk_cols or low in fk_cols:
            continue
        checks = [k for k in t["checks"] if (k.get("column") or "").lower() == low or
                  re.search(r'\b%s\b' % re.escape(col["name"]), k["expr"], re.I)]
        jt = java_type(col, t, dialect, cfg, enums_pg, checks, notes)
        f = _field(col, t, jt, field_overrides, ent, checks)
        ent["fields"].append(f)
        written.add(low)

    # associations
    for fk, target in mapped_fks:
        cols = [c.lower() for c in fk["columns"]]
        nullable = any(_col(t, c)["nullable"] for c in fk["columns"] if _col(t, c))
        unique = any(sorted(x.lower() for x in u["columns"] if x) == sorted(cols) for u in t["uniques"])
        shared_pk = sorted(cols) == sorted(pk_cols)
        in_pk = set(cols) <= set(pk_cols)
        kind = "OneToOne" if (unique or shared_pk) else "ManyToOne"
        name = field_overrides.get(f"{tname}.{'+'.join(cols)}".lower()) or _assoc_name(fk, target, ent)
        name = _unique_field(ent, name)
        maps_id = None
        if in_pk:
            maps_id = "" if id_info["kind"] == "simple" else _embedded_attr(id_info, fk["columns"])
        overlap = bool(set(cols) & written) and maps_id is None
        a = {"kind": kind, "name": name, "target": target["class"], "target_key": fk["ref_table"].lower(),
             "join_columns": _join_cols(fk), "optional": nullable, "fk_name": fk["name"], "maps_id": maps_id,
             "read_only": overlap, "on_delete": fk["on_delete"],
             "target_pk": [c for c in target["pk"]["columns"]],
             "references_pk": [c.lower() for c in fk["ref_columns"]] == [c.lower() for c in target["pk"]["columns"]]}
        if not a["references_pk"]:
            a["why_extra"] = "references a unique key, not the primary key: the target class implements Serializable"
        why = []
        if shared_pk:
            why.append("the foreign key is the primary key: one-to-one sharing the parent's id (@MapsId)")
        elif unique:
            why.append("unique foreign key: one-to-one")
        else:
            why.append("foreign key")
        if maps_id not in (None, ""):
            why.append(f"part of the composite key (@MapsId(\"{maps_id}\"))")
        if overlap:
            why.append("its columns are already mapped: read-only association")
            ent["warnings"].append(f"association {name}: columns {', '.join(fk['columns'])} are also mapped "
                                   f"elsewhere; mapped read-only (insertable = false, updatable = false)")
        a["why"] = "; ".join(why)
        ent["associations"].append(a)
        written.update(cols)

    # constraints and indexes for @Table
    for u in t["uniques"]:
        if None in u["columns"]:
            continue
        ent["uniques"].append({"name": u["name"], "columns": u["columns"]})
    for idx in t["indexes"]:
        if None in idx["columns"] or idx["unique"]:
            continue
        ent["indexes"].append({"name": idx["name"], "columns": idx["columns"]})
    if dialect == "oracle":
        for f in ent["fields"]:
            if f["java"] == "String" and not f["nullable"] and not f.get("lob"):
                f["oracle_not_empty"] = True
    return ent


def _identifier(t, info, seqs, schema, cfg, ent, notes, enums_pg, mapped_fks):
    pk_cols = info["pk"]["columns"]
    dialect = cfg["dialect"]
    full = t["name"].lower()
    if len(pk_cols) == 1:
        col = _col(t, pk_cols[0])
        jt = java_type(col, t, dialect, cfg, enums_pg, [], notes)
        java = jt["java"] if jt["java"] != "ENUM" else "String"
        gen = _generation(t, col, seqs, schema, java, notes)
        fk_on_pk = [fk for fk, _ in mapped_fks if [c.lower() for c in fk["columns"]] == [col["name"].lower()]]
        if fk_on_pk:
            gen = None
        override = {k.lower(): v for k, v in (cfg.get("field_names") or {}).items()}.get(
            f"{full}.{col['name']}".lower())
        low, tl = col["name"].lower(), t["name"].lower()
        generic = low in ("id", "pk", f"{tl}_id", f"{tl}id", f"id_{tl}", f"{singular_lower(tl)}_id")
        field = {"name": override or ("id" if generic else camel(col["name"])),
                 "column": col["name"], "quoted": col["quoted"], "java": java, "length": jt.get("length"),
                 "jdbc": jt.get("jdbc"), "precision": jt.get("precision"), "scale": jt.get("scale"),
                 "comment": col.get("comment")}
        if gen is None and not fk_on_pk:
            ent["warnings"].append(f"identifier {col['name']} has no generator: the application assigns it "
                                   f"(Spring Data save() then merges: consider Persistable<ID> with isNew())")
        return {"kind": "simple", "field": field, "java": java, "generation": gen}
    # composite key
    fields = []
    for c in pk_cols:
        col = _col(t, c)
        jt = java_type(col, t, dialect, cfg, enums_pg, [], notes)
        fields.append({"name": camel(col["name"]), "column": col["name"], "quoted": col["quoted"],
                       "java": jt["java"] if jt["java"] != "ENUM" else "String", "length": jt.get("length"),
                       "jdbc": jt.get("jdbc"), "precision": jt.get("precision"), "scale": jt.get("scale")})
    return {"kind": "embedded", "class": info["class"] + "Id", "fields": fields, "java": info["class"] + "Id",
            "generation": None}


def _embedded_attr(id_info, fk_columns):
    if len(fk_columns) == 1:
        for f in id_info["fields"]:
            if f["column"].lower() == fk_columns[0].lower():
                return f["name"]
    return ""


def _generation(t, col, seqs, schema, java, notes):
    full = f"{t['name']}.{col['name']}".lower()
    ident = col.get("identity")
    if java == "UUID":
        return {"strategy": "UUID", "source": "UUID primary key: generated by Hibernate"}
    if ident:
        if ident["kind"] == "serial":
            return {"strategy": "IDENTITY", "source": "serial column"}
        return {"strategy": "IDENTITY", "source": f"identity column (GENERATED {ident.get('mode', 'ALWAYS').upper()})"}
    default = col.get("default") or ""
    m = re.search(r"nextval\s*\(\s*'([^']+)'", default, re.I) or re.search(r"([A-Za-z0-9_$#.\"]+)\s*\.\s*NEXTVAL",
                                                                           default, re.I)
    if m:
        return _seq_gen(m.group(1), seqs, f"column default {default}", notes, full)
    for seq in seqs.values():
        ob = seq.get("owned_by")
        if ob and ob["table"].lower().split(".")[-1] == t["name"].lower() and ob["column"].lower() == \
                col["name"].lower():
            return _seq_gen(seq["name"], seqs, "sequence OWNED BY the column", notes, full)
    for link in schema["trigger_links"]:
        if link["table"].lower() == t["name"].lower() and link["column"].lower() == col["name"].lower():
            g = _seq_gen(link["sequence"], seqs, "BEFORE INSERT trigger", notes, full)
            if not link["conditional"]:
                notes.append(f"{full}: the trigger always overwrites the id with {link['sequence']}.NEXTVAL: "
                             f"Hibernate would not know the stored id. Make the trigger conditional "
                             f"(IF :NEW.{col['name']} IS NULL) or drop it")
            return g
    if java in ("Long", "Integer", "Short", "BigInteger"):
        tn = t["name"].lower()
        for cand in (f"{tn}_seq", f"seq_{tn}", f"{tn}_id_seq", f"s_{tn}", f"{tn}_s", f"sq_{tn}", f"{tn}_sq",
                     f"{tn}_{col['name'].lower()}_seq"):
            if cand in seqs:
                g = _seq_gen(seqs[cand]["name"], seqs, "sequence matched by name", notes, full)
                notes.append(f"DECISION {full}: id generator inferred from the sequence name "
                             f"{seqs[cand]['name']}; confirm that inserts use it")
                return g
    return None


def _seq_gen(name, seqs, source, notes, full):
    bare = name.split(".")[-1].strip('"')
    seq = seqs.get(bare.lower())
    if seq is None:
        notes.append(f"{full}: sequence {bare} is not defined in the scripts: allocationSize = 1; set it to the "
                     f"sequence's INCREMENT BY")
        inc = 1
    else:
        inc = seq["increment"] or 1
        if inc == 1:
            notes.append(f"{full}: sequence {bare} has INCREMENT BY 1: one database round trip per insert; "
                         f"INCREMENT BY 50 with allocationSize = 50 lets Hibernate allocate ids in blocks")
    return {"strategy": "SEQUENCE", "sequence": bare, "allocation": inc, "source": source}


def _assoc_name(fk, target, ent):
    cols = [c.lower() for c in fk["columns"]]
    if len(cols) == 1:
        c = cols[0]
        ref = (fk["ref_columns"][0] or "").lower()
        for suffix in ([f"_{ref}"] if ref else []) + ["_id", "_fk", "_no", "_key", "_code", "_ref"]:
            if c.endswith(suffix) and len(c) > len(suffix):
                return camel(c[: -len(suffix)])
        for prefix in ("id_", "fk_"):
            if c.startswith(prefix) and len(c) > len(prefix):
                return camel(c[len(prefix):])
        return camel(c) + "Ref"
    return camel(target["class"])


def _field(col, t, jt, overrides, ent, checks):
    low = col["name"].lower()
    name = overrides.get(f"{t['name']}.{col['name']}".lower()) or camel(col["name"])
    name = _unique_field(ent, name)
    default = col.get("default")
    f = {"name": name, "column": col["name"], "quoted": col["quoted"], "java": jt["java"], "nullable": col["nullable"],
         "length": jt.get("length"), "precision": jt.get("precision"), "scale": jt.get("scale"), "lob": jt["lob"],
         "jdbc": jt.get("jdbc"), "converter": jt.get("converter"), "enum": jt.get("enum"),
         "column_definition": jt.get("column_definition"), "comment": col.get("comment"), "version": False,
         "creation": False, "update": False, "computed": bool(col.get("computed")), "initial": None,
         "db_default": default, "rules": [], "sql_type": col["type"]["raw"]}
    if low in VERSION_NAMES and jt["java"] in ("Integer", "Long", "Short", "LocalDateTime", "Instant",
                                               "OffsetDateTime"):
        f["version"] = True
    elif low in CREATED_NAMES and jt["java"] in ("LocalDateTime", "Instant", "OffsetDateTime", "LocalDate"):
        f["creation"] = True
    elif low in UPDATED_NAMES and jt["java"] in ("LocalDateTime", "Instant", "OffsetDateTime", "LocalDate"):
        f["update"] = True
    if default and not f["version"] and not f["creation"] and not f["computed"]:
        f["initial"] = _literal_default(default, jt, f)
    for chk in checks:
        rule = check_rule(chk["expr"], col["name"])
        if rule and rule["kind"] != "json":
            f["rules"].append(rule)
    return f


def _literal_default(default, jt, f):
    d = default.strip()
    while d.startswith("(") and d.endswith(")"):
        d = d[1:-1].strip()
    d = re.sub(r"::[a-z ]+(\[\])?$", "", d, flags=re.I)
    java = jt["java"]
    if java == "Boolean":
        if d.upper() in ("TRUE", "1", "'Y'", "'T'", "'1'"):
            return "Boolean.TRUE"
        if d.upper() in ("FALSE", "0", "'N'", "'F'", "'0'"):
            return "Boolean.FALSE"
    if re.fullmatch(r"-?\d+(\.\d+)?", d):
        if java == "BigDecimal":
            return "BigDecimal.ZERO" if float(d) == 0 else f'new BigDecimal("{d}")'
        if java == "Long":
            return d + "L"
        if java == "Integer":
            return d
        if java == "Short":
            return f"(short) {d}"
        if java in ("Double", "Float"):
            return d + ("d" if java == "Double" else "f")
    if java == "String" and re.fullmatch(r"'(?:[^']|'')*'", d):
        return '"' + d[1:-1].replace("''", "'").replace("\\", "\\\\").replace('"', '\\"') + '"'
    if java == "ENUM" and re.fullmatch(r"'(?:[^']|'')*'", d):
        return {"enum_value": d[1:-1].replace("''", "'")}
    return None


def _collect_enums(plan, cfg):
    """One Java enum per distinct value set; generic field names are prefixed with the entity name."""
    overrides = {k.lower(): v for k, v in (cfg.get("enum_names") or {}).items()}
    by_name = {}
    classes = {e["class"] for e in plan["entities"]}
    for ent in plan["entities"]:
        for f in ent["fields"]:
            if f["java"] != "ENUM":
                continue
            e = f["enum"]
            key = f"{ent['table']}.{f['column']}".lower()
            if e["source"] == "pg":
                name = overrides.get(key) or pascal(e["type"])
            else:
                fname = camel(f["column"])
                name = overrides.get(key) or (ent["class"] + pascal(fname) if fname.lower() in GENERIC_ENUM_FIELDS
                                              else pascal(fname))
            if name in classes:
                name += "Type"
            values = e["values"]
            existing = by_name.get(name)
            if existing and existing["values"] != values:
                name = ent["class"] + name
                existing = by_name.get(name)
            if existing is None:
                consts = [_constant(v) for v in values]
                exact = all(c == v for c, v in zip(consts, values)) and len(set(consts)) == len(consts)
                if len(set(consts)) != len(consts):
                    consts = [f"{c}_{i}" for i, c in enumerate(consts)]
                existing = {"name": name, "values": values, "constants": consts,
                            "mode": "named" if e["source"] == "pg" else ("string" if exact else "converter"),
                            "used_by": []}
                by_name[name] = existing
            existing["used_by"].append(f"{ent['class']}.{f['name']}")
            f["java"] = name
            f["enum_mode"] = existing["mode"]
            if isinstance(f.get("initial"), dict):
                v = f["initial"]["enum_value"]
                f["initial"] = f"{name}.{existing['constants'][values.index(v)]}" if v in values else None
    plan["enums"] = list(by_name.values())
    for en in plan["enums"]:
        if en["mode"] == "converter":
            plan["converters"].append(en["name"] + "Converter")


def _constant(value):
    c = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_").upper()
    if not c:
        c = "EMPTY"
    if c[0].isdigit():
        c = "V_" + c
    return c


def _schema_warnings(schema, classes, plan):
    """Schema smells worth fixing on the database side."""
    for t in schema["tables"]:
        idx_heads = [[c.lower() for c in i["columns"] if c] for i in t["indexes"]]
        if t["pk"]:
            idx_heads.append([c.lower() for c in t["pk"]["columns"] if c])
        idx_heads += [[c.lower() for c in u["columns"] if c] for u in t["uniques"]]
        for fk in t["fks"]:
            cols = [c.lower() for c in fk["columns"]]
            if not any(h[:len(cols)] == cols for h in idx_heads):
                plan["warnings"].append(
                    f"{t['name']}: foreign key {fk['name'] or '(' + ', '.join(fk['columns']) + ')'} has no index "
                    f"starting with its columns: deletes on {fk['ref_table']} lock or scan {t['name']}; "
                    f"CREATE INDEX ON {t['name']} ({', '.join(fk['columns'])})")
        fk_cols = {c.lower() for fk in t["fks"] for c in fk["columns"]}
        for col in t["columns"]:
            low = col["name"].lower()
            if low.endswith("_id") and low not in fk_cols and not (t["pk"] and low in
                                                                   [c.lower() for c in t["pk"]["columns"] if c]):
                ref = low[:-3]
                if ref in classes or ref + "s" in classes:
                    plan["warnings"].append(f"{t['name']}.{col['name']}: looks like a reference to {ref} but has "
                                            f"no foreign key constraint: mapped as a plain field")
            t_ = col["type"]
            if t_["base"] in ("varchar",) and col["type"].get("length_semantics") == "BYTE":
                plan["warnings"].append(f"{t['name']}.{col['name']}: VARCHAR2 length in BYTE: @Size counts "
                                        f"characters, multi-byte text can still overflow")
