# Replay Test Results Analysis

**Date**: 2026-06-14
**Test**: 100-case replay validation
**Baseline**: Pre-hybrid approach (rule-based secondary detection)
**Current**: Post-hybrid approach (LLM + rule-based secondary detection)

---

## Executive Summary

| Metric | Baseline | Current | Change |
|--------|----------|---------|--------|
| **Primary Classification** | 78% | 78% | **0%** (unchanged) |
| **Secondary Areas (exact)** | 63% | 42% | **-21%** ⚠️ REGRESSION |
| **Cross-Practice Flag** | 82% | 61% | **-21%** ⚠️ REGRESSION |
| **Recommendation Logic** | 9% | 75% | **+66%** ✓ MAJOR WIN |
| **Request Errors** | 0 | 0 | 0% |

**Overall Assessment**: Mixed results. Recommendation logic dramatically improved, but secondary area detection regressed significantly.

---

## Detailed Analysis by Component

### A. Recommendation Logic: 75% (IMPROVED from 9%)

**Status**: Major improvement achieved ✓

The prompt changes to strengthen recommendation logic worked:
- Added mandatory step-by-step decision process
- Forced evidence_missing check before routing to attorney
- **Result**: 66% improvement (9% → 75%)

**Remaining Issues** (25 failures):
- Some cases still incorrectly routing to attorney vs requesting evidence
- Examples:
  - REPLAY-010 (should route to attorney, requested evidence)
  - REPLAY-016 (should request evidence, routed to attorney)

**Recommended Next Steps**:
- Investigate the 25 failing recommendation cases to identify pattern
- May need additional edge-case handling in recommendation prompt

---

### B. Primary Classification: 78% (UNCHANGED)

**Status**: No improvement

The TCPA vs FDCPA overlap guidance did not resolve primary classification issues.

**Failure Pattern** (22 failures):

1. **TCPA → FDCPA swaps** (debt collector calling cell phone cases):
   - REPLAY-007, 013, 019: Expected TCPA, got FDCPA
   - The prompt guidance about "METHOD vs CONDUCT" isn't being followed
   - LLM prioritizing debt collection context over call methodology

2. **TCPA → FCRA swaps** (credit-related calls):
   - REPLAY-004, 010, 016: Expected TCPA, got FCRA
   - LLM prioritizing credit context over call method

**Root Cause Hypothesis**:
- Current prompt guidance is too abstract ("METHOD vs CONDUCT")
- LLM needs concrete examples (few-shot learning)
- May need explicit decision tree logic in prompt

**Recommended Next Steps**:
1. Add 3-5 few-shot examples to classification prompt showing:
   - "Debt collector calling cell phone" → TCPA (method-focused)
   - "Debt collector harassing/lying" → FDCPA (conduct-focused)
   - "Credit report dispute + calls" → FCRA primary, TCPA secondary
2. Consider adding explicit decision tree:
   ```
   IF (cell phone calls mentioned) AND (no conduct violations mentioned)
     THEN TCPA
   ELSE IF (debt collector conduct violations)
     THEN FDCPA
   ```

---

### C. Secondary Practice Areas: 42% (REGRESSED from 63%)

**Status**: Critical regression - hybrid approach underperformed ⚠️

**Expected**: 78-88% accuracy
**Actual**: 42% accuracy
**Delta**: -21% worse than baseline

**Failure Pattern Analysis** (58 failures):

1. **False Positive FDCPA Detections** (~30-40% of failures):
   - Cases expecting `[]` but getting `["FDCPA"]`
   - Examples: REPLAY-005, 006, 011, 012, 017, 018
   - **Root Cause**: Hybrid approach too aggressive - LLM inferring FDCPA from weak contextual signals
   - **Impact**: Incorrectly flagging single-practice cases as cross-practice

2. **Cascading from Primary Failures** (~30-40% of failures):
   - REPLAY-004: Primary=FCRA (wrong, should be TCPA), missing FCRA in secondary
   - REPLAY-007: Primary=FDCPA (wrong, should be TCPA), has TCPA in secondary instead
   - **Expected behavior** when primary classification fails
   - **Impact**: Will auto-resolve when primary classification improves

3. **Missing Secondary Areas** (~20-30% of failures):
   - REPLAY-004, 010: Expected `["FCRA", "FDCPA"]`, got only `["FDCPA"]`
   - REPLAY-016: Expected `["FCRA", "FDCPA"]`, got `["FDCPA", "TCPA"]` (extra TCPA instead of FCRA)
   - **Root Cause**: LLM not detecting all relevant secondary areas, or detecting wrong ones

**Key Insight**: The hybrid approach (LLM + rules) performed worse than baseline (rules only).

**Hypothesis - Why Hybrid Failed**:
1. LLM confidence threshold (0.7) is too permissive
2. LLM over-interpreting generic debt language as FDCPA signals
3. LLM not properly filtering weak contextual signals
4. Secondary area detection may be harder for LLM than expected (requires precise legal distinction)

---

### D. Cross-Practice Flag: 61% (REGRESSED from 82%)

**Status**: Significant regression ⚠️

**Analysis**: Cross-practice flag directly depends on secondary area detection:
- Logic: `cross_practice_flag = len(secondary_areas) > 0`
- Since secondary detection has false positives (detecting FDCPA when it shouldn't), cross-practice flag is incorrectly set to `true`
- Examples: REPLAY-005, 006, 011, 012, 017, 018 (all expected `false`, got `true`)

**Root Cause**: Cascading from secondary area detection failures (false positives)

**Impact**: 21% regression (82% → 61%)

**Expected Behavior**: Will auto-resolve when secondary detection is fixed

---

## Root Cause: Hybrid Approach Issues

The hybrid LLM + Rules approach intended to improve secondary detection but caused regressions:

**Original Hypothesis** (Pre-Implementation):
- LLM would catch contextual signals missed by keyword-based rules
- Example: "calls for someone else" → FDCPA inference (no "debt" keyword needed)
- Target: 78-88% accuracy

**Actual Outcome**:
- LLM is too aggressive with FDCPA inference
- False positives outweigh true positives
- 42% accuracy (21% worse than baseline)

**Evidence**:
- Multiple false positives for FDCPA secondary detections
- Baseline (rule-based only) had 63% accuracy
- Hybrid (LLM + rules) dropped to 42% accuracy
- **Conclusion**: Hybrid approach failed to meet objectives

---

## Recommended Actions

### Priority 1: **ROLLBACK HYBRID APPROACH** (IMMEDIATE)

The hybrid approach did not meet expectations (42% vs target 78-88%).

**Action**: Revert to rule-based only for secondary area detection.

**Implementation**:
```python
# In app/services/summary_generator.py, line ~60:
# Set LLM suggestions to empty list (disables hybrid approach)
llm_secondary = []  # Disable LLM suggestions

# Keep only rule-based detection:
secondary = merge_secondary_areas(
    llm_suggestions=[],  # Empty - no LLM input
    rule_based=rule_based_secondary,
    primary_area=cls_result.primary_practice_area
)
```

**Expected Outcome**:
- Secondary accuracy: 42% → ~63% (restore baseline)
- Cross-practice flag: 61% → ~82% (restore baseline)

**Rollback Strategy**: Low-risk change, single line modification.

---

### Priority 2: **INVESTIGATE LLM SECONDARY SUGGESTIONS** (DIAGNOSTIC)

Before completely abandoning hybrid approach, understand why it failed.

**Action**: Query database to examine actual LLM outputs.

**Diagnostic Queries**:
```sql
-- Find conversations with LLM-inferred secondary areas
SELECT
    conversation_id,
    summary->>'secondary_practice_areas' as secondary_areas
FROM intake_summaries
WHERE summary->>'secondary_practice_areas' LIKE '%llm_inferred%'
LIMIT 20;

-- Check LLM classification results
SELECT
    conversation_id,
    result->>'secondary_practice_areas' as llm_suggestions,
    prompt_hash
FROM llm_call_records
WHERE task_type = 'classification'
ORDER BY created_at DESC
LIMIT 20;
```

**Analysis Goals**:
1. Identify which phrases trigger false positive FDCPA detections
2. Check confidence scores of LLM suggestions (are they barely meeting 0.7 threshold?)
3. Review LLM reasoning fields to understand inference logic
4. Determine if specific prompt wording is causing over-triggering

---

### Priority 3: **REFINE PRIMARY CLASSIFICATION PROMPT** (NEXT ITERATION)

Primary classification is stuck at 78% with persistent TCPA ↔ FDCPA swaps.

**Current Prompt Issue**: Abstract guidance ("METHOD vs CONDUCT") isn't being followed.

**Recommended Approach**: Few-shot learning with concrete examples.

**Implementation**:
Add to `app/prompts/system_prompt_v1.txt` [CLASSIFICATION_SYSTEM] section:

```
EXAMPLES:

Example 1: TCPA (method-focused)
User: "A debt collector keeps calling my cell phone repeatedly."
→ Primary: TCPA (unauthorized cell phone calls)
→ Secondary: [{"area": "FDCPA", "confidence": 0.6, "reason": "debt collection context"}]
→ Reasoning: "The PRIMARY issue is the METHOD of contact (cell phone calls). The debt collection context is secondary."

Example 2: FDCPA (conduct-focused)
User: "A debt collector called me and said they would garnish my wages if I didn't pay immediately."
→ Primary: FDCPA (threatening conduct)
→ Secondary: []
→ Reasoning: "The PRIMARY issue is the debt collector's threatening CONDUCT, not the method of contact."

Example 3: TCPA + FDCPA (method primary)
User: "I keep getting robocalls about a debt I already paid."
→ Primary: TCPA (robocalls - automated calling method)
→ Secondary: [{"area": "FDCPA", "confidence": 0.8, "reason": "debt collection on paid debt"}]
→ Reasoning: "The PRIMARY issue is robocalls (TCPA violation). The debt collection context is strong secondary."

Example 4: FCRA (credit report primary)
User: "There's an error on my credit report and the company keeps calling about it."
→ Primary: FCRA (credit reporting error)
→ Secondary: [{"area": "TCPA", "confidence": 0.5, "reason": "repeated calling mentioned"}]
→ Reasoning: "The PRIMARY issue is the credit report error. Calls are secondary."
```

**Expected Impact**:
- Few-shot examples provide concrete decision patterns
- Should reduce TCPA ↔ FDCPA swap rate
- Target: 78% → 85-90% primary accuracy

---

### Priority 4: **ALTERNATIVE - STRICTER LLM CONFIDENCE THRESHOLD** (IF NOT ROLLING BACK)

If hybrid approach is retained, reduce false positives by increasing confidence threshold.

**Current**: `min_llm_confidence = 0.7` (70%)
**Proposed**: `min_llm_confidence = 0.85` or `0.90` (85-90%)

**Implementation**:
```python
# In app/services/cross_practice.py, line ~70:
def merge_secondary_areas(
    llm_suggestions: list[SecondaryPracticeArea],
    rule_based: list[SecondaryPracticeArea],
    primary_area: PracticeArea,
    min_llm_confidence: float = 0.85  # Increased from 0.7
) -> list[SecondaryPracticeArea]:
    ...
```

**Trade-off**:
- Reduces false positives (fewer weak LLM suggestions accepted)
- May also reduce true positives (some valid contextual detections rejected)
- Unknown if this will restore 63% baseline or still underperform

**Recommended**: Only try this if diagnostic investigation (Priority 2) shows LLM suggestions are borderline (0.7-0.8 range).

---

## Testing Validation Plan

After implementing any changes, re-run full replay test:

```bash
# Start server in background
source .venv/Scripts/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &

# Run replay test
python replay_runner.py

# Compare results to current baseline
```

**Success Criteria**:
- Secondary accuracy: ≥63% (baseline) or ≥78% (original hybrid target)
- Cross-practice flag: ≥82% (baseline)
- Primary classification: ≥85% (improvement from current 78%)
- Recommendation logic: ≥75% (maintain current improvement)

---

## Decision Required

**Question**: Which action should be taken first?

1. **Rollback hybrid approach** (restore secondary accuracy to 63% baseline) ← RECOMMENDED
2. **Investigate LLM suggestions** first (diagnostic query to understand failure mode)
3. **Increase confidence threshold** to 0.85/0.9 (attempt to fix hybrid false positives)
4. **Focus on primary classification** improvements instead (few-shot examples)

**Recommended Path**:
- **Immediate**: Rollback hybrid (Priority 1) to restore baseline performance
- **Next**: Investigate why hybrid failed (Priority 2) for learning
- **Then**: Improve primary classification with few-shot examples (Priority 3)
- **Future**: Re-evaluate hybrid approach with stricter criteria if diagnostic reveals fixable issues

---

## Files Referenced

- `replay_results.json` - Current test results (100 cases)
- `app/services/summary_generator.py` - Integration point for hybrid approach
- `app/services/cross_practice.py` - Hybrid merge logic
- `app/prompts/system_prompt_v1.txt` - Classification and recommendation prompts
- `app/schemas.py` - LLMClassificationResult schema

---

## Appendix: Failure Case Examples

### False Positive FDCPA (Secondary Detection Over-Triggering)

- **REPLAY-005**: Expected `[]`, got `["FDCPA"]`
  - Conversation ID: `0e6c8853-e6bd-4a0b-9cf6-d82a2d9b4b77`
  - Likely: LLM inferred FDCPA from weak debt-related language

- **REPLAY-006**: Expected `[]`, got `["FDCPA"]`
  - Conversation ID: `0e181c03-d02c-4e16-abdb-588c4c2346c8`

- **REPLAY-011, 012, 017, 018**: Same pattern (false positive FDCPA)

### Primary Classification Swaps

- **REPLAY-004**: Expected TCPA, got FCRA
  - Conversation ID: `85a8d060-086f-4666-a8ba-d1af9c4c9b70`
  - Credit context overriding call method

- **REPLAY-007**: Expected TCPA, got FDCPA
  - Conversation ID: `e9f57af2-37b7-4d32-bc51-47e0cc127586`
  - Debt collection context overriding call method

- **REPLAY-013, 019**: Same TCPA → FDCPA swap pattern

### Missing Secondary Areas

- **REPLAY-010**: Expected `["FCRA", "FDCPA"]`, got `["FDCPA"]`
  - Conversation ID: `47fda434-1402-429d-8467-ed4936ee6bd0`
  - Missing FCRA secondary area

---

**END OF ANALYSIS**
