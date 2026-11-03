"""Render a mapping plan (mapping.py) as Java 21 sources: entities, embeddable ids, enums, converters,
DTO records with Bean Validation, MapStruct or plain mappers, and Spring Data repositories."""
import re

IMPORTS = {
    **{n: "jakarta.persistence." + n for n in (
        "AttributeConverter", "CascadeType", "Column", "Convert", "Converter", "Embeddable", "EmbeddedId", "Entity",
        "EnumType", "Enumerated", "FetchType", "ForeignKey", "GeneratedValue", "GenerationType", "Id", "Index",
        "JoinColumn", "JoinColumns", "JoinTable", "Lob", "ManyToMany", "ManyToOne", "MapsId", "OneToMany",
        "OneToOne", "SequenceGenerator", "Table", "UniqueConstraint", "Version")},
    "JdbcTypeCode": "org.hibernate.annotations.JdbcTypeCode", "SqlTypes": "org.hibernate.type.SqlTypes",
    "CreationTimestamp": "org.hibernate.annotations.CreationTimestamp",
    "UpdateTimestamp": "org.hibernate.annotations.UpdateTimestamp",
    "Generated": "org.hibernate.annotations.Generated", "EventType": "org.hibernate.generator.EventType",
    "YesNoConverter": "org.hibernate.type.YesNoConverter", "TrueFalseConverter": "org.hibernate.type.TrueFalseConverter",
    "NumericBooleanConverter": "org.hibernate.type.NumericBooleanConverter",
    "BigDecimal": "java.math.BigDecimal", "BigInteger": "java.math.BigInteger",
    **{n: "java.time." + n for n in ("Duration", "Instant", "LocalDate", "LocalDateTime", "LocalTime",
                                     "OffsetDateTime", "OffsetTime")},
    **{n: "java.util." + n for n in ("ArrayList", "HashSet", "List", "Objects", "Optional", "Set", "UUID")},
    "Serializable": "java.io.Serializable", "Serial": "java.io.Serial",
    **{n: "jakarta.validation.constraints." + n for n in ("DecimalMax", "DecimalMin", "Digits", "Max", "Min",
                                                          "NotEmpty", "NotNull", "Positive", "PositiveOrZero",
                                                          "Size")},
    **{n: "org.mapstruct." + n for n in ("Mapper", "Mapping", "MappingConstants", "MappingTarget",
                                         "NullValueCheckStrategy", "NullValuePropertyMappingStrategy",
                                         "ReportingPolicy")},
    "JpaRepository": "org.springframework.data.jpa.repository.JpaRepository",
    "Getter": "lombok.Getter", "Setter": "lombok.Setter", "AccessLevel": "lombok.AccessLevel",
}
INTEGRAL = {"Long", "Integer", "Short", "BigInteger"}


class JavaFile:
    def __init__(self, package, name):
        self.package, self.name, self.imports, self.lines = package, name, set(), []

    def use(self, *names):
        for n in names:
            self.imports.add(IMPORTS.get(n, n))

    def add(self, line=""):
        self.lines.append(line)

    def render(self):
        imports = sorted(i for i in self.imports if "." in i and i.rsplit(".", 1)[0] != self.package
                         and not i.startswith("java.lang."))
        groups = [[i for i in imports if not i.startswith(("java.", "javax."))],
                  [i for i in imports if i.startswith(("java.", "javax."))]]
        out = [f"package {self.package};", ""]
        for g in groups:
            if g:
                out += [f"import {i};" for i in g] + [""]
        body = "\n".join(self.lines).rstrip() + "\n"
        return "\n".join(out) + "\n" + body


def q(name, quoted):
    """SQL identifier inside a Java string literal (quoted identifiers keep their case)."""
    return '\\"' + name + '\\"' if quoted else name


def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def cap(s):
    return s[0].upper() + s[1:]


def javadoc(f, text, indent="    "):
    text = re.sub(r"\s+", " ", text or "").strip().replace("*/", "* /")
    if text:
        f.add(f"{indent}/** {text if text.endswith('.') else text + '.'} */")


class Ctx:
    def __init__(self, plan, cfg):
        self.plan, self.cfg = plan, cfg
        base = cfg["base_package"]
        self.pkg = {"entity": cfg.get("entity_package") or base + ".entity",
                    "dto": cfg.get("dto_package") or base + ".dto",
                    "mapper": cfg.get("mapper_package") or base + ".mapper",
                    "repository": cfg.get("repository_package") or base + ".repository"}
        self.entities = {e["class"]: e for e in plan["entities"]}
        self.enums = {e["name"]: e for e in plan["enums"]}
        self.lombok = cfg.get("lombok")

    def entity_import(self, f, cls):
        f.use(self.pkg["entity"] + "." + cls)

    def type_use(self, f, java):
        """Register imports for a Java type expression such as List<UUID> or an enum of the entity package."""
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", java):
            if tok in IMPORTS:
                f.use(tok)
            elif tok in self.enums or tok in self.entities or tok.endswith("Id") and tok[:-2] in self.entities:
                self.entity_import(f, tok)


# ---------------------------------------------------------------------------------------------------- entity

def id_field_name(ent):
    return ent["id"]["field"]["name"] if ent["id"]["kind"] == "simple" else "id"


def id_type(ent):
    return ent["id"]["java"]


def column_annotation(f, fld, extra=None, quoted_key="quoted"):
    attrs = [f'name = "{q(fld["column"], fld.get(quoted_key))}"']
    if fld.get("nullable") is False:
        attrs.append("nullable = false")
    if fld.get("length") and (fld["java"] == "String" or fld.get("enum_mode") in ("string", "converter")):
        attrs.append(f"length = {fld['length']}")
    if fld.get("precision") and fld["java"] == "BigDecimal":
        attrs.append(f"precision = {fld['precision']}")
        attrs.append(f"scale = {fld.get('scale') or 0}")
    if fld.get("column_definition"):
        attrs.append(f"columnDefinition = {lit(fld['column_definition'])}")
    attrs += extra or []
    f.use("Column")
    return "@Column(" + ", ".join(attrs) + ")"


def render_entity(ctx, ent):
    f = JavaFile(ctx.pkg["entity"], ent["class"])
    f.use("Entity", "Table")
    javadoc(f, (ent["comment"] + ". " if ent["comment"] else "") + f"Maps table {ent['table']}", indent="")
    f.add("@Entity")
    table_attrs = [f'name = "{q(ent["table"], ent["quoted"])}"']
    if ent["schema"] and ctx.cfg.get("schema_in_annotations"):
        table_attrs.append(f'schema = "{ent["schema"]}"')
    if ent["uniques"]:
        f.use("UniqueConstraint")
        items = []
        for u in ent["uniques"]:
            cols = ", ".join(lit(c) for c in u["columns"])
            cols = cols if len(u["columns"]) == 1 else "{" + cols + "}"
            items.append(f"@UniqueConstraint({'name = ' + lit(u['name']) + ', ' if u['name'] else ''}"
                         f"columnNames = {cols})")
        table_attrs.append("uniqueConstraints = " + _array(items))
    if ent["indexes"]:
        f.use("Index")
        items = [f"@Index({'name = ' + lit(i['name']) + ', ' if i['name'] else ''}"
                 f"columnList = {lit(', '.join(i['columns']))})" for i in ent["indexes"]]
        table_attrs.append("indexes = " + _array(items))
    f.add("@Table(" + _join_attrs(table_attrs) + ")")
    if ctx.lombok:
        f.use("Getter", "Setter")
        f.add("@Getter")
        f.add("@Setter")
    serializable = any(not a["references_pk"] and a["target"] == ent["class"]
                       for e in ctx.plan["entities"] for a in e["associations"])
    if serializable:
        f.use("Serializable")
    f.add(f"public class {ent['class']}{' implements Serializable' if serializable else ''} {{")
    f.add()
    if serializable:
        f.use("Serial")
        f.add("    @Serial")
        f.add("    private static final long serialVersionUID = 1L;")
        f.add()
    members = []  # (name, type, getter, setter)
    _render_id(ctx, f, ent, members)
    for fld in ent["fields"]:
        _render_field(ctx, f, ent, fld, members)
    for a in ent["associations"]:
        _render_association(ctx, f, ent, a, members)
    for m in ent["many_to_many"]:
        _render_many_to_many(ctx, f, ent, m, members)
    for inv in ent["inverse"]:
        _render_inverse(ctx, f, ent, inv, members)
    f.add(f"    public {ent['class']}() {{")
    f.add("    }")
    f.add()
    if not ctx.lombok:
        for name, typ, getter, setter in members:
            if getter:
                f.add(f"    public {typ} {_getter(name, typ)}() {{")
                f.add(f"        return {name};")
                f.add("    }")
                f.add()
            if setter:
                f.add(f"    public void set{cap(name)}({typ} {name}) {{")
                f.add(f"        this.{name} = {name};")
                f.add("    }")
                f.add()
    _render_helpers(ctx, f, ent)
    _render_equals(f, ent)
    f.add("}")
    return f


def _array(items):
    if len(items) == 1:
        return items[0]
    return "{\n                " + ",\n                ".join(items) + "}"


def _join_attrs(attrs):
    if sum(len(a) for a in attrs) < 80 and not any("\n" in a for a in attrs):
        return ", ".join(attrs)
    return ("\n        " + ",\n        ".join(attrs))


def _getter(name, typ):
    return ("is" if typ == "boolean" else "get") + cap(name)


def _render_id(ctx, f, ent, members):
    idinfo = ent["id"]
    if idinfo["kind"] == "embedded":
        f.use("EmbeddedId")
        f.add("    @EmbeddedId")
        f.add(f"    private {idinfo['class']} id = new {idinfo['class']}();")
        f.add()
        members.append(("id", idinfo["class"], True, True))
        return
    fld = idinfo["field"]
    shared = any(a.get("maps_id") == "" for a in ent["associations"])
    javadoc(f, fld.get("comment"))
    f.use("Id")
    f.add("    @Id")
    gen = idinfo["generation"]
    if gen:
        f.use("GeneratedValue", "GenerationType")
        if gen["strategy"] == "SEQUENCE":
            f.use("SequenceGenerator")
            gname = ent["class"][0].lower() + ent["class"][1:] + "IdGenerator"
            f.add(f'    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "{gname}")')
            f.add(f'    @SequenceGenerator(name = "{gname}", sequenceName = "{gen["sequence"]}", '
                  f'allocationSize = {gen["allocation"]})')
        else:
            f.add(f"    @GeneratedValue(strategy = GenerationType.{gen['strategy']})")
    if fld.get("jdbc"):
        f.use("JdbcTypeCode", "SqlTypes")
        f.add(f"    @JdbcTypeCode(SqlTypes.{fld['jdbc']})")
    if not shared:
        f.add("    " + column_annotation(f, dict(fld, nullable=False)))
    ctx.type_use(f, fld["java"])
    f.add(f"    private {fld['java']} {fld['name']};")
    f.add()
    writable = gen is None and not shared
    if ctx.lombok and not writable:
        _lombok_no_setter(f)
    members.append((fld["name"], fld["java"], True, writable))


def _render_field(ctx, f, ent, fld, members):
    javadoc(f, fld.get("comment"))
    ann = []
    extra = []
    if fld["version"]:
        f.use("Version")
        ann.append("@Version")
    if fld["creation"] and ctx.cfg.get("timestamps") == "hibernate":
        f.use("CreationTimestamp")
        ann.append("@CreationTimestamp")
        extra.append("updatable = false")
    if fld["update"] and ctx.cfg.get("timestamps") == "hibernate":
        f.use("UpdateTimestamp")
        ann.append("@UpdateTimestamp")
    if fld["computed"]:
        f.use("Generated", "EventType")
        ann.append("@Generated(event = {EventType.INSERT, EventType.UPDATE})")
        extra += ["insertable = false", "updatable = false"]
    if fld["lob"]:
        f.use("Lob")
        ann.append("@Lob")
    mode = fld.get("enum_mode")
    if mode in ("string", "named"):
        f.use("Enumerated", "EnumType")
        ann.append("@Enumerated(EnumType.STRING)")
        if mode == "named":
            f.use("JdbcTypeCode", "SqlTypes")
            ann.append("@JdbcTypeCode(SqlTypes.NAMED_ENUM)")
    elif mode == "converter":
        f.use("Convert")
        ann.append(f"@Convert(converter = {fld['java']}Converter.class)")
    if fld.get("converter"):
        f.use("Convert", fld["converter"])
        ann.append(f"@Convert(converter = {fld['converter']}.class)")
    if fld.get("jdbc"):
        f.use("JdbcTypeCode", "SqlTypes")
        ann.append(f"@JdbcTypeCode(SqlTypes.{fld['jdbc']})")
    for a in ann:
        f.add("    " + a)
    f.add("    " + column_annotation(f, fld, extra))
    ctx.type_use(f, fld["java"])
    init = f" = {fld['initial']}" if isinstance(fld.get("initial"), str) else ""
    if "BigDecimal" in init:
        f.use("BigDecimal")
    f.add(f"    private {fld['java']} {fld['name']}{init};")
    f.add()
    writable = not (fld["version"] or fld["computed"] or (fld["creation"] or fld["update"]) and
                    ctx.cfg.get("timestamps") == "hibernate")
    if ctx.lombok and not writable:
        _lombok_no_setter(f)
    members.append((fld["name"], fld["java"], True, writable))


def _lombok_no_setter(f):
    f.use("Setter", "AccessLevel")
    f.lines.insert(len(f.lines) - 2, "    @Setter(AccessLevel.NONE)")


def _join_column(f, jc, nullable, read_only, fk_name=None, with_ref=False, with_fk=True):
    attrs = [f'name = "{jc["name"]}"']
    if with_ref and jc.get("referenced"):
        attrs.append(f'referencedColumnName = "{jc["referenced"]}"')
    if not nullable:
        attrs.append("nullable = false")
    if read_only:
        attrs += ["insertable = false", "updatable = false"]
    if fk_name and with_fk:
        f.use("ForeignKey")
        attrs.append(f'foreignKey = @ForeignKey(name = "{fk_name}")')
    f.use("JoinColumn")
    return "@JoinColumn(" + ", ".join(attrs) + ")"


def _render_association(ctx, f, ent, a, members):
    f.use(a["kind"], "FetchType")
    if a["maps_id"] is not None:
        f.use("MapsId")
        f.add('    @MapsId' + (f'("{a["maps_id"]}")' if a["maps_id"] else ""))
    f.add(f"    @{a['kind']}(fetch = FetchType.LAZY{'' if a['optional'] else ', optional = false'})")
    target = ctx.entities.get(a["target"])
    with_ref = len(a["join_columns"]) > 1 or not a["references_pk"]
    if len(a["join_columns"]) == 1:
        f.add("    " + _join_column(f, a["join_columns"][0], a["optional"], a["read_only"], a["fk_name"],
                                    with_ref=with_ref))
    else:
        f.use("JoinColumns")
        cols = [_join_column(f, jc, a["optional"], a["read_only"], with_ref=True, with_fk=False)
                for jc in a["join_columns"]]
        fk = ""
        if a["fk_name"]:
            f.use("ForeignKey")
            fk = f',\n            foreignKey = @ForeignKey(name = "{a["fk_name"]}")'
        f.add("    @JoinColumns(value = {\n            " + ",\n            ".join(cols) + "}" + fk + ")")
    f.add(f"    private {a['target']} {a['name']};")
    f.add()
    members.append((a["name"], a["target"], True, True))
    del target


def _render_many_to_many(ctx, f, ent, m, members):
    f.use("ManyToMany", "JoinTable", "Set", "HashSet")
    f.add("    @ManyToMany")
    jcs = [_join_column(f, jc, False, False, m["fk_name"] if len(m["join_columns"]) == 1 else None,
                        with_ref=len(m["join_columns"]) > 1) for jc in m["join_columns"]]
    ijcs = [_join_column(f, jc, False, False, m["inverse_fk_name"] if len(m["inverse_join_columns"]) == 1 else None,
                         with_ref=len(m["inverse_join_columns"]) > 1) for jc in m["inverse_join_columns"]]
    jt = f'name = "{q(m["join_table"], m["join_table_quoted"])}"'
    if m.get("schema") and ctx.cfg.get("schema_in_annotations"):
        jt += f', schema = "{m["schema"]}"'
    f.add(f"    @JoinTable({jt},")
    f.add("            joinColumns = " + (jcs[0] if len(jcs) == 1 else "{" + ", ".join(jcs) + "}") + ",")
    f.add("            inverseJoinColumns = " + (ijcs[0] if len(ijcs) == 1 else "{" + ", ".join(ijcs) + "}") + ")")
    f.add(f"    private Set<{m['target']}> {m['name']} = new HashSet<>();")
    f.add()
    if ctx.lombok:
        _lombok_no_setter(f)
    members.append((m["name"], f"Set<{m['target']}>", True, False))


def _render_inverse(ctx, f, ent, inv, members):
    f.use("OneToMany", "List", "ArrayList")
    if inv["composition"]:
        f.use("CascadeType")
        f.add(f'    @OneToMany(mappedBy = "{inv["mapped_by"]}", cascade = CascadeType.ALL, orphanRemoval = true)')
    else:
        f.add(f'    @OneToMany(mappedBy = "{inv["mapped_by"]}")')
    f.add(f"    private List<{inv['target']}> {inv['name']} = new ArrayList<>();")
    f.add()
    if ctx.lombok:
        _lombok_no_setter(f)
    members.append((inv["name"], f"List<{inv['target']}>", True, False))


def _singular_name(collection, target):
    base = collection
    for suffix, rep in (("ies", "y"), ("ses", "s"), ("xes", "x"), ("s", "")):
        if base.endswith(suffix):
            return base[: len(base) - len(suffix)] + rep
    return target[0].lower() + target[1:]


def _render_helpers(ctx, f, ent):
    for inv in ent["inverse"]:
        if not inv["composition"]:
            continue
        one = _singular_name(inv["name"], inv["target"])
        var = inv["target"][0].lower() + inv["target"][1:]
        f.add(f"    /** Adds a {var} and sets its {inv['mapped_by']}: keeps both sides in sync. */")
        f.add(f"    public void add{cap(one)}({inv['target']} {var}) {{")
        f.add(f"        {inv['name']}.add({var});")
        f.add(f"        {var}.set{cap(inv['mapped_by'])}(this);")
        f.add("    }")
        f.add()
        f.add(f"    /** Removes a {var}; orphan removal deletes it at flush. */")
        f.add(f"    public void remove{cap(one)}({inv['target']} {var}) {{")
        f.add(f"        {inv['name']}.remove({var});")
        f.add(f"        {var}.set{cap(inv['mapped_by'])}(null);")
        f.add("    }")
        f.add()
    for m in ent["many_to_many"]:
        one = _singular_name(m["name"], m["target"])
        var = m["target"][0].lower() + m["target"][1:]
        f.add(f"    public void add{cap(one)}({m['target']} {var}) {{")
        f.add(f"        {m['name']}.add({var});")
        f.add("    }")
        f.add()
        f.add(f"    public void remove{cap(one)}({m['target']} {var}) {{")
        f.add(f"        {m['name']}.remove({var});")
        f.add("    }")
        f.add()


def _render_equals(f, ent):
    cls, idn = ent["class"], id_field_name(ent)
    getter = "get" + cap(idn) + "()"
    f.add("    /** Identity is the primary key: two instances are equal once persisted with the same id. */")
    f.add("    @Override")
    f.add("    public boolean equals(Object o) {")
    f.add("        if (this == o) {")
    f.add("            return true;")
    f.add("        }")
    f.add(f"        if (!(o instanceof {cls} other)) {{")
    f.add("            return false;")
    f.add("        }")
    if ent["id"]["kind"] == "embedded":
        f.add(f"        {ent['id']['class']} key = {getter};")
        checks = " && ".join(f"key.get{cap(x['name'])}() != null" for x in ent["id"]["fields"])
        f.add(f"        return key != null && {checks} && key.equals(other.{getter});")
    else:
        f.add(f"        return {getter} != null && {getter}.equals(other.{getter});")
    f.add("    }")
    f.add()
    f.add("    /** Constant per class, so the hash does not change when the id is assigned at persist. */")
    f.add("    @Override")
    f.add("    public int hashCode() {")
    f.add(f"        return {cls}.class.hashCode();")
    f.add("    }")
    f.add()
    f.add("    /** Only the id: no personal data in logs, no lazy association loaded. */")
    f.add("    @Override")
    f.add("    public String toString() {")
    f.add(f'        return "{cls}{{{idn}=" + {getter} + "}}";')
    f.add("    }")


def render_embedded_id(ctx, ent):
    idinfo = ent["id"]
    f = JavaFile(ctx.pkg["entity"], idinfo["class"])
    f.use("Embeddable", "Serializable", "Serial", "Objects")
    f.add(f"/** Composite primary key of {ent['table']}. */")
    f.add("@Embeddable")
    f.add(f"public class {idinfo['class']} implements Serializable {{")
    f.add()
    f.add("    @Serial")
    f.add("    private static final long serialVersionUID = 1L;")
    f.add()
    for fld in idinfo["fields"]:
        if fld.get("jdbc"):
            f.use("JdbcTypeCode", "SqlTypes")
            f.add(f"    @JdbcTypeCode(SqlTypes.{fld['jdbc']})")
        f.add("    " + column_annotation(f, dict(fld, nullable=False)))
        ctx.type_use(f, fld["java"])
        f.add(f"    private {fld['java']} {fld['name']};")
        f.add()
    f.add(f"    public {idinfo['class']}() {{")
    f.add("    }")
    f.add()
    params = ", ".join(f"{x['java']} {x['name']}" for x in idinfo["fields"])
    f.add(f"    public {idinfo['class']}({params}) {{")
    for x in idinfo["fields"]:
        f.add(f"        this.{x['name']} = {x['name']};")
    f.add("    }")
    f.add()
    for x in idinfo["fields"]:
        f.add(f"    public {x['java']} get{cap(x['name'])}() {{")
        f.add(f"        return {x['name']};")
        f.add("    }")
        f.add()
        f.add(f"    public void set{cap(x['name'])}({x['java']} {x['name']}) {{")
        f.add(f"        this.{x['name']} = {x['name']};")
        f.add("    }")
        f.add()
    names = [x["name"] for x in idinfo["fields"]]
    f.add("    @Override")
    f.add("    public boolean equals(Object o) {")
    f.add("        if (this == o) {")
    f.add("            return true;")
    f.add("        }")
    f.add(f"        if (!(o instanceof {idinfo['class']} other)) {{")
    f.add("            return false;")
    f.add("        }")
    f.add("        return " + "\n                && ".join(f"Objects.equals({n}, other.{n})" for n in names) + ";")
    f.add("    }")
    f.add()
    f.add("    @Override")
    f.add("    public int hashCode() {")
    f.add(f"        return Objects.hash({', '.join(names)});")
    f.add("    }")
    f.add()
    f.add("    @Override")
    f.add("    public String toString() {")
    parts = ' + ", '.join(f'{n}=" + {n}' for n in names)
    f.add(f'        return "{idinfo["class"]}{{{parts} + "}}";')
    f.add("    }")
    f.add("}")
    return f


def render_enum(ctx, en):
    f = JavaFile(ctx.pkg["entity"], en["name"])
    f.add(f"/** Values allowed by the database for {', '.join(en['used_by'])}. */")
    f.add(f"public enum {en['name']} {{")
    if en["mode"] == "converter":
        items = [f"    {c}({lit(v)})" for c, v in zip(en["constants"], en["values"])]
        f.add(",\n".join(items) + ";")
        f.add()
        f.add("    private final String code;")
        f.add()
        f.add(f"    {en['name']}(String code) {{")
        f.add("        this.code = code;")
        f.add("    }")
        f.add()
        f.add("    /** Value stored in the database. */")
        f.add("    public String code() {")
        f.add("        return code;")
        f.add("    }")
        f.add()
        f.add(f"    public static {en['name']} fromCode(String code) {{")
        f.add(f"        for ({en['name']} value : values()) {{")
        f.add("            if (value.code.equals(code)) {")
        f.add("                return value;")
        f.add("            }")
        f.add("        }")
        f.add(f'        throw new IllegalArgumentException("Unknown {en["name"]} code: " + code);')
        f.add("    }")
    else:
        f.add("    " + ",\n    ".join(en["constants"]))
    f.add("}")
    return f


def render_converter(ctx, en):
    name = en["name"] + "Converter"
    f = JavaFile(ctx.pkg["entity"], name)
    f.use("AttributeConverter", "Converter")
    f.add(f"/** Stores {en['name']} as its database code. */")
    f.add("@Converter")
    f.add(f"public class {name} implements AttributeConverter<{en['name']}, String> {{")
    f.add()
    f.add("    @Override")
    f.add(f"    public String convertToDatabaseColumn({en['name']} value) {{")
    f.add("        return value == null ? null : value.code();")
    f.add("    }")
    f.add()
    f.add("    @Override")
    f.add(f"    public {en['name']} convertToEntityAttribute(String code) {{")
    f.add(f"        return code == null ? null : {en['name']}.fromCode(code);")
    f.add("    }")
    f.add("}")
    return f


# ---------------------------------------------------------------------------------------------------- DTOs

def dto_components(ctx, ent, for_request):
    """List of (name, java type, annotations, source path, entity target) for DTO records and mappers."""
    comps = []
    idinfo = ent["id"]
    shared = next((a for a in ent["associations"] if a.get("maps_id") == ""), None)
    if idinfo["kind"] == "simple":
        fld = idinfo["field"]
        generated = idinfo["generation"] is not None
        if not (for_request and generated):
            ann = []
            if for_request:
                ann += _not_null(ctx, fld, required=True)
                ann += _size(fld)
            name = fld["name"]
            if shared and name == "id":
                name = shared["name"] + "Id"
            # a shared primary key comes from the association (@MapsId): the service sets the association
            comps.append({"name": name, "java": fld["java"], "ann": ann, "source": fld["name"],
                          "target": fld["name"], "kind": "shared_id" if shared else "id"})
    else:
        for x in idinfo["fields"]:
            ann = []
            if for_request:
                ann += _not_null(ctx, x, required=True) + _size(x)
            comps.append({"name": x["name"], "java": x["java"], "ann": ann, "source": f"id.{x['name']}",
                          "target": f"id.{x['name']}", "kind": "id"})
    for fld in ent["fields"]:
        if for_request and (fld["version"] or fld["computed"] or ((fld["creation"] or fld["update"]) and
                                                                  ctx.cfg.get("timestamps") == "hibernate")):
            continue
        ann = []
        if for_request:
            required = not fld["nullable"] and fld.get("initial") is None
            ann += _not_null(ctx, fld, required)
            ann += _size(fld) + _digits(fld) + _rules(fld)
        comps.append({"name": fld["name"], "java": fld["java"], "ann": ann, "source": fld["name"],
                      "target": fld["name"], "kind": "field"})
    for a in ent["associations"]:
        if a.get("maps_id") is not None:
            continue  # represented by the identifier
        target = ctx.entities[a["target"]]
        tid = target["id"]
        if tid["kind"] == "simple":
            name = _fk_field_name(a["join_columns"][0]["name"]) if len(a["join_columns"]) == 1 else \
                a["name"] + "Id"
            ann = ["@NotNull"] if for_request and not a["optional"] else []
            comps.append({"name": name, "java": tid["java"], "ann": ann,
                          "source": f"{a['name']}.{tid['field']['name']}", "target": a["name"], "kind": "assoc"})
        else:
            for x in tid["fields"]:
                ann = ["@NotNull"] if for_request and not a["optional"] else []
                comps.append({"name": a["name"] + cap(x["name"]), "java": x["java"], "ann": ann,
                              "source": f"{a['name']}.id.{x['name']}", "target": a["name"], "kind": "assoc"})
    for m in ent["many_to_many"]:
        target = ctx.entities[m["target"]]
        if target["id"]["kind"] != "simple":
            continue
        name = _singular_name(m["name"], m["target"]) + "Ids"
        comps.append({"name": name, "java": f"Set<{target['id']['java']}>", "ann": [], "source": m["name"],
                      "target": m["name"], "kind": "m2m", "element": target["id"]["java"],
                      "element_getter": "get" + cap(target["id"]["field"]["name"]), "target_class": m["target"]})
    return comps


def _fk_field_name(column):
    from mapping import camel
    return camel(column)


def _not_null(ctx, fld, required):
    if not required:
        return []
    if fld.get("oracle_not_empty") and fld["java"] == "String":
        return ["@NotEmpty"]  # Oracle stores '' as NULL: an empty string breaks NOT NULL
    return ["@NotNull"]


def _size(fld):
    if fld["java"] == "String" and fld.get("length") and not fld.get("lob"):
        return [f"@Size(max = {fld['length']})"]
    return []


def _digits(fld):
    if fld["java"] == "BigDecimal" and fld.get("precision"):
        s = fld.get("scale") or 0
        return [f"@Digits(integer = {fld['precision'] - s}, fraction = {s})"]
    return []


def _rules(fld):
    out = []
    integral = fld["java"] in INTEGRAL
    for r in fld.get("rules") or []:
        k = r["kind"]
        if k in ("Positive", "PositiveOrZero"):
            out.append("@" + k)
        elif k == "Min":
            out.append(f"@Min({_int_bound(r['value'], r['inclusive'], 1)})" if integral else
                       f'@DecimalMin(value = "{r["value"]}", inclusive = {str(r["inclusive"]).lower()})')
        elif k == "Max":
            out.append(f"@Max({_int_bound(r['value'], r['inclusive'], -1)})" if integral else
                       f'@DecimalMax(value = "{r["value"]}", inclusive = {str(r["inclusive"]).lower()})')
        elif k == "Range":
            out += ([f"@Min({r['min']})", f"@Max({r['max']})"] if integral else
                    [f'@DecimalMin("{r["min"]}")', f'@DecimalMax("{r["max"]}")'])
        elif k == "SizeMin" and fld["java"] == "String":
            out.append(f"@Size(min = {r['value']})")
    return out


def _int_bound(value, inclusive, step):
    v = int(float(value))
    return v if inclusive else v + step


def render_dto(ctx, ent, request):
    name = ent["class"] + ("Request" if request else "Dto")
    f = JavaFile(ctx.pkg["dto"], name)
    comps = dto_components(ctx, ent, request)
    what = "Data accepted to create or update" if request else "Read model of"
    f.add(f"/** {what} {ent['class']} (table {ent['table']}). */")
    lines = []
    for c in comps:
        ctx.type_use(f, c["java"])
        for a in c["ann"]:
            f.use(re.match(r"@(\w+)", a).group(1))
        prefix = " ".join(c["ann"])
        lines.append(f"        {prefix + ' ' if prefix else ''}{c['java']} {c['name']}")
    f.add(f"public record {name}(")
    f.add(",\n".join(lines) + ") {")
    f.add("}")
    return f


# ---------------------------------------------------------------------------------------------------- mappers

def render_mapstruct(ctx, ent):
    name = ent["class"] + "Mapper"
    f = JavaFile(ctx.pkg["mapper"], name)
    f.use("Mapper", "Mapping", "MappingConstants", "MappingTarget", "ReportingPolicy", "NullValueCheckStrategy",
          "NullValuePropertyMappingStrategy")
    ctx.entity_import(f, ent["class"])
    f.use(ctx.pkg["dto"] + "." + ent["class"] + "Dto", ctx.pkg["dto"] + "." + ent["class"] + "Request")
    read = dto_components(ctx, ent, False)
    write = dto_components(ctx, ent, True)
    f.add(f"/**")
    f.add(f" * Maps {ent['class']} to its DTOs. Associations are set by the service from the ids of the request")
    f.add(f" * (repository.getReferenceById), never by the mapper. Null request values leave the entity unchanged.")
    f.add(f" */")
    f.add("@Mapper(componentModel = MappingConstants.ComponentModel.SPRING,")
    f.add("        unmappedTargetPolicy = ReportingPolicy.ERROR,")
    f.add("        nullValueCheckStrategy = NullValueCheckStrategy.ALWAYS,")
    f.add("        nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)")
    f.add(f"public interface {name} {{")
    f.add()
    for c in read:
        if c["source"] != c["name"]:
            f.add(f'    @Mapping(target = "{c["name"]}", source = "{c["source"]}")')
    f.add(f"    {ent['class']}Dto toDto({ent['class']} entity);")
    f.add()
    ignores = _write_ignores(ctx, ent, write)
    id_targets = [c for c in write if c["kind"] == "id"]
    for direction in ("toEntity", "updateEntity"):
        extra = []
        if direction == "toEntity":
            for c in id_targets:
                if c["target"] != c["name"]:
                    f.add(f'    @Mapping(target = "{c["target"]}", source = "{c["name"]}")')
        else:  # an update never changes the primary key
            extra = sorted({"id" if c["target"].startswith("id.") else c["target"] for c in id_targets})
        for t in extra + ignores:
            f.add(f'    @Mapping(target = "{t}", ignore = true)')
        if direction == "toEntity":
            f.add(f"    {ent['class']} toEntity({ent['class']}Request request);")
        else:
            f.add(f"    void updateEntity({ent['class']}Request request, @MappingTarget {ent['class']} entity);")
        f.add()
    seen = set()
    for c in read:
        if c["kind"] == "m2m" and c["target_class"] not in seen:
            seen.add(c["target_class"])
            ctx.entity_import(f, c["target_class"])
            ctx.type_use(f, c["element"])
            var = c["target_class"][0].lower() + c["target_class"][1:]
            f.add(f"    default {c['element']} {var}ToId({c['target_class']} {var}) {{")
            f.add(f"        return {var} == null ? null : {var}.{c['element_getter']}();")
            f.add("    }")
            f.add()
    f.lines[-1:] = [] if f.lines and f.lines[-1] == "" else f.lines[-1:]
    f.add("}")
    return f


def _write_ignores(ctx, ent, write):
    """Entity properties the request does not set: generated, managed, associations and collections."""
    written = {c["target"] for c in write if c["kind"] in ("field", "id")}
    out = []
    idinfo = ent["id"]
    if idinfo["kind"] == "simple":
        if idinfo["field"]["name"] not in written:
            out.append(idinfo["field"]["name"])
    else:
        out.append("id") if not any(t.startswith("id.") for t in written) else None
    for fld in ent["fields"]:
        if fld["name"] not in written:
            out.append(fld["name"])
    out += [a["name"] for a in ent["associations"]]
    out += [m["name"] for m in ent["many_to_many"]]
    out += [i["name"] for i in ent["inverse"]]
    return out


def render_manual_mapper(ctx, ent):
    name = ent["class"] + "Mapper"
    f = JavaFile(ctx.pkg["mapper"], name)
    ctx.entity_import(f, ent["class"])
    f.use(ctx.pkg["dto"] + "." + ent["class"] + "Dto", ctx.pkg["dto"] + "." + ent["class"] + "Request")
    read = dto_components(ctx, ent, False)
    write = dto_components(ctx, ent, True)
    f.add(f"/**")
    f.add(f" * Maps {ent['class']} to its DTOs. Associations are set by the service from the ids of the request")
    f.add(f" * (repository.getReferenceById). Null request values leave the entity unchanged.")
    f.add(f" */")
    f.add(f"public final class {name} {{")
    f.add()
    f.add(f"    private {name}() {{")
    f.add("    }")
    f.add()
    f.add(f"    public static {ent['class']}Dto toDto({ent['class']} entity) {{")
    f.add("        if (entity == null) {")
    f.add("            return null;")
    f.add("        }")
    args = []
    for c in read:
        expr = _manual_read(ctx, ent, c, f)
        args.append(expr)
    f.add(f"        return new {ent['class']}Dto(")
    f.add("                " + ",\n                ".join(args) + ");")
    f.add("    }")
    f.add()
    f.add(f"    public static {ent['class']} toEntity({ent['class']}Request request) {{")
    f.add(f"        {ent['class']} entity = new {ent['class']}();")
    for c in write:
        if c["kind"] != "id":
            continue
        setter = (f"entity.getId().set{cap(c['target'][3:])}" if c["target"].startswith("id.")
                  else f"entity.set{cap(c['target'])}")
        f.add(f"        {setter}(request.{c['name']}());")
    f.add("        updateEntity(request, entity);")
    f.add("        return entity;")
    f.add("    }")
    f.add()
    f.add("    /** Copies the non-null values of the request; the primary key never changes. */")
    f.add(f"    public static void updateEntity({ent['class']}Request request, {ent['class']} entity) {{")
    for c in write:
        if c["kind"] != "field":
            continue
        if c["target"].startswith("id."):
            setter = f"entity.getId().set{cap(c['target'][3:])}"
        else:
            setter = f"entity.set{cap(c['target'])}"
        f.add(f"        if (request.{c['name']}() != null) {{")
        f.add(f"            {setter}(request.{c['name']}());")
        f.add("        }")
    f.add("    }")
    f.add("}")
    if any(c["kind"] == "m2m" for c in read):
        f.use("java.util.stream.Collectors")
    return f


def _manual_read(ctx, ent, c, f):
    parts = c["source"].split(".")
    if c["kind"] == "m2m":
        ctx.entity_import(f, c["target_class"])
        return (f"entity.get{cap(c['source'])}().stream().map({c['target_class']}::{c['element_getter']})"
                f".collect(Collectors.toSet())")
    expr = "entity"
    if len(parts) == 1:
        return f"entity.get{cap(parts[0])}()"
    # nested path through an association or the embedded id: null-safe on the first hop
    first = f"entity.get{cap(parts[0])}()"
    rest = "".join(f".get{cap(p)}()" for p in parts[1:])
    del expr
    return f"{first} == null ? null : {first}{rest}"


def render_repository(ctx, ent):
    name = ent["class"] + "Repository"
    f = JavaFile(ctx.pkg["repository"], name)
    f.use("JpaRepository")
    ctx.entity_import(f, ent["class"])
    ctx.type_use(f, id_type(ent))
    f.add(f"public interface {name} extends JpaRepository<{ent['class']}, {id_type(ent)}> {{")
    finders = []
    for u in ent["uniques"]:
        if len(u["columns"]) != 1:
            continue
        fld = next((x for x in ent["fields"] if x["column"].lower() == u["columns"][0].lower()), None)
        if fld:
            finders.append(fld)
    if finders:
        f.use("Optional")
        f.add()
        for fld in finders:
            ctx.type_use(f, fld["java"])
            f.add(f"    Optional<{ent['class']}> findBy{cap(fld['name'])}({fld['java']} {fld['name']});")
    f.add("}")
    return f


def render_all(plan, cfg):
    ctx = Ctx(plan, cfg)
    files = []
    for ent in plan["entities"]:
        files.append(("entity", render_entity(ctx, ent)))
        if ent["id"]["kind"] == "embedded":
            files.append(("entity", render_embedded_id(ctx, ent)))
    for en in plan["enums"]:
        files.append(("entity", render_enum(ctx, en)))
        if en["mode"] == "converter":
            files.append(("entity", render_converter(ctx, en)))
    if cfg.get("dto", True):
        for ent in plan["entities"]:
            files.append(("dto", render_dto(ctx, ent, request=False)))
            files.append(("dto", render_dto(ctx, ent, request=True)))
        if cfg.get("mapper") == "mapstruct":
            for ent in plan["entities"]:
                files.append(("mapper", render_mapstruct(ctx, ent)))
        elif cfg.get("mapper") == "manual":
            for ent in plan["entities"]:
                files.append(("mapper", render_manual_mapper(ctx, ent)))
    if cfg.get("repositories", True):
        for ent in plan["entities"]:
            files.append(("repository", render_repository(ctx, ent)))
    return [(layer, f.package, f.name, f.render()) for layer, f in files]
