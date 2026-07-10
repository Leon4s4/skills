#!/usr/bin/env python3
"""
Pre-flight structural check for a Gen3 Dynatrace dashboard document, to run
BEFORE spending a `dtctl apply` round-trip. `dtctl apply` still performs the
authoritative server-side validation; this catches the obvious structural
breakage locally and fast.

Checks:
  - accepts the full document {name, type, content:{...}} or a bare content object
  - `content.version` is an int; `content.variables` is a list
  - `content.tiles` and `content.layouts` are both keyed MAPS (not arrays)
  - every tile ID in `tiles` has a matching entry in `layouts` and vice versa
  - each layout has integer x,y,w,h; x>=0, y>=0, w>=1, h>=1
  - x + w <= grid columns (default 24, or content.settings.gridLayout.columnsCount) [warn: wraps]
  - no two tiles overlap [error]
  - each `data` tile has a non-empty DQL `query` and a `visualization`
  - top-level `name` present (required before deploy) [warn]
  - variables that are never referenced as `$key` in any tile query/input [warn]

Usage:
    python scripts/validate_dashboard.py path/to/dashboard.json
Exit 0 = OK (warnings allowed). Exit 1 = hard errors; do not deploy.
"""
import json
import sys

DEFAULT_COLUMNS = 24
KNOWN_VISUALIZATIONS = {
    "lineChart", "areaChart", "barChart", "bandChart",
    "categoricalBarChart", "pieChart", "donutChart",
    "singleValue", "meterBar", "gauge",
    "table", "raw", "recordList",
    "histogram", "honeycomb",
    "choroplethMap", "dotMap", "connectionMap", "bubbleMap",
    "heatmap", "scatterplot",
}
TILE_TYPES = {"markdown", "data", "code", "slo"}


def _rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def validate(doc):
    errors, warnings = [], []

    if not isinstance(doc, dict):
        return ["Top level must be a JSON object."], []

    # Accept {name,type,content:{...}} or a bare content object.
    if isinstance(doc.get("content"), dict):
        content = doc["content"]
        if not doc.get("name"):
            warnings.append("Top-level `name` is missing — required before deploy "
                            "(new dashboards need a name; the server assigns the id).")
        if "id" in doc and not doc.get("id"):
            warnings.append("Empty `id` present — remove it on new dashboards; on updates it "
                            "must come from the downloaded file.")
    else:
        content = doc
        warnings.append("No `content` wrapper found — treating the top level as `content`. "
                        "Deployable documents are {name, type, content:{...}}.")

    # version / variables
    if "version" not in content:
        errors.append("Missing `content.version` (int).")
    elif not isinstance(content["version"], int):
        errors.append(f"`content.version` must be an integer, got {type(content['version']).__name__}.")

    variables = content.get("variables", [])
    if "variables" not in content:
        warnings.append("Missing `content.variables` (use [] if none).")
    elif not isinstance(variables, list):
        errors.append("`content.variables` must be an array.")
        variables = []

    # tiles / layouts must both be maps
    tiles = content.get("tiles")
    layouts = content.get("layouts")
    for label, obj in (("tiles", tiles), ("layouts", layouts)):
        if obj is None:
            errors.append(f"Missing `content.{label}`.")
        elif isinstance(obj, list):
            errors.append(f"`content.{label}` must be a keyed object/map, not an array.")
        elif not isinstance(obj, dict):
            errors.append(f"`content.{label}` must be an object/map.")
    if not isinstance(tiles, dict) or not isinstance(layouts, dict):
        return errors, warnings

    # tiles <-> layouts ID matching
    tile_ids, layout_ids = set(tiles), set(layouts)
    for missing in sorted(tile_ids - layout_ids):
        errors.append(f"tile '{missing}' has no matching entry in `layouts`.")
    for orphan in sorted(layout_ids - tile_ids):
        errors.append(f"layout '{orphan}' has no matching tile in `tiles`.")

    # grid columns
    columns = DEFAULT_COLUMNS
    try:
        columns = int(content["settings"]["gridLayout"]["columnsCount"])
    except (KeyError, TypeError, ValueError):
        pass

    # per-tile content checks
    for tid, tile in tiles.items():
        where = f"tile '{tid}'"
        if not isinstance(tile, dict):
            errors.append(f"{where}: must be an object.")
            continue
        ttype = tile.get("type")
        if not ttype:
            errors.append(f"{where}: missing `type`.")
        elif ttype not in TILE_TYPES:
            warnings.append(f"{where}: unrecognized type '{ttype}' "
                            f"(expected one of {sorted(TILE_TYPES)}).")
        if ttype == "data":
            q = tile.get("query")
            if not isinstance(q, str) or not q.strip():
                errors.append(f"{where}: `data` tile has no non-empty DQL `query`.")
            viz = tile.get("visualization")
            if not viz:
                errors.append(f"{where}: `data` tile has no `visualization`.")
            elif viz not in KNOWN_VISUALIZATIONS:
                warnings.append(f"{where}: visualization '{viz}' is unrecognized "
                                f"(may still be valid; verify against the tenant).")
            if "querySettings" not in tile:
                warnings.append(f"{where}: `data` tile missing `querySettings` (use {{}} if none).")
        if ttype == "markdown" and not tile.get("content"):
            warnings.append(f"{where}: markdown tile has empty `content`.")

    # per-layout geometry
    rects = {}
    for lid, layout in layouts.items():
        where = f"layout '{lid}'"
        if not isinstance(layout, dict):
            errors.append(f"{where}: must be an object with x,y,w,h.")
            continue
        miss = [k for k in ("x", "y", "w", "h") if k not in layout]
        if miss:
            errors.append(f"{where}: missing {miss}.")
            continue
        if not all(isinstance(layout[k], int) for k in ("x", "y", "w", "h")):
            errors.append(f"{where}: x/y/w/h must all be integers.")
            continue
        x, y, w, h = layout["x"], layout["y"], layout["w"], layout["h"]
        if x < 0 or y < 0:
            errors.append(f"{where}: x and y must be >= 0 (got x={x}, y={y}).")
        if w < 1 or h < 1:
            errors.append(f"{where}: w and h must be >= 1 (got w={w}, h={h}).")
        if x + w > columns:
            warnings.append(f"{where}: x + w = {x + w} exceeds grid width {columns} "
                            f"(tile will wrap; use standard widths).")
        rects[lid] = (x, y, w, h)

    # overlaps
    ids = list(rects)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if _rects_overlap(rects[ids[i]], rects[ids[j]]):
                errors.append(f"layouts '{ids[i]}' and '{ids[j]}' overlap "
                              f"({rects[ids[i]]} vs {rects[ids[j]]}).")

    # unused variables (anti-pattern: every variable must be referenced)
    if isinstance(variables, list):
        all_query_text = " ".join(
            (t.get("query") or "") + " " + (t.get("input") or "")
            for t in tiles.values() if isinstance(t, dict)
        )
        for v in variables:
            if isinstance(v, dict) and v.get("key"):
                ref = "$" + v["key"]
                if ref not in all_query_text:
                    warnings.append(f"variable '{v['key']}' is never referenced as "
                                    f"{ref} in any tile query — remove it or use it.")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_dashboard.py path/to/dashboard.json")
        sys.exit(2)
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}")
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON: {e}")
        sys.exit(1)

    errors, warnings = validate(doc)
    content = doc.get("content", doc) if isinstance(doc, dict) else {}
    n_tiles = len(content.get("tiles", {})) if isinstance(content.get("tiles"), dict) else 0
    print(f"Validating: {path}")
    print(f"  name: {doc.get('name', '(none)')}   version: {content.get('version', '(missing)')}   tiles: {n_tiles}")
    for w in warnings:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  FAIL  {e}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(warnings)} warning(s) — do NOT deploy yet.")
        sys.exit(1)
    print(f"\nOK — 0 errors, {len(warnings)} warning(s). Still run "
          f"`dtctl apply --dry-run` for authoritative server validation.")
    sys.exit(0)


if __name__ == "__main__":
    main()
