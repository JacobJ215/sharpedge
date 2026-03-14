---
plan: 05-02
phase: 05-model-pipeline-upgrade
status: complete
completed: "2026-03-14"
commits:
  - c4b5379
  - e70874d
---

# Summary: 05-02 — FeatureAssembler

## What Was Built

Extended `GameFeatures` with 16 new MODEL-02 fields and implemented `FeatureAssembler` that assembles complete feature vectors at inference time with graceful degradation.

## Key Files

### Created
- `packages/models/src/sharpedge_models/feature_assembler.py` — FeatureAssembler class with travel penalty, timezone crossing calculation, and graceful degradation for missing external data
- `packages/models/src/sharpedge_models/_feature_helpers.py` — TEAM_TIMEZONES (32 NFL + 30 NBA teams), compute_timezone_crossings(), travel_penalty_from_crossings()
- `packages/models/src/sharpedge_models/_sport_medians.py` — Sport-specific median imputation values (extracted for 500-line compliance)

### Modified
- `packages/models/src/sharpedge_models/ml_inference.py` — GameFeatures extended with 16 MODEL-02 fields; to_array() uses sport-specific medians instead of 0.0 for None fields

## Test Results

All 16 tests in `test_feature_assembler.py` pass. All 37 model unit tests pass.

## Decisions

- Sport-specific medians over zero-fill: avoids NaN propagation and improves inference accuracy for sparse features
- TEAM_TIMEZONES + helpers extracted to `_feature_helpers.py`: 500-line compliance for feature_assembler.py
- _sport_medians.py submodule: separate file keeps ml_inference.py under limit
- Graceful degradation: all external client failures return None fields, assembled via median imputation
