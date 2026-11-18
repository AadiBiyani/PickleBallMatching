# Team Development Process

This document defines the development process for Team #2's Personalized Doubles Partner Coordination project. The team will follow this process for all application, backend, machine-learning, and experimental work in the shared repository.

## 1. Repository Architecture

The project will use a monorepo so the mobile application, backend services, machine-learning code, experiments, tests, and documentation can evolve together. The intended top-level structure is:

```text
PickleBallMatching/
├── docs/                       # Project plans, requirements, and technical documentation
│   ├── DEVELOPMENT.md          # This development process
│   └── agent-decisions.md      # Running record of material human/agent design decisions
├── frontend/                   # Installed mobile application and frontend-specific tests
├── backend/                    # APIs, authentication, persistence, and processing services
├── models/                     # Versioned ML source code, training, evaluation, and inference
├── experiments/                # Time-bounded prototypes and feasibility investigations
├── tests/                      # Cross-component fixtures and end-to-end/integration tests
├── .github/
│   └── workflows/              # Continuous integration and repository automation
├── .gitignore                  # Generated, local, secret, and large-file exclusions
└── README.md                   # Project overview and setup instructions
```

Directories may be added as the design becomes concrete, but additions should preserve clear ownership and separation of concerns.

### Directory responsibilities

- **`docs/`** contains durable project documentation, including the project proposal, software development plan, architectural decisions, API documentation, and test or evaluation plans.
- **`frontend/`** contains the installed mobile application. UI code, camera guidance, recording and upload behavior, and frontend-specific tests belong here.
- **`backend/`** contains server-side APIs and services, including authentication integration, authorization, persistence, video upload coordination, background-job orchestration, and recommendation endpoints.
- **`models/`** contains reproducible source code for court, player, and ball analysis; model training and evaluation; and production inference. Model code and model artifacts must be distinguished clearly. Large generated weights and datasets must not be committed directly unless the team has intentionally configured suitable artifact storage such as Git LFS.
- **`experiments/`** contains prototypes used to answer a specific feasibility question. Each substantial experiment should document its objective, setup, dependencies, and conclusion. Code that becomes part of the product must be moved into the appropriate production directory rather than imported indefinitely from an experiment.
- **`tests/`** contains tests and fixtures that span multiple components. Tests owned by only one component should remain near that component when supported by its framework.
- **`.github/workflows/`** contains CI definitions so required checks are version-controlled and reviewable.

Source code, tests, configuration examples, and documentation will be committed. Secrets, virtual environments, dependency caches, build outputs, raw participant videos, generated analysis outputs, local environment files, and other reproducible artifacts will be excluded through `.gitignore`. Participant data must be handled according to the project's consent, access, and retention requirements.

### Structure and engineering references

The architecture is guided by the following standards and official documentation:

1. The [Python Packaging User Guide discussion of `src` and flat layouts](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) will guide the internal organization of Python packages in the backend and model components.
2. The [PyPA guide to packaging Python projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/) will guide package metadata, dependency declarations, and testable module organization where Python is used.
3. [The Twelve-Factor App](https://12factor.net/) will guide service configuration, dependency declaration, build/run separation, and disposable backend processes.
4. [NIST SP 800-218, Secure Software Development Framework 1.1](https://csrc.nist.gov/pubs/sp/800/218/final) will guide source protection, dependency management, review, automated checks, and handling of security-sensitive changes.
5. [GitHub's documentation on large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) will guide storage decisions for videos, datasets, generated outputs, and model weights.

These references provide general guidance; component-level conventions will also follow the official framework documentation selected during implementation.

## 2. Branching and Workflow Model

The team will use [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow): one protected `main` branch and short-lived development branches. All team members will create branches in the shared team repository. Team members must not fork the repository to create personal development repositories.

### Main branches

- **`main`** is the single shared integration and release branch. It must remain buildable and demonstrable. Direct pushes are prohibited; changes enter through reviewed pull requests with required CI checks.
- **Short-lived development branches** are created from the latest `main` for one focused feature, fix, documentation change, experiment, or maintenance task. They are deleted after merging.

The team will not maintain permanent `develop`, personal, or release branches. If a stabilization branch becomes necessary for a class milestone, the team must first document its purpose, owner, merge-back plan, and removal date in a pull request that updates this process.

### Branch naming convention

Branch names use the following format:

```text
<developer>/<type>/<issue-number>-<short-kebab-case-description>
```

Allowed types are:

- `feature` for new user-facing or system behavior
- `fix` for defect corrections
- `docs` for documentation-only work
- `test` for test-only work
- `experiment` for feasibility investigations
- `chore` for maintenance, tooling, or dependency work

Examples:

```text
nishaant/feature/42-camera-validation
liam/fix/57-upload-retry
aadi/experiment/63-ball-tracking
logan/docs/71-api-contract
```

When no issue exists, use `no-issue` in the issue-number position and explain why in the pull request. Branches must be narrowly scoped and normally live no longer than one week. Developers should synchronize with `main` before requesting final approval and resolve conflicts on their development branch.

### Standard workflow

1. Create or select an issue with clear scope and acceptance criteria.
2. Update local `main`, then create a correctly named branch in the team repository.
3. Make focused commits and add or update tests and documentation with the implementation.
4. Push the branch and open a draft pull request early when feedback or coordination would be useful.
5. Complete the pull request template, obtain CI results, and request review when the change is ready.
6. Address review comments and rerun relevant checks after substantive changes.
7. Obtain approval from at least one eligible reviewer and ensure all required checks pass.
8. Squash and merge into `main`, then delete the development branch.

## 3. Code Development and Review Policy

### Pull request requirements

Every change to `main`, including documentation, experiments intended for team use, configuration, and agent-written code, must use a pull request. A pull request must:

- address one coherent change and link its issue when one exists;
- describe the motivation, implementation, user or system impact, and testing performed;
- identify known risks, limitations, follow-up work, and any migration or configuration steps;
- include tests appropriate to the changed behavior or explain why tests are not applicable;
- update affected setup, API, architecture, or user documentation;
- avoid unrelated formatting or refactoring that makes review harder; and
- never include secrets, private participant data, raw recordings, generated outputs, or unapproved large artifacts.

Draft pull requests may be used for early collaboration but cannot be merged.

### Pull request titles and merge commits

Because pull requests are squash-merged and the title becomes the commit message on `main`, titles must follow this convention:

```text
feat: add camera placement validation
fix: #57 preserve recording after upload failure
docs: define backend setup
test: add recommendation ranking fixtures
experiment: evaluate player tracking accuracy
chore: update CI dependencies
```

`feat:` is used for new behavior and `fix:` for defects. Other listed prefixes are used when they more accurately describe the change. Fix titles must include the issue number when one exists. Titles should be concise, imperative, and specific.

### Review and approval

- At least **one approval** is required before merging.
- The pull request author cannot approve their own pull request or count as the required reviewer.
- The reviewer should understand the affected component. Security-, privacy-, data-retention-, model-scoring-, database-schema-, or public-API changes should be reviewed by a teammate familiar with that area; the team should request a second reviewer when the risk or scope warrants it.
- The author must respond to or resolve every review thread. The reviewer who raised a blocking concern should confirm that it has been addressed.
- Substantive changes after approval require the author to request review again. Repository settings should dismiss stale approvals when possible.
- Reviewers evaluate correctness, scope, readability, maintainability, tests, security and privacy impact, failure handling, and consistency with requirements—not only whether the code runs.

No one may merge while required feedback is unresolved, required checks are pending or failing, or the branch has unresolved conflicts.

### Continuous integration checks

For application-code changes, the required CI checks are:

- linting and formatting validation;
- unit tests;
- integration tests;
- component build or type checking, where applicable; and
- secret and dependency checks once those workflows are established.

CI should run on every pull request update. Checks may be scoped to affected components to keep feedback timely, but all checks designated as required by branch protection must pass before merging. A required check may not be bypassed merely because a reviewer believes the failure is unrelated.

Some informational or experimental checks may initially be non-required. If one of these checks fails, the pull request author must explain the failure, provide evidence that it does not affect the proposed change, and create or link follow-up work when appropriate. The approving reviewer must explicitly accept that explanation before merge. Repeated or product-relevant failures should be promoted to required checks or fixed rather than routinely ignored.

Hardware-dependent camera tests, performance benchmarks, and model evaluations that cannot run in standard CI must have a documented manual procedure. The pull request must record the environment and result when such a test is required by the change.

### Merge policy

- Pull requests are merged using **squash and merge** after approval and successful required checks.
- The final squash commit message must use the approved pull request title.
- Direct pushes and force pushes to `main` are prohibited.
- The author normally merges after verifying that approval and checks are current.
- Emergency changes follow the same pull request, review, and CI rules. If an unavailable external service makes a required check impossible to run, the team must reach explicit agreement, document the exception and evidence in the pull request, and run the check as soon as service returns.
- A regression found on `main` is corrected through a new `fix` branch and pull request. Reverting a change is preferred when it restores stability faster and more safely than an immediate forward fix.

### Development frequency and coordination

During active development, each team member is expected to open at least **one meaningful pull request per week**. Small, focused pull requests are preferred to large end-of-milestone changes. This is a coordination target rather than a reason to submit incomplete or artificial work.

Team members should open draft pull requests early for cross-component changes and communicate interface or schema changes before implementation is finalized. Pull requests should normally receive an initial review within two working days. Authors should avoid allowing branches to diverge from `main` for more than one week.

### Agent-assisted code

Code written or modified with an AI agent follows exactly the same branch, testing, pull request, review, approval, CI, and merge rules as human-written code. The human author remains accountable for understanding and validating the change.

For each pull request that contains material agent-assisted work:

- the pull request description must identify which portions were agent-assisted;
- the author must verify generated code, tests, dependencies, licenses, security implications, and claims rather than accepting them without review; and
- material design choices arising from the human/agent conversation must be summarized in the running `docs/agent-decisions.md` file. Each entry should include the date, related issue or pull request, decision, alternatives considered, rationale, and known consequences.

Minor uses such as spelling corrections or editor completion do not require a decision-log entry unless they affect design or behavior. Private data, credentials, participant recordings, and other restricted information must not be placed into unapproved agent prompts or services.

## 4. Process Maintenance

The team will review this process at the end of each major milestone or when repeated friction shows that a rule is ineffective. Process changes require a pull request, the same review and approval used for code, and agreement from the team members affected by the change. Changes should make the process safer or easier to follow without weakening review, traceability, or the stability of `main`.
