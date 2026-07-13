#!/usr/bin/env python3
"""
csv2json — CSV → clean JSON with column-type validation, missing-value handling,
error handling, and logging. Standard library + pandas only.

Usage:
    python csv2json.py input.csv -o output.json \
        --schema '{"id":"int","price":"float","name":"str","joined":"date"}' \
        --missing fill --fill-default null

Flags:
    -o/--output       output JSON path (default: <input>.json)
    --schema          JSON dict of column -> type (int|float|str|date|bool); optional
    --missing         drop | fill | flag   (how to handle missing values; default: flag)
    --fill-default    value used when --missing fill (default: empty string; "null" -> None)
    --orient          records | columns    (JSON shape; default: records)
    --logfile         log file path (default: csv2json.log)

Exit codes: 0 ok · 2 bad args · 3 input not found · 4 parse/validation failure
"""
import argparse, json, logging, sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.stderr.write("pandas is required: pip install pandas\n"); sys.exit(2)

_PY = {"int": "Int64", "float": "float64", "str": "string", "bool": "boolean", "date": "datetime64[ns]"}

def setup_logging(logfile):
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(logfile, encoding="utf-8")],
    )
    return logging.getLogger("csv2json")

def coerce(df, schema, log):
    """Coerce columns to schema types; log row-level errors; return df + error count."""
    errors = 0
    for col, typ in (schema or {}).items():
        if col not in df.columns:
            log.warning("schema column '%s' not in CSV; skipping", col); continue
        if typ == "date":
            parsed = pd.to_datetime(df[col], errors="coerce")
        elif typ in ("int", "float"):
            parsed = pd.to_numeric(df[col], errors="coerce")
            if typ == "int":
                parsed = parsed.astype("Int64")
        elif typ == "bool":
            parsed = df[col].map({"true": True, "false": False, "1": True, "0": False,
                                  True: True, False: False}).astype("boolean")
        else:
            parsed = df[col].astype("string")
        bad = parsed.isna() & df[col].notna()
        for idx in df.index[bad]:
            errors += 1
            log.error("row %s col '%s': value %r not valid %s", idx, col, df.at[idx, col], typ)
        df[col] = parsed
    return df, errors

def handle_missing(df, strategy, fill_default, log):
    miss = int(df.isna().sum().sum())
    if miss:
        log.info("missing values found: %d", miss)
    if strategy == "drop":
        before = len(df); df = df.dropna(); log.info("dropped %d rows with missing values", before - len(df))
    elif strategy == "fill":
        fv = None if fill_default == "null" else fill_default
        df = df.where(df.notna(), fv); log.info("filled missing values with %r", fv)
    # 'flag' = leave as NaN -> becomes null in JSON
    return df

def to_records(df):
    """JSON-safe records: NaT/NaN -> None, datetimes -> ISO."""
    out = []
    for _, row in df.iterrows():
        rec = {}
        for k, v in row.items():
            if pd.isna(v):
                rec[k] = None
            elif hasattr(v, "isoformat"):
                rec[k] = v.isoformat()
            else:
                rec[k] = v.item() if hasattr(v, "item") else v
        out.append(rec)
    return out

def main(argv=None):
    p = argparse.ArgumentParser(description="CSV -> clean JSON with validation")
    p.add_argument("input"); p.add_argument("-o", "--output")
    p.add_argument("--schema"); p.add_argument("--missing", choices=["drop", "fill", "flag"], default="flag")
    p.add_argument("--fill-default", default="")
    p.add_argument("--orient", choices=["records", "columns"], default="records")
    p.add_argument("--logfile", default="csv2json.log")
    try:
        args = p.parse_args(argv)
    except SystemExit:
        return 2
    log = setup_logging(args.logfile)

    src = Path(args.input)
    if not src.exists():
        log.error("input not found: %s", src); return 3
    schema = None
    if args.schema:
        try:
            schema = json.loads(args.schema)
        except json.JSONDecodeError as e:
            log.error("--schema is not valid JSON: %s", e); return 2

    try:
        df = pd.read_csv(src)
        log.info("read %d rows x %d cols from %s", len(df), len(df.columns), src)
        df, errs = coerce(df, schema, log)
        df = handle_missing(df, args.missing, args.fill_default, log)
        if args.orient == "records":
            payload = to_records(df)
        else:
            payload = {c: to_records(df[[c]]) for c in df.columns}
        out = Path(args.output) if args.output else src.with_suffix(".json")
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("wrote %s (%d validation errors logged)", out, errs)
        return 0
    except Exception as e:
        log.exception("conversion failed: %s", e); return 4

if __name__ == "__main__":
    sys.exit(main())
