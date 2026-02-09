# SPEC v1.3 (Implementation Addendum)

Date: 2026-02-08  
Scope: Contract refinements for MVP viability and operational safety.

This document complements `SPEC.md`.  
If there is conflict, this addendum takes precedence for implementation details introduced below.

## 1. Delivery strategy by waves

### MVP-1 (mandatory first release)

1. IBGE admin connector (`ibge_admin_fetch`)
2. IBGE geometries connector (`ibge_geometries_fetch`)
3. IBGE indicators connector (`ibge_indicators_fetch`)
4. Gold baseline (`dbt_build`)
5. Quality suite (`quality_suite`)
6. API v1 with stable pagination and error contract
7. Operational metadata persistence (`ops.pipeline_runs`, `ops.pipeline_checks`)

### MVP-2 (electoral layer)

1. `tse_catalog_discovery`
2. `tse_electorate_fetch`
3. `tse_results_fetch`

### MVP-3 (domain expansion)

1. `education_inep_fetch`
2. `health_datasus_fetch`
3. `finance_siconfi_fetch`
4. `labor_mte_fetch`

## 2. Naming convention policy

1. Technical structures are English-first:
   - schemas, tables, columns, code identifiers, internal API contracts.
2. Source/business content remains in original language:
   - labels, official names, raw fields, dataset descriptions.
3. Compatibility can be provided through read-only views when old Portuguese names exist.

## 3. API contract hardening

1. API must be versioned at `/v1`.
2. Error response must follow this shape:

```json
{
  "error": {
    "code": "validation_error|http_error|internal_error",
    "message": "human readable message",
    "details": {},
    "request_id": "uuid"
  }
}
```

3. Every response must include `x-request-id`.

## 4. Canonical territorial identity

`silver.dim_territory` must include:

1. `canonical_key` (stable unique key, mandatory)
2. `source_system` (IBGE/TSE/etc)
3. `source_entity_id` (source-native id)
4. `normalized_name` (normalized text for matching)

This identity model is mandatory for cross-source joins and deduplication.

## 5. Data quality thresholds

Checks are no longer only boolean.  
Each mandatory check must include threshold and observed value:

1. `threshold_value`
2. `observed_value`
3. `status` derived by threshold comparison (`pass|warn|fail`)

Threshold configuration source: `configs/quality_thresholds.yml`.

## 6. Bronze operating policy

Bronze governance is mandatory:

1. Immutable by extraction timestamp
2. Manifest + checksum for every artifact
3. Retention window configurable (`BRONZE_RETENTION_DAYS`)
4. Dry-run must not write to Bronze or database

Operational policy reference: `docs/BRONZE_POLICY.md`.

## 7. Connector lifecycle registry

Connector status must be explicit and queryable:

1. `implemented`
2. `partial`
3. `blocked`
4. `planned`

Source of truth for seed status: `configs/connectors.yml`.  
Database registry: `ops.connector_registry`.

## 8. Operational observability in database

In addition to logs/manifests, execution metadata must persist in:

1. `ops.pipeline_runs`
2. `ops.pipeline_checks`

Minimum persisted fields:

1. run id, job name, source, dataset, wave
2. start/end timestamps, duration, status
3. row counters and warning/error counters
4. bronze path, manifest path, checksum
5. check details with observed and threshold values
