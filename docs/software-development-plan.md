Software Development Plan
Team: Team #2
Project: Personalized Doubles Partner Coordination
Team Members: Aadi Biyani, Nishaant Shah, Liam He, Logan Hanson
Course: ECE 49595 SD I
Semester: Fall 2026
1. Project Overview
Our project will help pickleball players find doubles partners whose movement capabilities and court coverage complement their own. Players will complete individual drills using an installed mobile application that validates camera placement, records footage, and uploads videos for automatic analysis. The system will generate coverage profiles and recommend potential partners using measured capabilities alongside factors such as location, skill level, and play preferences.
2. Scope
2.1 In Scope
SYS-01: Player Accounts and Profiles
Description: Support account registration, authentication, persistent player profiles containing reviewed assessment results, player strengths, preferred court side, self-reported play style, and manual skill rating. Our application should distinguish measured attributes from self-reported information and retain each rating’s source and data.
Justification: Persistent identities connect recordings to the correct player and allow registered users to participate in partner recommendations.
SYS-02: Guided Drill Recording
Description: Provide drill instructions, live camera-placement validation, and recording through an installed mobile application. Support human feeders and ball machines, with prescribed and reactive drill stages. Display actionable setup feedback and block recording until camera checks pass.
Justification: Consistent recording conditions and drill instructions are necessary to produce useful, comparable measurements. 
SYS-03: Video Upload and Background Processing
Description: Securely upload recordings, schedule server-side analysis, and communicate processing progress or failures. Passing setup checks reduces recording problems but does not guarantee that every attempt can be analyzed. Support retries without creating duplicate sessions or scored attempts, and retain the processing version associated with each result.
Justification: Background processing supports computationally demanding video analysis while keeping the application responsive.
SYS-04: Court, Player, and Ball Analysis
Description: Estimate court geometry and player movement, track ball events, and classify attempts as successful, unsuccessful, invalid feeds, or uncertain. Detect camera movement and exclude affected segments until back to acceptable position.
Justification: Automatic analysis provides the measurements needed to assess coverage without requiring users to label every attempt.
SYS-05: Coverage Profiles and Results
Description: Produce individual coverage summaries, supporting visualizations, and attempt-level evidence. Exclude uncertain attempts from scoring and identify insufficient data.
Justification: Players need understandable results, and the matching engine needs consistent measurements with known limitations.
SYS-06: Partner Recommendations
Description: Recommend registered players using complementary coverage and configurable matching factors, including location, skill level, and play preferences.
Justification: Finding suitable partners is the project’s primary user-facing outcome.
SYS-07: Explainable Comparisons and Recommendation History
Description: Display lineup alternatives, pair-level coverage gaps, score contributions, uncertainty, and a ratings-only comparison under the same roster constraints. Retain the profile versions, constraints, and scoring settings used to generate each comparison. Identify unstable rankings rather than presenting small differences as decisive.
Justification: Captains need to understand recommendations and assess whether coverage measurements add useful information beyond existing ratings.
SYS-08: Data Access, Consent, and Retention
Description: Enforce access permissions for players, captains/coaches, and administrators. Require recording and assessment consent, keep footage private, and restrict team information to authorized users. Support deletion requests and the proposed default expiration of raw recordings and evidence clips 30 days after upload. Require separate consent for research retention.
Justification: The system handles identifiable recordings and assessments that may affect team-selection decisions. Defined permissions and retention controls support responsible participation and data management.

2.2 Under Evaluation
SYS-UE-01: Personalized Positioning Recommendations
Description: Suggest starting positions and court responsibilities for a recommended partnership.
Issue / Uncertainty: Individual drill measurements may not adequately represent two players reacting together during a match.
Evaluation Plan: Compare predicted coverage with recorded paired drills and coach feedback before deciding whether positioning recommendations are reliable enough to include.
SYS-UE-02: Automatic Skill and Play-Style Inference
Description: Infer skill level and playing style directly from footage.
Issue / Uncertainty: Short movement drills may not capture shot selection, consistency, or tactical preferences.
Evaluation Plan: Compare candidate video-derived attributes with player reports and coach assessments. Use self-reported attributes in the baseline system.
SYS-UE-03: Expanded Device and Recording Support
Description: Support additional phone models, camera placements, lighting conditions, and court environments beyond the initial validated configuration.
Issue / Uncertainty: Ball visibility and tracking accuracy may vary substantially across devices and environments.
Evaluation Plan: Benchmark representative devices and recording conditions. Add a configuration to the supported list only after it meets the camera-validation and analysis criteria.
2.3 Out of Scope
SYS-OOS-01: Full-Match Analysis and Live Officiating
Description: Analyze unrestricted four-player matches, provide live tactical coaching, or make official line calls.
Justification: The MVP focuses on controlled individual drills. Full-match analysis introduces additional tracking, occlusion, and timing challenges.
SYS-OOS-02: Offline Video Analysis
Description: Perform the complete analysis and matching workflow without an internet connection.
Justification: The baseline architecture relies on server-side processing and a shared player database.
SYS-OOS-03: Scheduling and Social Features
Description: Provide messaging, court reservations, payments, or tournament management.
Justification: These features do not establish the feasibility or usefulness of coverage-based partner matching.

2.4 Assumptions
A-01: Participating players and feeders will receive instructions and attempt to follow the prescribed setup and drill protocol. The system must still detect supported setup violations, invalid feeds, and uncertain observations.
A-02: Recordings will use a stationary phone with sufficient visibility of the player, net, and relevant court boundaries.
A-03: The team will have access to a court, consenting participants, and recordings from both human-fed and machine-fed drills.
A-04: Users will provide reasonably accurate location, skill, and play-preference information.
A-05: Human-fed attempts will vary in difficulty. The system must identify invalid feeds and compare performance under sufficiently similar drill conditions.
A-06: Individual coverage measurements can inform partner recommendations, but improved match performance remains a hypothesis to evaluate.
2.5 Constraints
C-01: Development must fit within the two-semester senior design schedule and the team’s available time.
C-02: The project is software-focused and will use existing phones and sporting equipment rather than custom hardware.
C-03: The MVP will use one stationary phone camera per drill recording.
C-04: Internet access is required for uploading recordings, retrieving analysis, and receiving recommendations.
C-05: Processing capacity is limited by available computing resources and the approved cloud budget.
C-06: The initial mobile application will support a validated subset of iPhone models and recording configurations. Supported lighting, camera placement, and drill duration will be documented following testing.
3. Software Requirements
Numerical thresholds are initial acceptance targets and will be reviewed after pilot testing. Changes will be documented with their rationale and affected requirements.
3.1 Functional Requirements
FR-01: Account Registration and Authentication
System Requirement: SYS-01
Statement: When a user completes registration and authenticates successfully, the system shall establish a session associated with a unique player account.
Rationale: Recordings and results must belong to an identifiable user.
Test Method: Verify registration, sign-in, sign-out, duplicate registration, and invalid-credential cases. All expected authentication outcomes must pass, proving that user’s can only add, modify, and view the data they are authenticated to see (their own).
Supporting Context: Authentication will use a managed identity provider; private application data requires an authenticated session.
Trace: SYS-01: Player Accounts and Profiles
Priority: Must Have
FR-02: Player Profile Management
System Requirement: SYS-01
Statement: When an authenticated player submits valid profile changes, the system shall save those changes and display them when the profile is reopened.
Rationale: Matching requires current player information and preferences.
Test Method: Update each supported field, reload the application, and verify persistence. Confirm that invalid values are rejected without overwriting valid data.
Supporting Context: Initial fields include display name, approximate location, handedness, self-reported skill, play preferences, and matching preferences.
Trace: SYS-01: Player Accounts and Profiles
Priority: Must Have
FR-03: Versioned Drill Instructions
System Requirement: SYS-02
Statement: When a player selects a supported drill, the system shall display the instructions associated with that drill’s current version.
Rationale: Comparable measurements depend on consistent procedures.
Test Method: Verify that every available drill displays its starting position, feed method, stages, target regions, and completion instructions. Confirm that the selected version is stored with the session.
Supporting Context: Drill definitions will distinguish prescribed and reactive stages and specify human-feeder or ball-machine instructions.
Trace: SYS-02: Guided Drill Recording
Priority: Must Have
FR-04: Camera Validation and Recording Gate
System Requirement: SYS-02
Statement: While any required camera-setup check fails, the system shall disable recording and display a red status with corrective guidance; while all checks pass, the system shall display a green status and enable recording.
Rationale: If the camera is at an angle where the player or court is out of frame, then the results of the measured drills will be unreliable and difficult to normalize.
Test Method: Test at least 10 accepted and 10 rejected setup cases. Verify the correct recording state and guidance for every case.
Supporting Context: Checks cover required court and net visibility, player visibility, stability, and image quality. Text accompanies the colors. Passing the setup checks does not guarantee that the remainder of the frames recorded will be correct, however, we should assume that the camera does not move during the drills (the user will be suggested to use a tripod).
Trace: SYS-02: Guided Drill Recording
Priority: Must Have
FR-05: Drill Recording and Session Metadata
System Requirement: SYS-02
Statement: When a player completes a recording, the system shall save the video with its player ID, session ID, drill version, feed method, and capture timestamps.
Rationale: Analysis must interpret each recording using the correct drill conditions, and associate it with the correct player.
Test Method: Complete five recordings and verify that each playable file is associated with the correct metadata and a distinct session ID.
Supporting Context: Each recording assesses one player, although a feeder may also appear in the footage.
Trace: SYS-02: Guided Drill Recording
Priority: Must Have
FR-06:  Upload and Analysis Status
System Requirement: SYS-03
Statement: When a valid recording finishes uploading, the system shall submit it for analysis and expose the session’s current processing status to the player.
Rationale: Users need confirmation that their recording was received and is progressing.
Test Method: Process five valid recordings and verify the expected progression through uploaded, queued, processing, and completed states. Confirm that an incomplete upload does not enter analysis.
Supporting Context: Failed sessions should have an explicit failed status and an understandable explanation.
Trace: SYS-03: Video Upload and Background Processing
Priority: Must Have
FR-07: Failed Upload Recovery
System Requirement: SYS-03
Statement: If an upload fails, then the system shall retain the local recording and allow the player to retry uploading it under the same session ID.
Rationale: Temporary connectivity problems should not require repeating a drill.
Test Method: Interrupt uploads at three different progress points. Restore connectivity and verify that all three recordings upload successfully without creating additional sessions.
Supporting Context: On a failure we will restart uploading after a failure, we are not required to resume from the byte of the video where the upload previously failed. 
Trace: SYS-03: Video Upload and Background Processing
Priority: Must Have
FR-08: Court-Coordinate Movement Estimates
System Requirement: SYS-04
Statement: When court calibration succeeds, the system shall produce timestamped estimates of the assessed player’s ground position in a normalized court-coordinate system.
Rationale: Positions measured in pixels cannot be compared reliably across different camera placements, instead we will project the pixel coordinates onto a common 2 dimensional space coordinates on a standard pickleball court using homography.
Test Method: Analyze recordings with known reference positions and verify the coordinate output against NFR-06.
Supporting Context: Court-plane mapping applies to estimated ground positions. Airborne ball positions require separate trajectory and event analysis.
Trace: SYS-04: Court, Player, and Ball Analysis
Priority: Must Have
FR-09: Automatic Attempt Classification
System Requirement: SYS-04
Statement: When the system analyzes a drill recording, it shall create timestamped attempt records classified as successful return, unsuccessful return, invalid feed, or uncertain.
Rationale: To properly assess a player’s coverage, we need to know both movement information and evidence that the player returned the ball successfully.
Test Method: Compare predictions with independently labeled recordings using NFR-05. Verify that each detected attempt has a classification and evidence timestamps.
Supporting Context: A successful return must satisfy the selected drill’s rules, including crossing the net and landing in its permitted region. A confidently observed missed or failed return is unsuccessful, and impacts the results of the analysis.
Trace: SYS-04: Court, Player, and Ball Analysis
Priority: Must Have
FR-10: Exclusion of Unusable Attempts
System Requirement: SYS-05
Statement: If an attempt is classified as uncertain or an invalid feed, then the system shall exclude it from scored-attempt counts and derived coverage metrics while retaining its exclusion reason.
Rationale: Unusable evidence should not distort the player’s assessment, however the player should be able to observe the reason why it was excluded, and potentially override if they disagree / think it was misclassified.
Test Method: Use a fixture containing six successes, two failures, one invalid feed, and one uncertain attempt. Verify eight scored attempts, a 75% success rate, and two separately reported exclusions.
Supporting Context: Confidently observed failures remain in the denominator. Excluded attempts remain available for auditing.
Trace: SYS-05: Coverage Profiles and Results
Priority: Must Have
FR-11: Coverage Profile Generation
System Requirement: SYS-05
Statement: When sufficient scored attempts are available, the system shall generate a coverage profile containing movement measurements, return-success rates, and sample counts for the required drill regions and stages.
Rationale: The matching engine needs structured measurements that distinguish strengths, weaknesses, and missing evidence.
Test Method: Compare profile calculations with manually calculated fixtures. Verify that regions below the configured sample minimum are marked insufficient rather than assigned a performance score.
Supporting Context: The initial proposed minimum is five scored attempts per required region and stage, subject to pilot review. Comparisons use compatible drill versions and timing definitions.
Trace: SYS-05: Coverage Profiles and Results
Priority: Must Have
FR-12: Results and Supporting Evidence
System Requirement: SYS-05
Statement: When a player opens a completed session, the system shall display its coverage visualization, scored and excluded attempt counts, measurement limitations, and associated attempt evidence.
Rationale: Results must be understandable and traceable to the recording.
Test Method: For five completed sessions, verify displayed values against stored results and confirm that selecting an attempt opens its corresponding video segment.
Supporting Context: Insufficient-data regions must appear distinctly from measured low-performance regions.
Trace: SYS-05: Coverage Profiles and Results
Priority: Must Have
FR-13: Candidate Eligibility and Filtering
System Requirement: SYS-06
Statement: When a player requests partner recommendations, the system shall retrieve other registered players with usable, compatible assessment profiles who satisfy the requester’s active hard filters.
Rationale: Recommendations must be based on usable assessments and relevant preferences.
Test Method: Use a seeded database with eligible, incomplete, incompatible, and filtered-out profiles. Verify the exact expected candidate set, including exclusion of the requester.
Supporting Context: Any registered player may become eligible by completing the required assessment. Hard filters, such as distance, are distinguished from factors used only for ranking.
Trace: SYS-06: Partner Recommendations
Priority: Must Have
FR-14: Ranked and Explained Recommendations
System Requirement: SYS-06
Statement: When eligible candidates exist, the system shall return up to five candidates in descending compatibility order with an explanation of the factors contributing to each recommendation.
Rationale: Players need to understand why a proposed partner may suit them.
Test Method: Compare rankings against hand-calculated results for at least 10 synthetic profile sets. Include ties, fewer than five candidates, and pairs where complementary coverage changes the expected ranking.
Supporting Context: Scoring will include coverage complementarity and selected profile factors. Weights and tie-breaking rules will be versioned. A compatibility score is not a predicted probability of winning.
Trace: SYS-06: Partner Recommendations
Priority: Must Have
FR-15: Assessment Updates and Version History
System Requirement: SYS-05, SYS-06
Statement: When a new compatible assessment produces sufficient data, the system shall create a new profile version and use it for subsequent recommendation requests.
Rationale: Recommendations should reflect current capabilities while preserving the evidence behind earlier results.
Test Method: Process an initial assessment and a later assessment with different outcomes. Verify that both versions remain stored and new recommendations reference the updated version.
Supporting Context: An incomplete or failed assessment must not replace a previously usable profile. Historical session results remain associated with their original analysis versions.
Trace: SYS-05: Coverage Profiles and Results; SYS-06 — Partner Recommendations
Priority: Must Have
3.2 Non-Functional Requirements
The initial performance benchmark will use recordings up to 60 seconds long, at 1080p and 60 frames per second, with a maximum file size of 50 MB. Tests will use a sustained upload connection of at least 20 Mbps, one active analysis job, and a provisioned worker with models already loaded. These conditions are proposed and must be confirmed during prototyping.
NFR-01: Analysis Turnaround Time
System Requirement: SYS-03, SYS-05
Statement: When a player finishes a recording under the defined benchmark conditions, the system shall make its results available within 60 seconds in at least 90% of benchmark runs.
Rationale: Players should receive feedback shortly after completing a drill.
Test Method: Run 20 end-to-end trials. At least 18 must meet the limit; failed analyses count as missed targets. Record upload, queue, processing, and retrieval times separately.
Supporting Context: Timing begins when recording stops and includes automatic upload. Hardware and software versions must be recorded with the results.
Trace: SYS-03: Video Upload and Background Processing; SYS-05 — Coverage Profiles and Results
Priority: Must Have
NFR-02: Camera Feedback Responsiveness
System Requirement: SYS-02
Statement: While camera setup is active, the system shall update its visible setup status within one second of a relevant scene change in at least 95% of tested cases.
Rationale: Delayed feedback makes camera placement confusing.
Test Method: Introduce 20 controlled changes, including camera movement and loss of required visibility. At least 19 status updates must meet the limit.
Supporting Context: Tests run on each supported phone configuration and measure from the visible scene change to the displayed response.
Trace: SYS-02: Guided Drill Recording
Priority: Must Have
NFR-03: Access Control
System Requirement: SYS-01, SYS-03, SYS-05
Statement: If a request lacks valid authorization for a private recording or assessment, then the system shall deny access to that resource.
Rationale: Uploaded footage and individual assessment records must not be exposed through predictable identifiers or public storage.
Test Method: Test unauthenticated access, cross-account access, expired credentials, and expired signed URLs. All unauthorized requests must fail without returning private content.
Supporting Context: Video storage remains private, transport uses HTTPS, and temporary media URLs expire. Matching responses expose only designated profile fields, not another player’s private footage.
Trace: SYS-01: Player Accounts and Profiles; SYS-03 — Video Upload and Background Processing; SYS-05: Coverage Profiles and Results
Priority: Must Have
NFR-04: Duplicate-Processing Reliability
System Requirement: SYS-03, SYS-05
Statement: If an analysis job is retried or delivered more than once, then the system shall publish at most one completed result set for the same session ID and analysis version.
Rationale: Retries must not inflate attempt counts or corrupt profiles.
Test Method: Repeat job submission 10 times and interrupt workers during five additional runs. After recovery, verify one consistent published result set per session and version.
Supporting Context: Multiple execution attempts are acceptable; duplicate published results are not. Partial outputs must not become visible as completed profiles.
Trace: SYS-03: Video Upload and Background Processing; SYS-05 — Coverage Profiles and Results
Priority: Must Have
NFR-05: Outcome Classification Quality
System Requirement: SYS-04, SYS-05
Statement: When analyzing the held-out evaluation set, the system shall achieve a macro F1 score of at least 0.85 across successful and unsuccessful returns while scoring at least 80% of ground-truth-valid attempts.
Rationale: Accuracy must be measured alongside the proportion of attempts retained.
Test Method: Evaluate at least 100 valid-feed attempts from at least five players, including at least 40 successes and 40 failures and both feed methods. Report classification metrics, exclusions, missed attempts, and spurious detections.
Supporting Context: Evaluation sessions are excluded from training and threshold tuning. Two reviewers establish reference labels and resolve disagreements. Attempts wrongly rejected as invalid or uncertain reduce the retained-attempt percentage.
Trace: SYS-04: Court, Player, and Ball Analysis; SYS-05 — Coverage Profiles and Results
Priority: Must Have
NFR-06: Court-Position Accuracy
System Requirement: SYS-04
Statement: When the player occupies a measured reference position under supported capture conditions, the system shall estimate the player’s ground position with a mean error no greater than 0.30 meters across the reference test set.
Rationale: Large position errors could change coverage estimates and partner rankings.
Test Method: Compare estimates at 30 measured positions across at least three accepted camera setups. Report mean, maximum, and 95th-percentile error, plus missing estimates.
Supporting Context: The reference point and estimated point must use the same definition of player ground position. Missing estimates cannot be silently removed to improve the error metric.
Trace: SYS-04: Court, Player, and Ball Analysis
Priority: Must Have
NFR-07: First-Time User Usability
System Requirement: SYS-02, SYS-05, SYS-06
Statement: When first-time participants follow the application’s instructions, at least four of five participants shall complete camera setup, one supported recording, and results review within 15 minutes without interface assistance from the development team.
Rationale: Players should be able to use the system outside a supervised demonstration.
Test Method: Conduct five observed usability sessions and record completion time, errors, and assistance requests.
Supporting Context: A feeder may help run the drill. The criterion concerns application use, and participants may consult the app’s instructions.
Trace: SYS-02: Guided Drill Recording; SYS-05: Coverage Profiles and Results; SYS-06: Partner Recommendations
Priority: Should Have
NFR-08: Automated Regression Checks
System Requirement: SYS-03, SYS-04, SYS-05, SYS-06
Statement: When a pull request changes application code, the development pipeline shall run the designated automated checks and report failure if any required check fails.
Rationale: Changes to scoring, storage, or ranking must not silently break established behavior.
Test Method: Submit one passing change and one change containing a deliberate regression. Verify the expected pipeline results and that required checks block merging the failing change.
Supporting Context: Checks include backend tests, scoring and matching fixtures, database validation, and mobile type checking. Hardware-dependent acceptance tests remain documented manual tests.
Trace: SYS-03: Video Upload and Background Processing; SYS-04: Court, Player, and Ball Analysis; SYS-05: Coverage Profiles and Results; SYS-06: Partner Recommendations
Priority: Should Have
4. Deliverables
D-01: Installed iOS Mobile Application
Description: A working iOS application that enables users to create accounts, sign in securely, and manage player profiles. The application will provide drill instructions and tutorials, guide users through camera placement and setup validation, and support video recording and upload. Users will be able to view court-coverage assessments and partner recommendations based on their profiles and analyzed drill performance.
Requirements Satisfied: FR-01–FR-05, FR-12, NFR-02, NFR-07.
D-02: Backend and Processing Infrastructure
Description: A deployed backend that provides application APIs, private storage for videos and player information, a video-processing queue, analysis workers, and persistent session records. The infrastructure will support authenticated uploads, processing-status updates, recovery from interrupted or failed processing, and access controls that restrict player data and recordings to authorized users.
Requirements Satisfied: FR-06, FR-07, NFR-01, NFR-03, NFR-04.
D-03: Video Analysis and Court-Coverage Pipeline
Description: An integrated video-analysis pipeline that maps player movement into court coordinates, classifies drill attempts, and excludes unusable or uncertain observations from scored results. The pipeline will generate versioned court-coverage profiles containing performance measurements, confidence information, usable sample counts, and references to supporting video footage.
Requirements Satisfied: FR-08–FR-12, FR-15, NFR-05, NFR-06.
D-04: Partner-Matching Module
Description: A configurable partner-matching module, integrated with the mobile application, that filters eligible players and ranks potential partners using complementary court coverage and relevant profile attributes. Each recommendation will include an explanation of the measurements and compatibility factors contributing to its ranking. Recommendations will reflect updated assessment profiles as new drill results become available.
Requirements Satisfied: FR-13–FR-15, NFR-07.
D-05: Evaluation and Reproducibility Package
Description: A complete project package containing source code, environment and setup instructions, recordings approved for evaluation use, annotations, automated tests, and a requirements-to-test traceability matrix. A final evaluation report will document test methods, results, unmet targets, and known limitations. The report will compare coverage-based partner matching against a baseline using location and skill level, evaluating whether the proposed approach provides measurable benefits without assuming improved match outcomes.
Requirements Satisfied: Verification evidence for FR-01–FR-15 and NFR-01–NFR-08; implementation of NFR-08.

5. Standards
The team will use the following standards and guidance to structure development and evaluation. Compliance will be documented through project evidence; this plan does not claim formal certification.
5.1 ISO/IEC/IEEE 29148:2018 — Requirements Engineering
URL: https://www.iso.org/standard/72089.html
Applicability: This standard addresses requirements engineering and the information produced throughout that process. It applies to defining and maintaining the project’s scope, software requirements, and verification records [1].
Impact on Design and Code: Each requirement will have a unique identifier, rationale, verification method, and connection to a system capability. The team will use EARS syntax as its chosen writing method. EARS is not being presented as a requirement of this standard.
Compliance Plan: Review requirements for clarity, consistency, feasibility, and testability before each major milestone. Maintain traceability from requirements to implementation work and acceptance evidence.
5.2 ISO/IEC 25010:2023 — Product Quality Model
URL: https://www.iso.org/standard/78176.html
Applicability: This standard provides a model for specifying and evaluating software product quality. It applies to the project’s performance, reliability, security, interaction, and maintainability objectives [2].
Impact on Design and Code: Quality objectives will influence background processing, retry handling, access controls, understandable feedback, and separation of analysis from matching logic. The team will express selected objectives as measurable non-functional requirements.
Compliance Plan: Map relevant quality characteristics to the project’s tests and review the results at integration milestones. Record unmet targets and planned corrective actions. Corrective actions will be assessed after completion to confirm that they have addressed the deficiency.
5.3 NIST SP 800-218 — Secure Software Development Framework, Version 1.1
URL: https://csrc.nist.gov/pubs/sp/800/218/final
Applicability: This national guidance recommends secure development practices that can be incorporated into a software development lifecycle. It guides how the application manages user accounts, uploaded videos, and cloud resources [3].
Impact on Design and Code: The team will use managed authentication, private storage, server-side authorization, protected secrets, and dependency checks. Security-sensitive behavior will be tested alongside normal functionality, and peer review will be used to ensure sufficient security measures are taken.
Compliance Plan: Maintain a checklist of applicable practices and supporting evidence, including authorization tests and review records. Track and resolve identified vulnerabilities and release-blocking issues before demonstrations involving participant data.
6. References
[1] ISO, IEC, and IEEE, Systems and software engineering—Life cycle processes—Requirements engineering, ISO/IEC/IEEE 29148:2018, 2018. [Online]. Available: https://www.iso.org/standard/72089.html. [Accessed: Oct. 8, 2026].
[2] ISO and IEC, Systems and software engineering—Systems and software Quality Requirements and Evaluation (SQuaRE)—Product quality model, ISO/IEC 25010:2023, 2023. [Online]. Available: https://www.iso.org/standard/78176.html. [Accessed: Oct. 8, 2026].
[3] M. Souppaya, K. Scarfone, and D. Dodson, Secure Software Development Framework (SSDF) Version 1.1: Recommendations for Mitigating the Risk of Software Vulnerabilities, NIST SP 800-218, Feb. 2022. doi: 10.6028/NIST.SP.800-218. [Online]. Available: https://csrc.nist.gov/pubs/sp/800/218/final. [Accessed: Oct. 8, 2026].
[4] A. Mavin, “EARS: Easy Approach to Requirements Syntax.” [Online]. Available: https://alistairmavin.com/ears/. [Accessed: Oct. 8, 2026].
7. GenAI Statement
We used ChatGPT to draft our project discussions, suggest measurable acceptance criteria, and identify relevant standards. 


## Feedback:
# Software Development Plan Feedback

SYS-02: Would it be helpful to consider the guided video recording to be time limited? One of the challenges that I find in general is that there is a lot of variability that is getting introduced, depending on the way how recording is being done and how the player movements, etc., are happening. This is not good when your system is trying to use an AI solution with no human having to analyze and provide feedback. Thus, I would suggest you look at opportunities where the variability can be reduced so that it becomes more feasible for the ML models to analyze and provide insightful results.

For items "Under evaluation", I suggest you make it concrete as to what data will suggest and by when you will make the decision if something can be as a part of scope or not.

A-05: In practice, how will this assumption be justified. How will the system be able to identify if a recorded instance is valid or in-valid. Granted even if a human sees a recording and gives their opinion, how can you assess if that can be handled by the ML model as a valid input?

A-06: In my opinion, this is a very strong assumption. The feasibility of the project depends on this assumption. I'll suggest doing some first principle analysis to figure out whether this is an assumption or grounded in reality.

MoSCow 0/15 No submission

Requirements (Functional Requirements) 26/30

The explanation for FR-11 is not clear. I'll suggest using some generative tools to get feedback on why the wording is difficult to follow along and try to improve the readability. I'll suggest the same for FR-15

FR-14: The test method is not having clarity. I'll suggest expanding on the details, as in how will thew hand calculations be carried out, how will that be compared to the results provided by the algorithm etc.,

A general feedback is that the team needs to identify use cases for which the ground truth is known. For instances, the team needs to know certain configuration of pairs that are obviously bad and some that are good. Then they need to use their platform to see if the software solution also agrees with the ground truth or not.

Requirements (Project Coverage / Completeness) 5/5

Requirements (Non-Functional Requirements) 13/15

In my opinion NFR-05 and NFR-06 should be functional requirements. I say so, because without these in place, the functionality of the app's method is not guaranteed.

NFR-01: I'll suggest the team to look into other published applications on the website that have a similar flavor to this project and learn what are the representative analysis turn around times. Currently the quoted number of 60 seconds, appears as a generic guess which is not substantiate by any data.

For the NFR's, I'll suggest the team specifies what particular hardware and software (OS version) will be used for conducting the evaluations.
