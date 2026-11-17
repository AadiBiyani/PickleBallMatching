# Requirements index

A lookup table for `docs/software-development-plan.md`. Use the plan for exact wording, rationale, and full test methods. Thresholds are initial targets that the team will review after pilot testing.

## System capabilities

| ID | Capability |
| --- | --- |
| SYS-01 | Player accounts and profiles. Measured attributes are kept apart from self-reported ones |
| SYS-02 | Guided drill recording with live camera validation that gates recording |
| SYS-03 | Video upload and background processing with status, retries, and no duplicates |
| SYS-04 | Court, player, and ball analysis. Attempt classification. Camera-movement detection |
| SYS-05 | Coverage profiles and results with attempt-level evidence |
| SYS-06 | Partner recommendations from complementary coverage plus configurable factors |
| SYS-07 | Explainable comparisons and recommendation history |
| SYS-08 | Data access, consent, and retention. Raw recordings expire 30 days after upload by default |

## Functional requirements

All are Must Have.

| ID | SYS | Requirement | Key test detail |
| --- | --- | --- | --- |
| FR-01 | 01 | Registration and authentication create a session tied to a unique player account | Sign-in, sign-out, duplicate, and invalid-credential cases. Users reach only their own data |
| FR-02 | 01 | Valid profile changes are saved and shown on reopen | Invalid values are rejected without overwriting valid data |
| FR-03 | 02 | A selected drill shows the instructions for its current version | The version is stored with the session |
| FR-04 | 02 | Recording is disabled with a red status and guidance while any camera check fails, and enabled with a green status when all pass | At least 10 accepted and 10 rejected setups |
| FR-05 | 02 | A finished recording is saved with player ID, session ID, drill version, feed method, and timestamps | Five recordings, each with a distinct session ID |
| FR-06 | 03 | A finished upload is submitted for analysis and its status is visible | uploaded, queued, processing, completed. Failed has a reason |
| FR-07 | 03 | A failed upload keeps the local recording and retries under the same session ID | Interrupt at three progress points. No extra sessions |
| FR-08 | 04 | After court calibration, produce timestamped ground-position estimates in normalized court coordinates | Verified against NFR-06 |
| FR-09 | 04 | Create timestamped attempt records classified as successful, unsuccessful, invalid feed, or uncertain | Verified against NFR-05. Each attempt has evidence timestamps |
| FR-10 | 05 | Uncertain and invalid-feed attempts are excluded from scored counts and metrics, with the reason kept | Fixture: 6 successes, 2 failures, 1 invalid, 1 uncertain gives 8 scored, 75%, 2 exclusions |
| FR-11 | 05 | With enough scored attempts, generate a coverage profile with movement measurements, success rates, and sample counts per region and stage | Proposed minimum of 5 scored attempts per region and stage. Below that the region is marked insufficient |
| FR-12 | 05 | A completed session shows the coverage visualization, scored and excluded counts, limitations, and attempt evidence | Selecting an attempt opens its video segment |
| FR-13 | 06 | A recommendation request retrieves other registered players with usable, compatible profiles who pass the hard filters | Seeded database. The exact expected candidate set, without the requester |
| FR-14 | 06 | Return up to five candidates in descending compatibility order, each with an explanation | At least 10 synthetic profile sets, including ties and fewer than five candidates |
| FR-15 | 05, 06 | A new compatible assessment with sufficient data creates a new profile version used for later requests | Both versions stay stored. A failed assessment never replaces a usable profile |

## Non-functional requirements

Benchmark conditions for timing: recordings up to 60 s at 1080p and 60 fps, at most 50 MB, an upload link of at least 20 Mbps, one active job, and a warm worker.

| ID | SYS | Requirement | Threshold | Priority |
| --- | --- | --- | --- | --- |
| NFR-01 | 03, 05 | Analysis turnaround, timed from recording stop | Results within 60 s in at least 18 of 20 runs. Failed analyses count as misses | Must |
| NFR-02 | 02 | Camera feedback responsiveness | Status updates within 1 s in at least 19 of 20 scene changes | Must |
| NFR-03 | 01, 03, 05 | Access control | Every unauthorized request fails. Private storage, HTTPS, expiring URLs | Must |
| NFR-04 | 03, 05 | Duplicate-processing reliability | At most one published result set per session ID and analysis version | Must |
| NFR-05 | 04, 05 | Outcome classification quality | Macro-F1 of 0.85 or more across successful and unsuccessful, while scoring at least 80% of valid attempts. At least 100 valid-feed attempts from 5 or more players, with at least 40 successes and 40 failures and both feed methods | Must |
| NFR-06 | 04 | Court-position accuracy | Mean error of 0.30 m or less over 30 measured positions across 3 or more camera setups. Report mean, maximum, 95th percentile, and missing estimates | Must |
| NFR-07 | 02, 05, 06 | First-time usability | 4 of 5 participants finish setup, one recording, and results review within 15 minutes unaided | Should |
| NFR-08 | 03-06 | Automated regression checks on pull requests | Required checks block a failing merge | Should |

Evaluation rules that apply across NFR-05 and NFR-06:

- Evaluation sessions are excluded from training and threshold tuning.
- Two reviewers establish reference labels.
- Attempts wrongly rejected as invalid or uncertain lower the retained percentage.
- Missing position estimates cannot be silently removed.

## Under evaluation and out of scope

| ID | Item |
| --- | --- |
| SYS-UE-01 | Personalized positioning recommendations for a pair |
| SYS-UE-02 | Automatic skill and play-style inference from footage |
| SYS-UE-03 | Additional phones, camera placements, lighting, and courts |
| SYS-OOS-01 | Full-match analysis and live officiating |
| SYS-OOS-02 | Offline video analysis |
| SYS-OOS-03 | Scheduling and social features |

## Assumptions and constraints that shape design

- A-02 and C-03: one stationary phone per recording, with the player, net, and relevant court lines visible.
- A-05: human feeds vary. The system must detect invalid feeds and compare like with like.
- A-06: coverage measurements informing recommendations is a hypothesis under test.
- C-02: software only. Existing phones and equipment.
- C-05: processing is bounded by available compute and the approved cloud budget.
- C-06: a validated subset of iPhone models first.

## Deliverables

| ID | Deliverable | Requirements |
| --- | --- | --- |
| D-01 | Installed iOS mobile application | FR-01 to FR-05, FR-12, NFR-02, NFR-07 |
| D-02 | Backend and processing infrastructure | FR-06, FR-07, NFR-01, NFR-03, NFR-04 |
| D-03 | Video analysis and court-coverage pipeline | FR-08 to FR-12, FR-15, NFR-05, NFR-06 |
| D-04 | Partner-matching module | FR-13 to FR-15, NFR-07 |
| D-05 | Evaluation and reproducibility package, including a requirements-to-test traceability matrix | Evidence for all FR and NFR. Implements NFR-08 |

## Open instructor feedback on the plan

These points are unresolved. Keep them in mind when a task touches the same area.

- **Reduce recording variability (SYS-02).** Consider time-limited, more tightly constrained recordings so automated analysis is feasible.
- **Under-evaluation items** need the deciding data and a decision date.
- **A-05:** say how a recording is judged valid or invalid in practice.
- **A-06** is a strong assumption that the project's feasibility depends on. Support it with first-principles analysis.
- **Ground-truth pairs:** identify pairings known to be good and known to be bad, then check that the software agrees.
- **FR-11 and FR-15** wording is hard to follow. **FR-14's** test method needs detail on the hand calculation.
- **NFR-05 and NFR-06** arguably belong with the functional requirements.
- **NFR-01:** the 60 s figure needs support from comparable published applications.
- **All NFRs:** name the hardware and OS versions used for evaluation.
- The MoSCoW section was not submitted.
