# csv2json — CSV → clean JSON (validation, missing-value handling, logging)

Standard library + pandas only. Single file: `csv2json.py`.

## Install
```
pip install pandas
```

## Usage
```
python csv2json.py input.csv -o output.json \
  --schema '{"id":"int","price":"float","name":"str","joined":"date","active":"bool"}' \
  --missing fill --fill-default null
```

| flag | meaning |
|---|---|
| `-o/--output` | output path (default `<input>.json`) |
| `--schema` | JSON `{col: int\|float\|str\|date\|bool}` — validates + coerces, logs row-level errors |
| `--missing` | `drop` \| `fill` \| `flag` (default `flag` → null in JSON) |
| `--fill-default` | value for `--missing fill` (`null` → JSON null) |
| `--orient` | `records` (default) \| `columns` |
| `--logfile` | log path (default `csv2json.log`) |

## Behaviour
- Type validation per `--schema`; invalid cells are logged with row+column and become `null`.
- Missing values handled per `--missing`.
- Dates → ISO 8601 strings. Robust `try/except` with exit codes: 0 ok · 2 args · 3 no input · 4 failure.
- Logs to stdout + logfile.

## Example
`sample.csv` (has a missing price, an invalid number `abc`, an invalid date) →
```
python csv2json.py sample.csv -o expected.json --schema '{"id":"int","price":"float","joined":"date","active":"bool"}' --missing flag
```
produces valid JSON with bad cells as `null` and every error logged.
