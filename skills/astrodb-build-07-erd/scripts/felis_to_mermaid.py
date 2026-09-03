#!/usr/bin/env python
"""Emit a Mermaid erDiagram from a Felis schema.yaml. Requires only pyyaml.

Usage:
    python felis_to_mermaid.py --schema schema.yaml
    python felis_to_mermaid.py --schema schema.yaml --format md --out docs/figures/schema_erd.md
    python felis_to_mermaid.py --schema schema.yaml --split docs/schema/erd
    python felis_to_mermaid.py --schema schema.yaml --inject docs/figures/schema_erd.md --check

No system binaries, no graphviz, no node. The output is text that GitHub renders
natively in READMEs, markdown files, issues, and pull requests.
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: pyyaml is required. Install it with: uv add pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

# GitHub's mermaid maxTextSize is 50000 characters and is NOT configurable there.
# Past it, the diagram silently renders as "Maximum text size in diagram exceeded".
# Default to 10% headroom under that.
GITHUB_MAX_TEXT_SIZE = 50000
DEFAULT_MAX_CHARS = 45000

# Mermaid attribute types must be single tokens.
TYPE_MAP = {
    "string": "string",
    "char": "string",
    "unicode": "string",
    "text": "text",
    "double": "double",
    "float": "float",
    "int": "int",
    "long": "long",
    "short": "short",
    "byte": "byte",
    "boolean": "boolean",
    "timestamp": "timestamp",
    "binary": "blob",
}

# Cluster taxonomy for the astrodb-template-db schema. Names match the
# Lookup / Main / Data grouping in astrodb-build-03-schema-match/references/schema.md.
# Any table not listed here is placed by the structural heuristic in assign_clusters().
KNOWN_CLUSTERS = {
    "lookup": [
        "Publications", "Telescopes", "Instruments", "PhotometryFilters", "Versions",
        "RegimeList", "AssociationList", "ParameterList", "CompanionList", "SourceTypeList",
    ],
    "main": ["Sources", "Names", "Positions"],
    "data": [
        "Photometry", "Parallaxes", "RadialVelocities", "ProperMotions", "ModeledParameters",
        "RotationalParameters", "Morphology", "Spectra", "CompanionParameters",
        "CompanionRelationships", "Associations", "SourceTypes",
    ],
}

CLUSTER_TITLES = {
    "lookup": "Lookup tables",
    "main": "Main tables",
    "data": "Data tables",
}


def parse_ref(ref):
    """'#Sources.ra_deg' -> ('Sources', 'ra_deg');  '#Sources' -> ('Sources', None)."""
    body = str(ref).lstrip("#")
    table, _, column = body.partition(".")
    return table, (column or None)


def mermaid_type(datatype):
    """Map a Felis datatype to a single-token mermaid attribute type."""
    if not datatype:
        return "unknown"
    key = str(datatype).lower()
    if key in TYPE_MAP:
        return TYPE_MAP[key]
    return re.sub(r"\W+", "_", key) or "unknown"


def clean_comment(text, limit=60):
    """Make a Felis description safe for a mermaid attribute comment.

    Double quotes terminate the comment and newlines break the parser, so both go.
    """
    if not text:
        return ""
    collapsed = " ".join(str(text).split())
    collapsed = collapsed.replace('"', "")
    if len(collapsed) > limit:
        collapsed = collapsed[: limit - 1].rstrip() + "…"
    return collapsed


def entity_name(name):
    """Quote a table name if it is not a bare mermaid identifier."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        return name
    return '"%s"' % str(name).replace('"', "")


def load_schema(path):
    """Read and parse a Felis schema.yaml file into a dict."""
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "tables" not in data:
        raise ValueError("%s does not look like a Felis schema (no top-level 'tables')" % path)
    return data


class Table:
    """One Felis table, with its key roles resolved."""

    def __init__(self, raw):
        """Parse one Felis table dict into name, columns, and resolved PK/FK/UK roles."""
        self.raw = raw
        self.name = raw.get("name") or parse_ref(raw.get("@id", "#?"))[0]
        self.description = raw.get("description", "")
        self.columns = raw.get("columns") or []

        self.pk = []
        for ref in raw.get("primaryKey") or []:
            _, col = parse_ref(ref)
            if col:
                self.pk.append(col)

        self.fk_columns = set()
        self.foreign_keys = []
        self.unique = set()

        for constraint in raw.get("constraints") or []:
            ctype = constraint.get("@type")
            cols = [parse_ref(c)[1] for c in constraint.get("columns") or []]
            cols = [c for c in cols if c]
            if ctype == "ForeignKey":
                referenced = [parse_ref(c) for c in constraint.get("referencedColumns") or []]
                referenced = [r for r in referenced if r[0]]
                if not cols or not referenced:
                    continue
                self.fk_columns.update(cols)
                self.foreign_keys.append(
                    {
                        "columns": cols,
                        "parent": referenced[0][0],
                        "parent_columns": [r[1] for r in referenced],
                    }
                )
            elif ctype == "Unique":
                self.unique.update(cols)
            # "Check" constraints carry no relationship information; skip them.

        for index in raw.get("indexes") or []:
            if index.get("unique"):
                for ref in index.get("columns") or []:
                    _, col = parse_ref(ref)
                    if col:
                        self.unique.add(col)

    def column_role(self, column_name):
        """Return the mermaid key markers for a column, in PK, FK, UK order."""
        markers = []
        if column_name in self.pk:
            markers.append("PK")
        if column_name in self.fk_columns:
            markers.append("FK")
        if column_name in self.unique:
            markers.append("UK")
        return markers

    def is_nullable(self, column_name):
        """Felis omits `nullable` when it defaults to true."""
        for col in self.columns:
            if col.get("name") == column_name:
                return col.get("nullable", True) is not False
        return True

    def ordered_columns(self, detail):
        """Columns to show, PK first (in primaryKey order), then FKs, then schema order."""
        by_name = {c.get("name"): c for c in self.columns if c.get("name")}

        if detail == "full":
            selected = [c.get("name") for c in self.columns if c.get("name")]
        elif detail == "required":
            selected = [
                name
                for name in by_name
                if self.column_role(name) or not self.is_nullable(name)
            ]
        else:  # keys
            selected = [name for name in by_name if self.column_role(name)]

        selected = set(selected)
        ordered = []
        for name in self.pk:
            if name in selected and name in by_name:
                ordered.append(name)
        for col in self.columns:
            name = col.get("name")
            if name in selected and name not in ordered and name in self.fk_columns:
                ordered.append(name)
        for col in self.columns:
            name = col.get("name")
            if name in selected and name not in ordered:
                ordered.append(name)
        return [(name, by_name[name]) for name in ordered if name in by_name]


def build_tables(schema):
    """Turn a parsed schema dict into a name -> Table map."""
    tables = [Table(raw) for raw in schema.get("tables") or []]
    return {t.name: t for t in tables}


def relationships(tables):
    """One mermaid relationship line's worth of data per foreign key constraint.

    A composite foreign key collapses to a single edge labelled with all its columns.
    """
    rels = []
    for name, table in tables.items():
        for fk in table.foreign_keys:
            parent = fk["parent"]
            if parent not in tables:
                continue
            cols = fk["columns"]

            # Parent multiplicity: a nullable child column means the parent may be absent.
            all_required = all(not table.is_nullable(c) for c in cols)
            left = "||" if all_required else "|o"

            # Child multiplicity.
            if set(cols) == set(table.pk) and table.pk:
                right = "||"
            elif len(cols) == 1 and cols[0] in table.unique:
                right = "|o"
            else:
                right = "o{"

            # Identifying relationships (the FK is part of the child's key) get a solid line.
            line = "--" if set(cols) & set(table.pk) else ".."

            rels.append(
                {
                    "parent": parent,
                    "child": name,
                    "columns": cols,
                    "marker": left + line + right,
                }
            )
    rels.sort(key=lambda r: (r["parent"], r["child"], ",".join(r["columns"])))
    return rels


def assign_clusters(tables, rels):
    """Group tables into lookup / main / data.

    Known astrodb-template-db table names use the documented taxonomy; anything else
    is placed structurally. Callers should confirm the result with the user.
    """
    known = {}
    for cluster, names in KNOWN_CLUSTERS.items():
        for name in names:
            known[name] = cluster

    outdeg = {name: set() for name in tables}
    indeg = {name: set() for name in tables}
    for rel in rels:
        outdeg[rel["child"]].add(rel["parent"])
        indeg[rel["parent"]].add(rel["child"])

    assigned = {}
    unknown = []
    for name in tables:
        if name in known:
            assigned[name] = known[name]
        else:
            unknown.append(name)

    if unknown:
        # Lookup: referenced by several tables, references nothing itself.
        for name in list(unknown):
            if not outdeg[name] and len(indeg[name]) >= 2:
                assigned[name] = "lookup"
                unknown.remove(name)

        # The hub is whatever the most tables point at; it and its neighbours are "main".
        hub = None
        if unknown:
            hub = max(unknown, key=lambda n: len(indeg[n]))
            if not indeg[hub]:
                hub = None
        if hub:
            assigned[hub] = "main"
            unknown.remove(hub)
            for name in list(unknown):
                if hub in outdeg[name]:
                    assigned[name] = "data"
                    unknown.remove(name)

        for name in unknown:
            assigned[name] = "main"

    clusters = {"lookup": [], "main": [], "data": []}
    for name in tables:
        clusters[assigned.get(name, "main")].append(name)
    return clusters, assigned


def render(tables, rels, include, detail="keys", comments=False, context=()):
    """Render an erDiagram over `include`, with `context` tables shown keys-only."""
    include = [n for n in tables if n in set(include)]
    context = [n for n in tables if n in set(context) and n not in set(include)]
    visible = set(include) | set(context)

    lines = ["erDiagram"]

    # Relationship lines first, mermaid draws these above the entity boxes.
    for rel in rels:
        if rel["parent"] in visible and rel["child"] in visible:
            lines.append(
                "    %s %s %s : \"%s\""
                % (
                    entity_name(rel["parent"]),
                    rel["marker"],
                    entity_name(rel["child"]),
                    ", ".join(rel["columns"]),
                )
            )

    # Then one entity box per table; context tables are always keys-only.
    for name in include + context:
        table = tables[name]
        table_detail = detail if name in set(include) else "keys"
        cols = table.ordered_columns(table_detail)
        if not cols:
            lines.append("    %s {" % entity_name(name))
            lines.append("    }")
            continue
        lines.append("    %s {" % entity_name(name))
        for col_name, col in cols:
            parts = [mermaid_type(col.get("datatype")), col_name]
            markers = table.column_role(col_name)
            if markers:
                # Mermaid requires multiple key markers comma-separated: "PK, FK".
                parts.append(", ".join(markers))
            if comments:
                comment = clean_comment(col.get("description"))
                if comment:
                    parts.append('"%s"' % comment)
            lines.append("        " + " ".join(parts))
        lines.append("    }")

    return "\n".join(lines) + "\n"


def wrap_markdown(diagram, title, marker_prefix):
    """Wrap a raw mermaid diagram in a fenced code block with BEGIN/END markers."""
    begin = "<!-- %s:BEGIN - generated by astrodb-build-07-erd; edit schema.yaml, not this block -->" % marker_prefix
    end = "<!-- %s:END -->" % marker_prefix
    parts = []
    if title:
        parts.append("# %s\n" % title)
    parts.append(begin)
    parts.append("```mermaid")
    parts.append(diagram.rstrip("\n"))
    parts.append("```")
    parts.append(end)
    return "\n".join(parts) + "\n"


def inject(path, diagram, marker_prefix, title, check=False):
    """Replace the block between the ERD markers in `path`. Returns True if changed."""
    begin_re = re.compile(r"<!--\s*%s:BEGIN.*?-->" % re.escape(marker_prefix))
    end_re = re.compile(r"<!--\s*%s:END\s*-->" % re.escape(marker_prefix))
    target = Path(path)
    new_block = wrap_markdown(diagram, None, marker_prefix).rstrip("\n")

    # No file yet: check mode has nothing to compare against, otherwise seed a new file.
    if not target.exists():
        if check:
            print(
                "ERROR: %s does not exist; nothing to check against." % target,
                file=sys.stderr,
            )
            sys.exit(1)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(wrap_markdown(diagram, title, marker_prefix))
        return True

    original = target.read_text()
    begin_match = begin_re.search(original)
    end_match = end_re.search(original)
    if not begin_match or not end_match or end_match.start() < begin_match.end():
        print(
            "ERROR: could not find a matching <!-- %s:BEGIN --> / <!-- %s:END --> pair in %s.\n"
            "Add the markers around the block you want replaced, or write to a new file instead."
            % (marker_prefix, marker_prefix, target),
            file=sys.stderr,
        )
        sys.exit(1)

    updated = original[: begin_match.start()] + new_block + original[end_match.end() :]
    if updated == original:
        return False
    if not check:
        target.write_text(updated)
    return True


def report_stats(tables, rels, focus, context, diagram, max_chars, label=""):
    """Print table/column/relationship/size counts for a rendered diagram to stderr."""
    focus = [n for n in focus if n in tables]
    context = [n for n in context if n in tables and n not in set(focus)]
    visible = set(focus) | set(context)
    columns = sum(len(tables[n].columns) for n in focus)
    edges = [r for r in rels if r["parent"] in visible and r["child"] in visible]
    prefix = "%s: " % label if label else ""
    extra = " (+%d context)" % len(context) if context else ""
    print(
        "%s%d tables%s, %d columns, %d relationships, %d characters (budget %d, GitHub limit %d)"
        % (
            prefix, len(focus), extra, columns, len(edges),
            len(diagram), max_chars, GITHUB_MAX_TEXT_SIZE,
        ),
        file=sys.stderr,
    )


def check_budget(diagram, max_chars, detail, comments, splitting=False):
    """Exit 1 with remedy suggestions if the diagram exceeds the character budget."""
    if len(diagram) <= max_chars:
        return
    remedies = []
    if comments:
        remedies.append("drop --comments")
    if detail == "full":
        remedies.append("use --detail required or --detail keys")
    elif detail == "required":
        remedies.append("use --detail keys")
    if splitting:
        # Already split: suggesting --split again would be useless advice.
        remedies.append("draw this cluster in pieces with --tables")
    else:
        remedies.append("split the diagram with --split PREFIX")
    print(
        "ERROR: the diagram is %d characters, over the %d budget.\n"
        "GitHub's mermaid limit is %d and it is NOT configurable there - past it the diagram\n"
        "silently renders as \"Maximum text size in diagram exceeded\" instead of failing loudly.\n"
        "Remedies: %s."
        % (len(diagram), max_chars, GITHUB_MAX_TEXT_SIZE, "; ".join(remedies)),
        file=sys.stderr,
    )
    sys.exit(1)


def write_output(text, out):
    """Write text to stdout if out is "-", otherwise to a file (creating parent dirs)."""
    if out == "-":
        sys.stdout.write(text)
        return
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def build_arg_parser():
    """Define the CLI, split out so main() only has to run it."""
    parser = argparse.ArgumentParser(
        description="Emit a Mermaid erDiagram from a Felis schema.yaml (pyyaml only)."
    )
    parser.add_argument("--schema", required=True, help="Path to the Felis schema.yaml")
    parser.add_argument("--out", default="-", help="Output file; '-' writes to stdout (default)")
    parser.add_argument(
        "--format",
        choices=["mmd", "md"],
        default="mmd",
        help="Raw mermaid (mmd) or markdown with a fenced mermaid block (md)",
    )
    parser.add_argument(
        "--detail",
        choices=["keys", "required", "full"],
        default="keys",
        help="keys = PK/FK/UK only (default); required = keys plus non-nullable; full = every column",
    )
    parser.add_argument(
        "--comments",
        action="store_true",
        help="Include Felis descriptions as attribute comments (off by default - biggest size driver)",
    )
    parser.add_argument("--tables", help="Comma-separated tables to include")
    parser.add_argument(
        "--no-neighbors",
        action="store_true",
        help="With --tables, do not pull in directly related tables as context",
    )
    parser.add_argument("--exclude", help="Comma-separated tables to drop")
    parser.add_argument(
        "--cluster",
        choices=["lookup", "main", "data"],
        help="Emit one cluster (see references/clusters.md)",
    )
    parser.add_argument(
        "--split",
        help="Write overview plus one file per cluster as PREFIX-overview.md, PREFIX-lookup.md, ... "
        "(flat files; parent dirs are created as needed)",
    )
    parser.add_argument("--title", help="Heading used when --format md")
    parser.add_argument("--inject", help="Replace the block between the ERD markers in this file")
    parser.add_argument(
        "--marker-prefix",
        default="ERD",
        help='Marker prefix; default "ERD" -> <!-- ERD:BEGIN --> / <!-- ERD:END -->',
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="With --inject: exit 1 if the file is stale, and write nothing",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Character budget per diagram (default %d; GitHub's limit is %d)"
        % (DEFAULT_MAX_CHARS, GITHUB_MAX_TEXT_SIZE),
    )
    parser.add_argument("--stats", action="store_true", help="Print counts and sizes to stderr")
    parser.add_argument(
        "--print-clusters",
        action="store_true",
        help="Print the proposed cluster assignment and exit (confirm it with the user)",
    )
    return parser


def load_tables_or_exit(schema_path):
    """Parse the schema and compute tables/relationships/clusters, or exit(1) with a message."""
    if not schema_path.exists():
        print("ERROR: Schema file not found: %s" % schema_path, file=sys.stderr)
        sys.exit(1)
    try:
        schema = load_schema(schema_path)
    except Exception as exc:
        print("ERROR: could not read %s: %s" % (schema_path, exc), file=sys.stderr)
        sys.exit(1)

    tables = build_tables(schema)
    if not tables:
        print("ERROR: %s defines no tables." % schema_path, file=sys.stderr)
        sys.exit(1)
    rels = relationships(tables)
    clusters, assigned = assign_clusters(tables, rels)
    return tables, rels, clusters, assigned


def boundary_context(names, rels, exclude):
    """Tables directly connected to `names` but not in it - drawn as keys-only context boxes."""
    context = set()
    for rel in rels:
        if rel["child"] in names and rel["parent"] not in names:
            context.add(rel["parent"])
        if rel["parent"] in names and rel["child"] not in names:
            context.add(rel["child"])
    return context - exclude


def split_output_path(prefix, part, format):
    """Build a flat output path: PREFIX-overview.md, PREFIX-lookup.md, etc."""
    base = Path(prefix.rstrip("/\\"))
    ext = "md" if format == "md" else "mmd"
    return str(base.parent / ("%s-%s.%s" % (base.name, part, ext)))


def run_split(args, tables, rels, clusters):
    """Handle --split: write an overview plus one diagram per cluster as flat PREFIX-*.md files."""
    all_names = list(tables)
    exclude = {n.strip() for n in (args.exclude or "").split(",") if n.strip()}
    prefix = args.split.rstrip("/\\")
    written = []

    overview_names = [n for n in all_names if n not in exclude]
    overview = render(tables, rels, overview_names, detail="keys", comments=False)
    check_budget(overview, args.max_chars, "keys", False)
    overview_path = split_output_path(prefix, "overview", args.format)
    write_output(
        wrap_markdown(overview, "Schema overview", args.marker_prefix)
        if args.format == "md"
        else overview,
        overview_path,
    )
    written.append(overview_path)
    if args.stats:
        report_stats(tables, rels, overview_names, [], overview, args.max_chars, "overview")

    for cluster in ("lookup", "main", "data"):
        names = [n for n in clusters[cluster] if n not in exclude]
        if not names:
            continue
        context = boundary_context(names, rels, exclude)
        diagram = render(
            tables, rels, names, detail=args.detail, comments=args.comments, context=context
        )
        check_budget(diagram, args.max_chars, args.detail, args.comments, splitting=True)
        cluster_path = split_output_path(prefix, cluster, args.format)
        write_output(
            wrap_markdown(diagram, CLUSTER_TITLES[cluster], args.marker_prefix)
            if args.format == "md"
            else diagram,
            cluster_path,
        )
        written.append(cluster_path)
        if args.stats:
            report_stats(tables, rels, names, sorted(context), diagram, args.max_chars, cluster)

    print(
        "Wrote overview plus %d cluster diagram(s): %s"
        % (len(written) - 1, ", ".join(written))
    )


def resolve_selection(args, tables, rels, clusters):
    """Work out which tables to draw (--cluster / --tables / everything) plus their context."""
    exclude = {n.strip() for n in (args.exclude or "").split(",") if n.strip()}

    if args.cluster:
        include = [n for n in clusters[args.cluster] if n not in exclude]
        context = boundary_context(include, rels, exclude)
    elif args.tables:
        include = [n.strip() for n in args.tables.split(",") if n.strip()]
        missing = [n for n in include if n not in tables]
        if missing:
            print("ERROR: table(s) not in the schema: %s" % ", ".join(missing), file=sys.stderr)
            sys.exit(1)
        context = boundary_context(include, rels, exclude) if not args.no_neighbors else set()
        include = [n for n in include if n not in exclude]
    else:
        include = [n for n in tables if n not in exclude]
        context = set()

    if not include:
        print("ERROR: no tables left to draw after filtering.", file=sys.stderr)
        sys.exit(1)
    return include, context


def emit_or_inject(args, schema_path, tables, rels, include, context):
    """Render the diagram and either inject it into a file, write it out, or both check-only."""
    diagram = render(
        tables, rels, include, detail=args.detail, comments=args.comments, context=context
    )
    check_budget(diagram, args.max_chars, args.detail, args.comments)

    if args.stats:
        report_stats(tables, rels, include, sorted(context), diagram, args.max_chars)

    if args.inject:
        changed = inject(args.inject, diagram, args.marker_prefix, args.title, check=args.check)
        if args.check:
            if changed:
                print(
                    "ERROR: %s is out of date with %s. Regenerate it by re-running without --check."
                    % (args.inject, schema_path),
                    file=sys.stderr,
                )
                sys.exit(1)
            print("%s is up to date." % args.inject)
        else:
            print("%s %s" % ("Updated" if changed else "Already up to date:", args.inject))
        return

    text = wrap_markdown(diagram, args.title, args.marker_prefix) if args.format == "md" else diagram
    write_output(text, args.out)
    if args.out != "-":
        print("Wrote %s" % args.out)


def main():
    """CLI entry point: parse args, load the schema, then dispatch to the right mode."""
    args = build_arg_parser().parse_args()
    schema_path = Path(args.schema)
    tables, rels, clusters, _assigned = load_tables_or_exit(schema_path)

    if args.print_clusters:
        for cluster in ("lookup", "main", "data"):
            names = clusters[cluster]
            if names:
                print("%s: %s" % (CLUSTER_TITLES[cluster], ", ".join(names)))
        return

    if args.split:
        run_split(args, tables, rels, clusters)
        return

    include, context = resolve_selection(args, tables, rels, clusters)
    emit_or_inject(args, schema_path, tables, rels, include, context)


if __name__ == "__main__":
    main()
