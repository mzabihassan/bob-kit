#!/usr/bin/env python3
"""Map Oracle or PostgreSQL DDL to Spring Boot JPA entities, DTO records, mappers and repositories.

  analyze  <sql files or folders...> --out <dir> [--dialect oracle|postgresql]
           Parses the scripts (folders: Flyway order, V1__ < V1_1__ < V2__ < R__), writes model.json, plan.json,
           config.json (kept if it exists) and mapping-report.md, and prints a short summary.
  generate --out <dir> --into <src/main/java> [--overwrite] [--dry-run]
           Builds the plan with <dir>/config.json and writes the Java sources under --into. Existing files that
           differ are reported as conflicts and left untouched unless --overwrite.

Read-only on the SQL scripts; writes only under --out and --into.
"""
import argparse
import json
import os
import re
import sys

sys.dont_write_bytecode = True  # never leave __pycache__ in the installed skill folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ddl_parser  # noqa: E402
import javagen  # noqa: E402
import mapping  # noqa: E402

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def flyway_key(path):
    name = os.path.basename(path)
    m = re.match(r"^[Vv](\d+(?:[._]\d+)*)__", name)
    if m:
        return (0, tuple(int(x) for x in re.split(r"[._]", m.group(1))), name)
    if re.match(r"^[Rr]__", name):
        return (2, (), name)
    return (1, (), name)


def collect(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            found = []
            for root, dirs, names in os.walk(p):
                dirs[:] = sorted(d for d in dirs if not d.startswith("."))
                found += [os.path.join(root, n) for n in names if n.lower().endswith(".sql")]
            files += sorted(found, key=flyway_key)
        elif os.path.isfile(p):
            files.append(p)
        else:
            raise SystemExit(f"error: {p} not found")
    if not files:
        raise SystemExit("error: no .sql file found")
    return files


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def load_config(out, dialect):
    path = os.path.join(out, "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        base = mapping.default_config(cfg.get("dialect") or dialect)
        base.update(cfg)
        return base, path, False
    return mapping.default_config(dialect), path, True


def validate_names(cfg):
    for key in ("class_names", "enum_names", "field_names"):
        for k, v in (cfg.get(key) or {}).items():
            if not IDENT.match(str(v)):
                raise mapping.ConfigError(f"{key}[{k}] = {v!r} is not a Java identifier")
    for key in ("entity_package", "dto_package", "mapper_package", "repository_package"):
        v = cfg.get(key)
        if v and not re.match(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$", v):
            raise mapping.ConfigError(f"{key} = {v!r} is not a lower-case Java package")


# ---------------------------------------------------------------------------------------------------- report

def report(plan, files, cfg, generated=None):
    out = ["# SQL to JPA mapping report", "",
           f"Dialect: {plan['dialect']}. Scripts: {', '.join(os.path.basename(f) for f in files)}.", ""]
    out += ["## Classes", "", "| Table | Class | Identifier | Generation |", "| --- | --- | --- | --- |"]
    for e in plan["entities"]:
        idinfo = e["id"]
        gen = idinfo["generation"]
        g = "assigned" if not gen else (f"{gen['strategy']} {gen.get('sequence', '')} "
                                        f"(allocationSize {gen['allocation']})".replace("  ", " ")
                                        if gen["strategy"] == "SEQUENCE" else gen["strategy"])
        if gen:
            g += f" - {gen['source']}"
        ident = (f"{idinfo['field']['name']}: {idinfo['java']}" if idinfo["kind"] == "simple"
                 else f"@EmbeddedId {idinfo['class']}")
        out.append(f"| {e['table']} | {e['class']} | {ident} | {g} |")
    out += ["", "## Relationships", "", "| Id (config key) | Mapping | Why |", "| --- | --- | --- |"]
    for r in plan["relations"]:
        out.append(f"| `{r['id']}` | {r['from']}.{r['field']} {r['kind']} {r['to']} | {r['why']} |")
    if plan["enums"]:
        out += ["", "## Enums", "", "| Enum | Values | Mapping | Used by |", "| --- | --- | --- | --- |"]
        for en in plan["enums"]:
            how = {"string": "@Enumerated(STRING)", "named": "PostgreSQL enum type (NAMED_ENUM)",
                   "converter": "AttributeConverter (codes differ from Java names)"}[en["mode"]]
            out.append(f"| {en['name']} | {', '.join(en['values'])} | {how} | {', '.join(en['used_by'])} |")
    managed = []
    for e in plan["entities"]:
        for f in e["fields"]:
            what = ("@Version (optimistic lock, no setter)" if f["version"] else
                    "computed by the database: read-only, refreshed after insert and update (@Generated)"
                    if f["computed"] else
                    "@CreationTimestamp, never updated" if f["creation"] and cfg.get("timestamps") == "hibernate" else
                    "@UpdateTimestamp" if f["update"] and cfg.get("timestamps") == "hibernate" else
                    f"initialised to {f['initial']} (database default {f['db_default']})"
                    if isinstance(f.get("initial"), str) else None)
            if what:
                managed.append(f"{e['class']}.{f['name']} ({f['column']}): {what}")
    sections = [("Managed columns (mapped, set automatically)", managed),
                ("Decisions to confirm", plan["decisions"]),
                ("Schema warnings (fix in the database)", plan["warnings"] +
                 [f"{e['class']}: {w}" for e in plan["entities"] for w in e["warnings"]]),
                ("Notes", plan["notes"]),
                ("Not mapped as entities", [f"{s['table']}: {s['reason']}" for s in plan["skipped"]])]
    for title, items in sections:
        if items:
            out += ["", f"## {title}", ""] + [f"- {i}" for i in items]
    if generated:
        out += ["", "## Generated files", ""] + [f"- {g}" for g in generated]
    return "\n".join(out) + "\n"


def summary(plan, cfg, out_dir, created_config):
    lines = [f"dialect {plan['dialect']}; {len(plan['entities'])} entities, {len(plan['enums'])} enums, "
             f"{len(plan['skipped'])} tables not mapped as entities"]
    for e in plan["entities"]:
        gen = e["id"]["generation"]
        g = gen["strategy"] if gen else "assigned"
        rel = [f"{a['name']}->{a['target']}({a['kind']})" for a in e["associations"]]
        rel += [f"{m['name']}->{m['target']}(ManyToMany)" for m in e["many_to_many"]]
        rel += [f"{i['name']}<-{i['target']}({'composition' if i['composition'] else 'inverse'})"
                for i in e["inverse"]]
        lines.append(f"  {e['table']} -> {e['class']} [id {g}] {'; '.join(rel)}")
    for s in plan["skipped"]:
        lines.append(f"  {s['table']}: {s['reason']}")
    inverse_on = {i["relation_id"] for e in plan["entities"] for i in e["inverse"]}
    keys = [f"{a['relation_id']}={'on' if a['relation_id'] in inverse_on else 'off'} ({a.get('relation_kind')})"
            for e in plan["entities"] for a in e["associations"] if a["kind"] == "ManyToOne"]
    if keys:
        lines.append("INVERSE KEYS (config \"inverse\": {\"<key>\": true|false} adds or removes the parent's "
                     "collection; composition = cascade + orphan removal): " + ", ".join(keys))
    if plan["decisions"]:
        lines.append("DECISIONS (set in config.json if the default is wrong):")
        lines += [f"  - {d}" for d in plan["decisions"]]
    warns = plan["warnings"] + [f"{e['class']}: {w}" for e in plan["entities"] for w in e["warnings"]]
    if warns:
        lines.append(f"WARNINGS ({len(warns)}, details in mapping-report.md):")
        lines += [f"  - {w}" for w in warns[:12]]
        if len(warns) > 12:
            lines.append(f"  - ... {len(warns) - 12} more")
    lines.append(f"config: {os.path.join(out_dir, 'config.json')}"
                 f"{' (created with defaults: set base_package, lombok, mapper)' if created_config else ''}")
    lines.append(f"report: {os.path.join(out_dir, 'mapping-report.md')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------- commands

def cmd_analyze(args):
    files = collect(args.sql)
    os.makedirs(args.out, exist_ok=True)
    schema = ddl_parser.parse_scripts([(os.path.basename(f), read(f)) for f in files])
    detected = ddl_parser.detect_dialect(schema)
    cfg, cfg_path, created = load_config(args.out, args.dialect or detected)
    if args.dialect:
        cfg["dialect"] = args.dialect
    if cfg.get("dialect") not in ("oracle", "postgresql"):
        raise SystemExit("error: the dialect cannot be detected from the scripts: pass --dialect oracle|postgresql")
    if detected and detected != cfg["dialect"]:
        print(f"warning: the scripts look like {detected} but the dialect is {cfg['dialect']}")
    model = schema.to_dict()
    model["files"] = files
    write_json(os.path.join(args.out, "model.json"), model)
    validate_names(cfg)
    plan = mapping.build_plan(model, cfg)
    write_json(os.path.join(args.out, "plan.json"), plan)
    if created:
        write_json(cfg_path, cfg)
    with open(os.path.join(args.out, "mapping-report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(plan, files, cfg))
    print(summary(plan, cfg, args.out, created))
    if model["ignored_statements"]:
        print("ignored statements: " + ", ".join(f"{k} x{v}" for k, v in sorted(model["ignored_statements"].items())))
    return 0


def cmd_generate(args):
    model_path = os.path.join(args.out, "model.json")
    if not os.path.exists(model_path):
        raise SystemExit(f"error: {model_path} missing: run analyze first")
    with open(model_path, encoding="utf-8") as fh:
        model = json.load(fh)
    cfg, _, created = load_config(args.out, None)
    if created:
        raise SystemExit("error: config.json missing: run analyze first")
    validate_names(cfg)
    plan = mapping.build_plan(model, cfg)
    sources = javagen.render_all(plan, cfg)
    into = os.path.abspath(args.into)
    stats = {"created": [], "updated": [], "unchanged": [], "conflict": []}
    for _layer, package, name, text in sources:
        rel = os.path.join(*package.split("."), name + ".java")
        path = os.path.join(into, rel)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                current = fh.read()
            if current == text:
                stats["unchanged"].append(rel)
                continue
            if not args.overwrite:
                stats["conflict"].append(rel)
                if not args.dry_run:
                    alt = os.path.join(args.out, "conflicts", rel)
                    os.makedirs(os.path.dirname(alt), exist_ok=True)
                    with open(alt, "w", encoding="utf-8") as fh:
                        fh.write(text)
                continue
            stats["updated"].append(rel)
        else:
            stats["created"].append(rel)
        if not args.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
    generated = [f"{k}: {r}" for k in ("created", "updated", "conflict") for r in stats[k]]
    with open(os.path.join(args.out, "mapping-report.md"), "w", encoding="utf-8") as fh:
        fh.write(report(plan, model.get("files", []), cfg, generated))
    write_json(os.path.join(args.out, "plan.json"), plan)
    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {len(stats['created']) + len(stats['updated'])} files under {into} "
          f"({len(stats['created'])} new, {len(stats['updated'])} replaced, {len(stats['unchanged'])} unchanged)")
    by_pkg = {}
    for _layer, package, name, _ in sources:
        by_pkg.setdefault(package, []).append(name)
    for pkg, names in by_pkg.items():
        print(f"  {pkg}: {', '.join(names)}")
    if stats["conflict"]:
        print(f"CONFLICTS ({len(stats['conflict'])}): existing files differ and were kept; the generated versions "
              f"are in {os.path.join(args.out, 'conflicts')} (compare, or rerun with --overwrite):")
        for r in stats["conflict"]:
            print(f"  - {r}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    a.add_argument("sql", nargs="+", help="SQL files or folders (Flyway order)")
    a.add_argument("--out", required=True, help="working folder for model, plan, config and report")
    a.add_argument("--dialect", choices=["oracle", "postgresql"])
    g = sub.add_parser("generate")
    g.add_argument("--out", required=True, help="working folder used by analyze")
    g.add_argument("--into", required=True, help="Java source root, e.g. src/main/java")
    g.add_argument("--overwrite", action="store_true", help="replace existing files that differ")
    g.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        return cmd_analyze(args) if args.cmd == "analyze" else cmd_generate(args)
    except mapping.ConfigError as e:
        print(f"error: config.json: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
