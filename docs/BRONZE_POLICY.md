# Bronze Policy

## Purpose

`Bronze` stores source files exactly as received from official providers.  
No transformations are allowed in this layer.

## Rules

1. Immutable path by extraction timestamp:
   - `data/bronze/{source}/{dataset}/{reference_period}/extracted_at={iso_ts}/raw.ext`
2. Every raw artifact must have:
   - SHA256 checksum
   - Manifest in `data/manifests/...`
3. Same payload downloaded at different times remains versioned by `extracted_at`.
4. Pipeline retries must never overwrite existing bronze files.

## Retention

1. Bronze data is retained for at least `BRONZE_RETENTION_DAYS` days.
2. Cleanup can remove only data older than retention window.
3. Cleanup runs must keep manifests and checksums aligned with deleted files.

## Operational safeguards

1. Writes are restricted to the `data/` directory.
2. Any failed extraction must not produce partial manifest metadata.
3. `dry_run` mode must not write to Bronze or database.
