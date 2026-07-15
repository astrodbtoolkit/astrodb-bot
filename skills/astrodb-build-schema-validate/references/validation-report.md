# Validation Report Structure

Output a markdown validation report using this exact structure:

```
## Schema Mapping Validation Report
Source: <filename> → <schema.yaml path>
Date: <today>

### Nullable Violations  (<N> issues)
| Data Column | Maps To | Null Count | Total Rows | % Null |
|---|---|---|---|---|
| col_name | Table.field | 42 | 1000 | 4.2% |

### Type Mismatches  (<N> issues)
| Data Column | Data Type | Maps To | Expected Type | Compatible? |
|---|---|---|---|---|
| col_name | float32 | Table.field | string | ❌ No |

### Clean Mappings  (<N> columns OK)
(List column → field pairs that passed both checks, one per line, as a collapsed summary)

### Summary
- X nullable violations found (columns with nulls in non-nullable fields)
- Y type mismatches found
- Z columns passed validation cleanly

**Next steps:**
- For nullable violations: either filter out null rows before ingest, fill with a default
  value, or ask the schema maintainer whether the field can be made nullable.
- For type mismatches: add a type-cast step in your ingestion script.
```

If there are no issues, say so clearly: "All N mapped columns passed validation."

Also write the full report to `astrodb-build-artifacts/schema-validation-report.md` using the
Write tool and tell the user the path. (This is the same `astrodb-build-artifacts/` directory the
validation script in Step 2 was written to, and where the other build skills write their outputs.)
