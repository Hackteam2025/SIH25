## BUG 1 : Data not getting preprocessed
### Issue Analysis

1. QC flag handling
    - Original code accepted only numeric QC flags (1, 2); dataset included character flags like 'B'.
2. Data mode extraction
    - Character-array decoding failed for some encoded characters, causing DATA_MODE and PLATFORM_NUMBER to be read incorrectly.
3. Variable selection
    - Fallback logic for unknown/edge-case data modes was not robust.

### Fixes Applied

- step5_data_preprocessor.py:88–95 — Better variable selection
  - Introduced robust fallback logic for unknown data modes to avoid missing variables.

- step5_data_preprocessor.py:105–127 — Enhanced QC flag handling
  - Added _safe_qc_check() that accepts numeric and character QC flags and treats 'B' as acceptable.
  - Centralized QC checks to reduce duplicated logic.

- step5_data_preprocessor.py:165–174 — Improved character decoding
  - Added error handling and fallbacks when decoding DATA_MODE and PLATFORM_NUMBER from character arrays.
  - Ensures sensible defaults when decoding fails.

- Logging and observability
  - Added debug-level logs to trace decoding, QC decisions, and fallback triggers to aid troubleshooting.

Notes:
- Changes aim to be defensive: prefer safe defaults and explicit logs over silent failures.
- Refer to the file and line ranges above when reviewing the patch.

[SOLVED BY] : PRABHUDAYAL VAISHNAV @ 15.09.2025