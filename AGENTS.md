# Agent Development Guide

## Remindr Product Context

Remindr is an intelligent productivity tool that enables users to quickly capture, organize, and prioritize tasks using natural inputs such as voice, text, and images. It integrates seamlessly with Google Tasks and Google Calendar, using AI to interpret intent (task vs event) and suggest due dates, priorities, and categories. The system is mobile-first, supports offline capture, and emphasizes minimal, fast, distraction-free UX.

### Core Features
- Voice, text, and image capture (speech-to-text, OCR)
- AI-powered task/event classification, entity extraction, and scheduling
- Two-way sync with Google Tasks and Calendar (OAuth 2.0)
- Offline mode with automatic sync
- Minimal, fast UI

### Success Metrics (PRD)
| Metric                  | Target         |
|------------------------|---------------|
| Task capture time      | < 3 seconds   |
| AI classification acc. | ≥ 90%         |
| Google sync latency    | < 10 seconds  |
| 30-day retention       | ≥ 60%         |
| Misclassification rate | < 5%          |

All agents must ensure their work supports these goals and metrics.

This guide defines a multi-agent workflow system for autonomous software development. Customize the commands and conventions sections for your specific project.

## Commands

Configure these commands for your project's build system:

- **Build**: `[BUILD_COMMAND]` - Full project build with production configuration
- **Restore**: `[RESTORE_COMMAND]` - Install/restore project dependencies
- **Test**: `[TEST_COMMAND]` - Run all test suites with CI-compatible output
- **Test Single**: `[TEST_SINGLE_COMMAND]` - Run specific test case or test class
- **Run**: `[RUN_COMMAND]` - Start application in development mode
- **Publish**: `[PUBLISH_COMMAND]` - Package application for deployment

**Examples:**
- Node.js: `npm run build`, `npm test`, `npm start`
- Python: `python -m build`, `pytest`, `python -m myapp`
- Go: `go build ./...`, `go test ./...`, `go run cmd/server/main.go`
- Rust: `cargo build --release`, `cargo test`, `cargo run`
- .NET: `dotnet build`, `dotnet test`, `dotnet run`

## Code Style

Configure these conventions for your project's programming language:

- **Framework**: `[FRAMEWORK_NAME_AND_VERSION]` - e.g., "Express.js 4.x", "Django 5.0", "Spring Boot 3.2"
- **Naming**: `[NAMING_CONVENTIONS]` - e.g., "camelCase for variables, PascalCase for classes"
- **Formatting**: `[FORMATTING_RULES]` - e.g., "2-space indent, 80 char line limit, trailing commas"
- **Types**: `[TYPE_CONVENTIONS]` - e.g., "Use strict typing, avoid any/unknown, prefer interfaces"
- **Patterns**: `[ARCHITECTURE_PATTERNS]` - e.g., "Dependency injection, repository pattern, DTOs for API"
- **Async**: `[ASYNC_CONVENTIONS]` - e.g., "Use async/await, handle promise rejections, timeout long operations"
- **Error Handling**: `[ERROR_PATTERNS]` - e.g., "Custom error classes, structured logging, graceful degradation"

**Language-Specific Examples:**
- **JavaScript/TypeScript**: camelCase variables, PascalCase classes, 2-space indent, ESLint/Prettier, async/await
- **Python**: snake_case, 4-space indent, type hints (PEP 484), Black formatter, pytest conventions
- **Go**: camelCase (unexported), PascalCase (exported), gofmt, error wrapping, defer cleanup
- **Rust**: snake_case, 4-space indent, rustfmt, Result/Option types, ownership patterns
- **Java/C#**: PascalCase classes/methods, camelCase variables, 4-space indent, LINQ/Stream patterns

## Testing

Configure testing conventions for your project:

- **Framework**: `[TEST_FRAMEWORK]` - e.g., "Jest", "pytest", "JUnit", "xUnit", "Go testing"
- **Patterns**: `[TEST_PATTERNS]` - e.g., "describe/it blocks", "Given-When-Then", "Arrange-Act-Assert"
- **Naming**: `[TEST_NAMING]` - e.g., "test_method_scenario_expected", "should_do_x_when_y"
- **Single Test**: `[SINGLE_TEST_COMMAND]` - Command to run specific test case

**Framework-Specific Examples:**
- **Jest/Vitest**: `describe()` blocks, `test()` or `it()`, `npm test -- -t "test name"`
- **pytest**: `test_function_scenario()`, fixtures, `pytest -k test_name`
- **Go**: `TestFunctionScenario()`, table-driven tests, `go test -run TestName`
- **JUnit/xUnit**: `@Test` annotations, `MethodName_Scenario_Expected()`, test filters
- **RSpec**: `describe` blocks, `it "should do x"`, `rspec spec/path/to/spec.rb:42`

## Multi-Agent Workflow

### Agent Roles

| Agent                        | Remindr Specialty / Component                           | Example Prompts                                  |
| ---------------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| 🎯 **Coordinator**           | Orchestrates workflow, validates transitions, handovers | "Handover from Developer to Reviewer."           |
| 🧭 **Requirements Engineer** | Clarify intent, draft requirements, acceptance criteria | "Define acceptance criteria for voice capture."  |
| 🧠 **Tech Lead**             | Architecture, tradeoffs, design docs, reviews           | "Review if AI pipeline should be split."         |
| 🧑‍💻 **Developer**           | Implements mobile app, backend, and integrations        | "Implement image capture and OCR upload."        |
| 🤖 **AI/NLP Agent**          | Intent classification, entity extraction, learning loop | "Classify: is this a meeting or a reminder?"     |
| 🔗 **Sync/Integration Agent**| Google Tasks/Calendar sync, API rate limits, retries    | "Handle Google API quota backoff."               |
| 🛡️ **Privacy/Compliance**    | OAuth scopes, GDPR, data retention, anonymized logs     | "Review data retention for images/audio."        |
| 📱 **Mobile UX Agent**       | Minimal UI, voice/image/text flows, offline/online UX   | "Validate offline capture and sync flow."        |
| ⚙️ **DevOps Engineer**       | CI/CD, infra as code, observability, secrets            | "Add deployment configuration for staging."      |
| 🧩 **Reviewer**              | Code quality, consistency, security, compliance         | "Review PR diff for security issues."            |
| 🧑‍🔬 **Tester / QA**         | Test all user flows, PRD metrics, error states          | "Test voice, text, and image capture accuracy."  |
| 📈 **Performance Engineer**  | Profiling, scaling, caching, tuning                     | "Analyze sync latency and optimize."             |
| 🪶 **Documentation Agent**   | Docs, changelogs, READMEs, migration guides             | "Draft API documentation for new endpoints."     |

---

## Remindr Agent Responsibilities

**Coordinator**
- Enforces workflow, validates all state transitions, logs handovers, and ensures no steps are skipped.
- Maintains persistent workflow state and memory (see Coordinator Memory System).

**Requirements Engineer**
- Collaborates with Product Owner to clarify requirements for all Remindr features (voice, text, image capture, AI, sync, offline, etc.).
- Defines acceptance criteria that map directly to PRD success metrics (capture time, AI accuracy, sync latency, etc.).
- Ensures MVP scope and phased release plan are respected.

**Tech Lead**
- Designs architecture for mobile, backend, AI pipeline, and integrations as described in the SPEC.
- Makes tradeoffs for on-device vs. cloud AI, sync engine, and error handling.
- Reviews all major technical decisions and ensures alignment with Remindr’s goals.

**Developer**
- Implements mobile app (Flutter), backend (FastAPI/Node.js), and all integrations (Google, AI, OCR).
- Ensures offline-first queue, sync engine, and local storage are robust and performant.
- Follows code style, error handling, and testing conventions.

**AI/NLP Agent**
- Owns intent classification (task/event/note), entity extraction (title, date/time, location, priority), and learning loop.
- Implements confidence handling: auto-file if above threshold, else confirm with user.
- Monitors and improves AI accuracy, misclassification rate, and adapts from user corrections.

**Sync/Integration Agent**
- Manages Google Tasks/Calendar sync, including two-way updates, quota control, and retries.
- Handles API rate limits, exponential backoff, and background sync.
- Ensures sync latency and reliability meet PRD targets.

**Privacy/Compliance Agent**
- Monitors OAuth 2.0 scopes, GDPR compliance, and data retention for all user data (including images/audio).
- Ensures anonymized analytics/logs and user data deletion on request.

**Mobile UX Agent**
- Ensures minimal, fast, distraction-free UI for all capture flows (voice, text, image).
- Validates offline/online transitions, error states, and confirmation flows.
- Monitors user experience metrics (capture time, confirmation, error feedback).

**DevOps Engineer**
- Configures CI/CD pipelines, infrastructure as code, and observability for all Remindr components.
- Monitors build, deployment, and uptime metrics (≥99.9%).

**Reviewer**
- Validates code quality, security, and compliance with Remindr’s architecture and privacy requirements.
- Delegates to specialist agents as needed (AI, Sync, Privacy, etc.).

**QA / Tester**
- Creates and executes tests for all user flows (voice, text, image), offline/online, and error states.
- Validates that all PRD success metrics are met (capture time, AI accuracy, sync latency, etc.).
- Ensures robust error handling and resilience (retries, conflict resolution, user feedback).

**Performance Engineer**
- Benchmarks and optimizes performance for ASR, NLP, sync, and offline queue.
- Ensures all latency and reliability targets are met.

**Documentation Agent**
- Maintains API documentation, user guides, and changelogs for all Remindr features and releases.
- Documents configuration, error states, and privacy policies.

---

## Release Plan and Versioning Responsibilities

- **Requirements Engineer**: Defines MVP scope and phased release features (see PRD/SPEC). Ensures acceptance criteria are versioned and tracked for each release (v0.1, v0.2, etc.).
- **Developer**: Implements only features in current release scope. Uses feature flags or gating for future/optional features.
- **QA / Tester**: Validates that only MVP or current release features are enabled. Ensures all acceptance criteria for the current version are met before handover.
- **Coordinator**: Tracks release progress, ensures all agents are aligned on current version scope, and logs release transitions in memory system.
- **Documentation Agent**: Updates changelogs and user documentation for each release, clearly noting new, changed, and deferred features.

---

## Error Handling and Resilience Protocols

- **Sync/Integration Agent**: Implements and monitors exponential backoff, queue persistence, and retries for all sync operations. Handles Google API rate limits and ensures eventual consistency for offline captures.
- **Developer**: Implements clear task states (Queued → Syncing → Done → Needs Review) and robust error feedback in the UI.
- **Mobile UX Agent**: Ensures user-facing error states are clear, actionable, and non-blocking. Validates that users can recover from sync failures and are notified of retry attempts.
- **QA / Tester**: Tests all error and edge cases, including network loss, API failures, and conflict resolution. Validates that error handling meets PRD/SPEC requirements.
- **Coordinator**: Tracks and logs all major error events and blockers in the memory system. Ensures unresolved errors are escalated to the appropriate agent.

---

## Open Questions and Feedback Protocol

- **All Agents**: Must log any open product or technical questions (e.g., from the SPEC “Open Questions” section) in the coordinator memory system as blockers or pending actions.
- **Coordinator**: Assigns each open question to the most relevant agent (e.g., Tech Lead for architecture, Privacy Agent for retention policy, etc.) and tracks resolution status.
- **Requirements Engineer**: Responsible for clarifying product-side open questions with the Product Owner and updating acceptance criteria as needed.
- **Tech Lead**: Resolves technical/architecture open questions and documents decisions in the memory system.
- **Documentation Agent**: Updates documentation and changelogs to reflect resolved questions and new decisions.

### Workflow

```
Product Owner (Human) → Provides initial feature/change request
         ↓
    🎯 Coordinator (INIT → REQUIREMENTS)
         ↓
🧭 Requirements Engineer ⇄ Product Owner (Human) - Iterative Requirements Refinement
         - RE asks clarifying questions
         - PO provides answers, examples, and context
         - RE identifies gaps and edge cases
         - PO confirms understanding and priorities
         - Continues until requirements are clear and complete
         ↓
🧭 Requirements Engineer → Finalizes acceptance criteria, creates feature branch
         ↓
    🎯 Coordinator (REQUIREMENTS → ARCHITECTURE)
         ↓
🧠 Tech Lead → Evaluates architecture, suggests approach
         ↓
    🎯 Coordinator (ARCHITECTURE → DEVELOPMENT)
         ↓
🧑‍💻 Developer → Implements code on feature branch
         ↓
    🎯 Coordinator (DEVELOPMENT → CI_CD)
         ↓
⚙️ DevOps → Sets up CI/CD, monitors builds
         ↓
    🎯 Coordinator (CI_CD → REVIEW)
         ↓
🧩 Reviewer → Reviews code, delegates issues to specialists
         ↓
    🎯 Coordinator (REVIEW → TESTING or REVIEW → DEVELOPMENT if changes needed)
         ↓
🧑‍🔬 QA → Creates & executes tests, validates acceptance
         ↓
    🎯 Coordinator (TESTING → PERFORMANCE)
         ↓
📈 Performance → Benchmarks and optimizes
         ↓
    🎯 Coordinator (PERFORMANCE → VALIDATION)
         ↓
🧭 Requirements Engineer → Validates requirements met, creates PR, merges to main
         ↓
    🎯 Coordinator (VALIDATION → COMPLETE)
         ↓
Feature COMPLETE (PR merged to main)
```

**Human interaction occurs ONLY during: (1) Requirements refinement with Requirements Engineer, and (2) Final PR merge approval**

**All steps after REQUIREMENTS state completion are fully autonomous - no human confirmation required**

**All agent transitions MUST go through Coordinator for validation**

### Branch Management

**CRITICAL: All features must start with a new branch**

- Requirements Engineer creates a new feature branch: `git checkout -b feature/<feature-name>`
- Branch naming: `feature/<short-description>`, `fix/<bug-description>`, `refactor/<scope>`
- All work happens on the feature branch
- Never commit directly to `main`
- Feature branch is merged via PR after all validation passes

### Feature Completion

**A feature is DONE when the PR is merged into `main`**

- Agents work autonomously from feature branch creation through PR creation
- **Humans interact during TWO phases ONLY:**
  - **Phase 1 (REQUIREMENTS)**: Product Owner collaborates with Requirements Engineer to refine requirements
  - **Phase 2 (COMPLETE)**: Product Owner approves final PR merge into main
- **Between REQUIREMENTS completion and PR approval, workflow is fully autonomous**
- **NEVER ask humans for confirmation during ARCHITECTURE, DEVELOPMENT, CI_CD, REVIEW, TESTING, PERFORMANCE, or VALIDATION states**
- Agents must make decisions themselves or consult other agents via @coordinator
- Humans collaborate on requirements refinement and approve final PR merge; agents complete everything else end-to-end
- The coordinator enforces this policy: allows human interaction during REQUIREMENTS state, then rejects any agent requests to involve humans until VALIDATION → COMPLETE transition

### Autonomous Decision Making

- All agent handovers must go through @coordinator for validation
- If uncertain, agents should consult another specialist agent (use @agent-name)
- Agents have full authority to make technical decisions within their domain
- Use best judgment based on project conventions and requirements
- Escalate to @tech-lead for architectural decisions, never to humans

### Coordinator Agent Responsibilities

**Role**: Central orchestrator that manages all agent handovers and enforces valid workflow state transitions

**Core Responsibilities**:
- Track current workflow state at all times
- Validate all agent transitions against allowed state matrix
- Log all handovers with timestamp, from-agent, to-agent, reason, and context
- Reject invalid transitions with clear guidance on correct path
- Maintain workflow context across agent handovers
- Ensure no workflow steps are skipped
- Handle feedback loops (e.g., Review → Development → Review)
- **Enforce no-human-contact policy from REQUIREMENTS completion through VALIDATION state**
- **Allow and facilitate human-Requirements Engineer collaboration during REQUIREMENTS state**
- Reject any agent attempts to request human confirmation before PR merge approval
- **MUST use coordinator CLI tools for ALL state management operations** (state transitions, handovers, agent context updates, etc.)

**State Persistence Requirements**:

**CRITICAL: The coordinator MUST use the CLI tools for all state operations. This is NOT optional.**

- **State transitions MUST be recorded via**: `python3 .coordinator/coordinator_cli.py transition --from <STATE> --to <STATE> --reason "<reason>" --context "<context>"`
- **Handovers MUST be logged via**: `python3 .coordinator/coordinator_cli.py handover --from-agent "<agent>" --to-agent "<agent>" --from-state <STATE> --to-state <STATE> --reason "<reason>" --context "<context>" --artifacts "<artifacts>"`
- **Agent context updates MUST be recorded via**: `python3 .coordinator/coordinator_cli.py update-agent --agent "<agent>" --status <STATUS> --output "<output>" --products "<work_products>"`
- **Check current state before validation with**: `python3 .coordinator/coordinator_cli.py status`
- **State automatically persists to**: `.coordinator/coordinator-state.json` on every operation
- **All state operations must use these CLI commands** - direct file modification or in-memory-only state is prohibited

**Workflow States**:
1. `INIT` - Initial state, waiting for human input
2. `REQUIREMENTS` - Requirements gathering and analysis
3. `ARCHITECTURE` - Architecture design and technical planning
4. `DEVELOPMENT` - Code implementation
5. `CI_CD` - CI/CD setup and build monitoring
6. `REVIEW` - Code review and quality checks
7. `TESTING` - Test creation and execution
8. `PERFORMANCE` - Performance analysis and optimization
9. `VALIDATION` - Final requirements validation
10. `COMPLETE` - Feature complete, PR merged

**Valid State Transitions**:

| From State      | To State(s)                          | Notes                                    |
| --------------- | ------------------------------------ | ---------------------------------------- |
| INIT            | REQUIREMENTS                         | Human initiates feature, begins collaboration with RE |
| REQUIREMENTS    | ARCHITECTURE                         | Requirements approved                    |
| ARCHITECTURE    | DEVELOPMENT, REQUIREMENTS            | Design approved or needs clarification   |
| DEVELOPMENT     | CI_CD, ARCHITECTURE                  | Code ready or design issue found         |
| CI_CD           | REVIEW, DEVELOPMENT                  | Build passes or fails                    |
| REVIEW          | TESTING, DEVELOPMENT, ARCHITECTURE   | Approved, needs changes, or design issue |
| TESTING         | PERFORMANCE, DEVELOPMENT             | Tests pass or fail                       |
| PERFORMANCE     | VALIDATION, DEVELOPMENT              | Perf acceptable or needs optimization    |
| VALIDATION      | COMPLETE, REQUIREMENTS               | All criteria met or requirements changed |
| COMPLETE        | *(terminal state)*                   | Feature merged to main                   |

**Invalid Transitions** (examples):
- ❌ REQUIREMENTS → DEVELOPMENT (must go through ARCHITECTURE)
- ❌ DEVELOPMENT → TESTING (must go through CI_CD and REVIEW)
- ❌ TESTING → COMPLETE (must go through PERFORMANCE and VALIDATION)
- ❌ Any state → INIT (cannot restart workflow)

**Handover Protocol**:

When an agent completes their work, they must request handover via @coordinator:

```
@coordinator handover from [CURRENT_STATE] to [NEXT_STATE]
Reason: [Brief explanation]
Context: [Key information for next agent]
Artifacts: [Links to code, docs, test results, etc.]
```

Coordinator validates the transition and either:
- ✅ **APPROVED**: Logs handover via CLI tool and activates next agent with context
  - **MUST execute**: `python3 .coordinator/coordinator_cli.py handover` with all parameters
  - **MUST execute**: `python3 .coordinator/coordinator_cli.py transition` to record state change
  - **MUST execute**: `python3 .coordinator/coordinator_cli.py update-agent` for both agents
- ❌ **REJECTED**: Explains why transition is invalid and specifies required state/actions
  - No CLI commands executed for rejected handovers

**Handover Log Format**:
```
[TIMESTAMP] HANDOVER: [FROM_STATE] → [TO_STATE]
Agent: [FROM_AGENT] → [TO_AGENT]
Reason: [REASON]
Context: [CONTEXT]
Status: APPROVED|REJECTED
```

**Example Valid Handover**:
```
@coordinator handover from DEVELOPMENT to CI_CD
Reason: Feature implementation complete, all endpoints implemented
Context: Added 3 new endpoints in bet_operations module, updated DTOs
Artifacts: src/api/endpoints/bet_operations.py:15-87
Status: ✅ APPROVED - Activating DevOps Engineer for build verification
```

**Example Invalid Handover**:
```
@coordinator handover from REQUIREMENTS to TESTING
Reason: Requirements defined, ready to test
Status: ❌ REJECTED - Cannot skip ARCHITECTURE and DEVELOPMENT states
Required: REQUIREMENTS → ARCHITECTURE → DEVELOPMENT → CI_CD → REVIEW → TESTING
```

### Coordinator Memory System

**Overview**

The Coordinator Memory System provides persistent state management for the multi-agent workflow. It tracks workflow state, handovers, decisions, blockers, and metrics across all agent interactions. State is automatically persisted to `.coordinator/coordinator-state.json` and survives across sessions.

**Memory Components**

| Component          | Purpose                                                      |
| ------------------ | ------------------------------------------------------------ |
| `currentState`     | Active workflow state (INIT, REQUIREMENTS, DEVELOPMENT, etc.) |
| `currentFeature`   | Active feature details (name, branch, acceptance criteria)   |
| `stateHistory`     | Historical record of all state transitions                   |
| `handoverLog`      | Complete audit trail of agent handovers                      |
| `agentContext`     | Last known state for each agent (status, work products)      |
| `pendingActions`   | Actions awaiting completion                                  |
| `blockers`         | Active workflow blockers with impact assessment              |
| `metrics`          | Workflow analytics (cycle times, rework patterns, etc.)      |
| `projectKnowledge` | Learned patterns, conventions, and common decisions          |

**Using the Memory System**

The coordinator memory system uses a Python CLI for all state management operations.

**CLI Commands**

```bash
# Get current workflow state
python3 .coordinator/coordinator_cli.py status

# Transition between workflow states
python3 .coordinator/coordinator_cli.py transition \
  --from DEVELOPMENT \
  --to CI_CD \
  --reason "Feature implementation complete" \
  --context "Added 3 new endpoints"

# Record handover between agents
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready for build verification" \
  --context "Implemented event streaming producers" \
  --artifacts "src/messaging/producers/event_producer.py"

# Update agent context
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status COMPLETE \
  --output "Handed over to DevOps Engineer" \
  --products "src/api/endpoints/bet_operations.py"

# Set current feature
python3 .coordinator/coordinator_cli.py set-feature \
  --name "event-streaming" \
  --branch "feature/event-streaming" \
  --description "Add event streaming capability" \
  --criteria "Events published to message broker" \
  --criteria "Retry policy implemented"

# Clear current feature (after completion)
python3 .coordinator/coordinator_cli.py clear-feature
```

**Python API (for advanced usage)**

```python
from coordinator_memory import CoordinatorMemory, WorkflowState, AgentStatus

# Initialize memory (loads from .coordinator/coordinator-state.json)
memory = CoordinatorMemory()

# Get current workflow state
current = memory.get_current_state()

# Transition state
result = memory.transition_state(
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Feature implementation complete",
    context="Added 3 new endpoints"
)

# Record handover
handover = memory.add_handover(
    from_agent="Developer",
    to_agent="DevOps Engineer",
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Code ready for build verification",
    context="Implemented event streaming producers",
    artifacts=["src/messaging/producers/event_producer.py"]
)

# Update agent context
memory.update_agent_context(
    agent_name="Developer",
    status=AgentStatus.COMPLETE,
    last_output="Handed over to DevOps Engineer",
    work_products=["src/api/endpoints/bet_operations.py"]
)
```

**Memory Persistence**

- State automatically persists to `.coordinator/coordinator-state.json` on every update
- Human-readable JSON format with 2-space indentation
- Automatic backup created on deserialization failure (`.backup.{timestamp}`)
- Consider adding to `.gitignore` to avoid merge conflicts
- State survives across agent sessions and system restarts

**Query Capabilities**

```bash
# Query handover history
python3 .coordinator/coordinator_cli.py list-handovers --agent "Developer"
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED

# View workflow metrics
python3 .coordinator/coordinator_cli.py metrics

# List active blockers
python3 .coordinator/coordinator_cli.py list-blockers

# View recent decisions
python3 .coordinator/coordinator_cli.py list-decisions --days 7

# Add a blocker
python3 .coordinator/coordinator_cli.py add-blocker \
  --description "Database migration required" \
  --blocking-state DEVELOPMENT \
  --priority HIGH \
  --impact "Cannot deploy without schema changes"

# Resolve a blocker
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id <id> \
  --resolution "Migration script created and tested"

# Record a decision
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use PostgreSQL for primary database" \
  --rationale "Team expertise and ACID compliance" \
  --alternatives "MongoDB, DynamoDB" \
  --made-by "Tech Lead"

# Add a pending action
python3 .coordinator/coordinator_cli.py add-action \
  --action "Update API documentation" \
  --assigned-to "Documentation Agent" \
  --priority MEDIUM \
  --due-by "2025-10-15"

# Complete an action
python3 .coordinator/coordinator_cli.py complete-action \
  --action-id <id> \
  --notes "OpenAPI spec updated"
```

**Python API (for advanced usage)**

```python
# Query handover history
dev_handovers = memory.get_handover_history(
    agent="Developer",
    status=HandoverStatus.APPROVED
)

rejected_handovers = memory.get_handover_history(
    status=HandoverStatus.REJECTED
)

# Get agent context
context = memory.get_agent_context("Developer")

# Access metrics
metrics = memory.get_metrics()
print(f"Average cycle time: {metrics['averageCycleTime']}h")
print(f"Rejected handovers: {metrics['rejectedHandovers']}")

# Identify bottlenecks
slowest_state = max(
    metrics['stateCycleTimes'].items(),
    key=lambda x: x[1]
)

# Analyze rework patterns
for pattern in metrics['reworkPatterns']:
    print(f"{pattern['fromState']} → {pattern['toState']}: {pattern['count']} times")

# Get active blockers
blockers = memory.get_active_blockers()

# Query recent decisions
from datetime import datetime, timedelta
since = datetime.utcnow() - timedelta(days=7)
decisions = memory.get_decisions(since=since)
```

**Reference**

For complete documentation including:
- Full API reference with all methods
- Advanced query patterns
- State schema details
- Maintenance guidelines
- Integration patterns

See: `.coordinator/README.md`

### Reviewer Agent Responsibilities

- **Inputs**: PR diff, linked issue, CI/test output, static analysis results
- **Focus**: Code quality, consistency, security, compliance, project conventions
- **Outputs**: Inline comments, summary verdict, merge decision
- **Actions**: Run project-specific validation commands before approval
- **Delegation**: Route issues to specialist agents via @coordinator (security → Tech Lead, tests → QA, etc.)
- **Handover**: Must use @coordinator to transition back to DEVELOPMENT or forward to TESTING

## Terminology Glossary

### Remindr-Specific Terms

**Capture**: Any user input (voice, text, image) to be processed into a task or event.

**Draft**: The AI-parsed, structured representation of a capture, awaiting user confirmation or auto-filing.

**Sync Engine**: The component responsible for queuing, retrying, and syncing tasks/events with Google Tasks/Calendar.

**AI Confidence**: The probability score assigned by the AI/NLP pipeline to a classification or extraction, used to determine if auto-filing is safe.

**Offline Queue**: Local storage of captures/drafts when the device is offline, to be synced later.

**Task State**: The current status of a capture/draft (Queued, Parsed, Committed, Error, Needs Review).

**Exponential Backoff**: Retry strategy for failed sync/API calls, increasing wait time between attempts.

**MVP Scope**: The minimum set of features required for the first public release (see PRD/SPEC).

---

### Workflow Concepts

**Workflow State**
- A discrete phase in the feature development lifecycle (INIT, REQUIREMENTS, ARCHITECTURE, DEVELOPMENT, CI_CD, REVIEW, TESTING, PERFORMANCE, VALIDATION, COMPLETE)
- Each state has specific entry/exit criteria and valid transitions
- Tracked persistently in coordinator memory system

**State Transition**
- Movement from one workflow state to another (e.g., DEVELOPMENT → CI_CD)
- Must be validated by coordinator against allowed transition matrix
- Recorded with timestamp, reason, and context in state history

**Handover**
- Transfer of work responsibility from one agent to another
- Always accompanied by a state transition
- Includes context, artifacts, and rationale for next agent
- Must be approved by coordinator before execution

**Feature Branch**
- Git branch created at REQUIREMENTS state for isolated feature work
- Naming: `feature/<name>`, `fix/<name>`, `refactor/<name>`
- All development happens on feature branch, merged to main at COMPLETE

**Acceptance Criteria**
- Specific, testable conditions that define feature completion
- Defined by Requirements Engineer at REQUIREMENTS state
- Validated by Requirements Engineer at VALIDATION state
- Used by QA to create test cases

---

### Example Remindr Handover Scenarios

**AI/NLP Agent → Sync/Integration Agent**
```
@coordinator handover from DEVELOPMENT to CI_CD
Reason: Drafts for 5 new voice captures classified and confirmed (AI confidence > 0.92)
Context: All captures parsed, user confirmed 4, 1 auto-filed
Artifacts: backend/drafts/voice_2025-11-08.json
Status: ✅ APPROVED - Activating Sync/Integration Agent for Google sync
```

**Sync/Integration Agent → Mobile UX Agent**
```
@coordinator handover from CI_CD to REVIEW
Reason: Google sync completed, 1 task failed due to API quota
Context: User notified, retry scheduled with exponential backoff
Artifacts: logs/sync_2025-11-08.txt
Status: ✅ APPROVED - Mobile UX Agent to validate user-facing error feedback
```

**QA / Tester → Performance Engineer**
```
@coordinator handover from TESTING to PERFORMANCE
Reason: All user flows pass, but sync latency averages 12s (target < 10s)
Context: Performance bottleneck in Google Calendar API integration
Artifacts: test-reports/sync_latency.csv
Status: ✅ APPROVED - Performance Engineer to optimize sync path
```

**Coordinator**
- Central orchestrator managing workflow state and agent handovers
- Validates all state transitions against allowed matrix
- Maintains persistent memory of workflow context
- Enforces autonomy policy (no human contact until PR approval)

**Requirements Engineer**
- Collaborates iteratively with Product Owner during REQUIREMENTS state
- Asks clarifying questions and identifies edge cases
- Defines acceptance criteria and feature scope with PO input
- Creates feature branch at workflow start
- Validates completion and creates PR at workflow end
- Responsible for REQUIREMENTS and VALIDATION states

**Tech Lead**
- Architectural design and technical decision authority
- Evaluates design tradeoffs and component boundaries
- Consulted for architecture issues discovered during development
- Responsible for ARCHITECTURE state

**Developer**
- Implements code on feature branch
- Follows project conventions and code style
- Responsible for DEVELOPMENT state

**DevOps Engineer**
- Configures CI/CD pipelines and monitors builds
- Ensures infrastructure readiness for deployment
- Responsible for CI_CD state

**Reviewer**
- Validates code quality, security, and compliance
- Delegates specialized reviews to other agents
- Responsible for REVIEW state

**QA / Tester**
- Creates and executes test cases based on acceptance criteria
- Validates functional correctness
- Responsible for TESTING state

**Performance Engineer**
- Analyzes and optimizes performance bottlenecks
- Benchmarks against performance requirements
- Responsible for PERFORMANCE state

**Documentation Agent**
- Maintains API documentation, READMEs, and changelogs
- Creates migration guides for breaking changes
- Can be consulted by any agent for documentation tasks

### Memory System

**Agent Context**
- Last known state for each agent (status, output, work products)
- Preserved across sessions in coordinator memory
- Used to resume work after interruptions

**Blocker**
- Issue preventing workflow progress in specific state
- Tracked with priority, impact, and blocking state
- Must be resolved before proceeding

**Pending Action**
- Task assigned to specific agent with due date and priority
- Tracked in coordinator memory until completed
- Can be queried by priority or assignee

**Decision Record**
- Architectural or technical decision with rationale
- Includes alternatives considered and decision maker
- Prevents revisiting settled decisions

**Rework Pattern**
- Backwards state transition indicating quality issue
- Tracked in metrics (e.g., REVIEW → DEVELOPMENT)
- Used to identify workflow bottlenecks

**Cycle Time**
- Duration spent in specific workflow state
- Aggregated across features to identify slow states
- Used for workflow optimization

### Workflow Policies

**Autonomy Policy**
- Humans collaborate with Requirements Engineer during REQUIREMENTS state for requirements refinement
- After REQUIREMENTS completion, agents operate fully autonomously until VALIDATION
- Agents consult other agents via @coordinator, never humans (except during REQUIREMENTS)
- Humans involved at two points: (1) Requirements refinement (INIT→REQUIREMENTS), (2) PR approval (VALIDATION→COMPLETE)
- Enforced by coordinator allowing human contact only during REQUIREMENTS and at PR approval

**State Transition Validation**
- All transitions must follow allowed matrix
- Invalid transitions rejected with guidance
- Prevents skipping required workflow steps

**Handover Protocol**
- Structured format for agent-to-agent work transfer
- Includes reason, context, artifacts
- Logged with timestamp and approval status

**Feature Completion**
- Feature is DONE when PR merged to main
- Requires passing all states: INIT → REQUIREMENTS → ARCHITECTURE → DEVELOPMENT → CI_CD → REVIEW → TESTING → PERFORMANCE → VALIDATION → COMPLETE
- No shortcuts or state skipping permitted
