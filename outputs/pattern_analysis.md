# Pattern Analysis — Sidekick Group Bookings QA

**Conversations audited:** 50
**Issues flagged:** 16
**Expert review queue:** 1
**Passed:** 32
**Correct deferrals:** 1

## Top systemic patterns

### 1. Outdated KB articles driving errors

Articles 2, 4, 9, and 10 contain superseded minimums, attrition, and commission guidance. Sidekick cites these and produces wrong hotel/cruise minimums, wedding attrition advice, and Hyatt rates.

- Related issue count (proxy): 13

### 2. Inverted or outdated attrition negotiation guidance

Article 4 suggests pushing 15% attrition and that lower attrition improves rates. Article 3 and HQ Source 1 indicate 20-30% is standard and wedding blocks should not over-optimize attrition.

- Related issue count (proxy): 9

### 3. Missing HQ operational nuance

TC credit splitting, Hyatt 2026 program rates, comp ratio negotiation, and Japan DMC/TO hybrid options exist in HQ sources but are absent or incomplete in Sidekick responses.

- Related issue count (proxy): 18

### 4. Overconfident answers vs appropriate deferral

Some responses state definitive policy where KB is silent; others correctly defer to Tour Ops (e.g., Japan pricing).


### 5. DMC vs tour operator oversimplification

Article 10 and Sidekick responses lack hybrid approach, cost ranges, and commission tradeoffs documented in HQ Source 4.

- Related issue count (proxy): 2

## Issue type breakdown

- `factual_error`: 8
- `outdated_kb_cited`: 8
- `incomplete`: 7
- `wrong_priority`: 1
- `kb_contradiction`: 1

## Articles most often targeted for fixes

- Article 4: 6
- Article 2: 3
- Article 3: 3
- Article 9: 2
- Article 1: 2
- Article 8: 2
- Article 10: 2

## Severity distribution (flagged conversations)

- P2: 8
- P1: 7
- P0: 2

## Stakeholder routing

- tour_ops: 11
- booking_platform: 7

## Assumptions flagged for expert review

- Conv 50: Attrition recommendation spans 20-30% with judgment factors; borderline vs other wedding guidance