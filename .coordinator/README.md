# Coordinator Memory System

## Overview

The Coordinator Memory System provides persistent state management for the multi-agent workflow. It uses a **Python CLI** with **coordinator-only access** to ensure proper workflow orchestration and state consistency.

**Key Features:**
- ✅ Python CLI for all state operations (no .NET runtime required)
- ✅ Coordinator-only access control (agents request via @coordinator)
- ✅ File locking for concurrent access safety
- ✅ Automatic backups on corruption
- ✅ Comprehensive workflow metrics
- ✅ Project knowledge learning
- ✅ Decision audit trail

## Architecture

### Access Control Model

**IMPORTANT:** The coordinator memory system uses a **coordinator-only access model**:

```
Agents → @coordinator request → Coordinator validates → Python CLI executes → State updated
```

- **Agents MUST NOT** call the CLI directly
- **Agents MUST** request handovers via `@coordinator` 
- **Only the Coordinator** validates and executes state changes
- **State file** is the single source of truth

### Components

```
.coordinator/
├── coordinator_memory.py       # Core Python implementation (1,051 lines)
├── coordinator_cli.py          # CLI interface (464 lines)
├── coordinator-state.json      # Persistent state file
├── memory-schema.json          # JSON Schema definition
├── test_coordinator_memory.py  # Test suite (35 tests)
├── requirements.txt            # Python dependencies
└── [documentation files]
```

### State File

- **Location:** `.coordinator/coordinator-state.json`
- **Format:** JSON with camelCase properties (schema-compliant)
- **Locking:** Uses `fcntl` file locks for concurrent access
- **Backup:** Automatic `.backup.{timestamp}` on corruption
- **Version Control:** Consider `.gitignore` to avoid merge conflicts

## Getting Started

### Prerequisites

```bash
# Install Python dependencies
pip install -r .coordinator/requirements.txt
# or
pip install python-dateutil
```

### Verify Installation

```bash
# Check current state
python3 .coordinator/coordinator_cli.py status

# Run tests
python3 -m pytest .coordinator/test_coordinator_memory.py -v
```

### First Steps

```bash
# 1. Check workflow status
python3 .coordinator/coordinator_cli.py status

# 2. View metrics
python3 .coordinator/coordinator_cli.py metrics

# 3. List recent handovers
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-01
```

## CLI Commands

All commands output JSON for easy parsing and integration.

### Workflow State Commands

#### `status` - Show Current State

```bash
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming",
    "description": "Add event streaming",
    "startedAt": "2025-10-07T10:00:00Z",
    "acceptanceCriteria": [
      "Events published successfully",
      "Retry policy implemented"
    ]
  }
}
```

#### `transition` - Change Workflow State

```bash
python3 .coordinator/coordinator_cli.py transition \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Feature implementation complete" \
  --context "Added 3 new endpoints"
```

**Output (success):**
```json
{
  "success": true,
  "transition": {
    "fromState": "DEVELOPMENT",
    "toState": "CI_CD",
    "timestamp": "2025-10-07T14:30:00Z",
    "reason": "Feature implementation complete",
    "approved": true
  }
}
```

**Output (failure):**
```json
{
  "success": false,
  "error": "Invalid transition: DEVELOPMENT → TESTING. Required path: DEVELOPMENT → CI_CD → REVIEW → TESTING"
}
```

### Feature Management Commands

#### `set-feature` - Set Current Feature

```bash
python3 .coordinator/coordinator_cli.py set-feature \
  --name "event-streaming" \
  --branch "feature/event-streaming" \
  --description "Add event streaming" \
  --criteria "Events published successfully,Retry policy configured,Tests passing" \
  --issues "#123,#124"
```

**Output:**
```json
{
  "success": true,
  "feature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming",
    "description": "Add event streaming",
    "startedAt": "2025-10-07T10:00:00Z",
    "acceptanceCriteria": [
      "Events published successfully",
      "Retry policy configured",
      "Tests passing"
    ],
    "linkedIssues": ["#123", "#124"]
  }
}
```

#### `clear-feature` - Clear Current Feature

```bash
python3 .coordinator/coordinator_cli.py clear-feature
```

**Output:**
```json
{
  "success": true
}
```

### Handover Commands

#### `handover` - Record Agent Handover

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready for build verification" \
  --context "Implemented event producers" \
  --artifacts "src/messaging/producers/event_producer.py"
```

**Output (approved):**
```json
{
  "success": true,
  "handover": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "fromAgent": "Developer",
    "toAgent": "DevOps Engineer",
    "fromState": "DEVELOPMENT",
    "toState": "CI_CD",
    "status": "APPROVED",
    "timestamp": "2025-10-07T14:30:00Z"
  }
}
```

**Output (rejected):**
```json
{
  "success": false,
  "error": "Invalid transition: DEVELOPMENT → TESTING",
  "handover": {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "status": "REJECTED",
    "rejectionReason": "Cannot skip CI_CD and REVIEW states"
  }
}
```

#### `list-handovers` - Query Handover History

```bash
# All handovers
python3 .coordinator/coordinator_cli.py list-handovers

# Filter by agent
python3 .coordinator/coordinator_cli.py list-handovers --agent "Developer"

# Filter by status
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED

# Filter by date
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-01T00:00:00Z

# Combined filters
python3 .coordinator/coordinator_cli.py list-handovers \
  --agent "Developer" \
  --status APPROVED \
  --since 2025-10-07T00:00:00Z
```

**Output:**
```json
{
  "count": 2,
  "handovers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "fromAgent": "Developer",
      "toAgent": "DevOps Engineer",
      "fromState": "DEVELOPMENT",
      "toState": "CI_CD",
      "status": "APPROVED",
      "reason": "Code ready",
      "timestamp": "2025-10-07T14:30:00Z",
      "rejectionReason": null
    }
  ]
}
```

### Agent Context Commands

#### `update-agent` - Update Agent Status

```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Implementing event producer" \
  --work-products "src/messaging/producers/event_producer.py"
```

**Output:**
```json
{
  "success": true,
  "agent": "Developer",
  "context": {
    "status": "WORKING",
    "lastActive": "2025-10-07T14:30:00Z",
    "lastOutput": "Implementing event producer",
    "workProducts": [
      "src/messaging/producers/event_producer.py"
    ]
  }
}
```

**Agent Status Values:**
- `IDLE` - Agent available for work
- `WORKING` - Agent actively working
- `BLOCKED` - Agent blocked by dependency
- `COMPLETE` - Agent completed assigned work

### Blocker Management Commands

#### `add-blocker` - Create Blocker

```bash
python3 .coordinator/coordinator_cli.py add-blocker \
  --description "Message broker not available in test environment" \
  --impact HIGH \
  --affected-state TESTING \
  --affected-agent "Tester / QA"
```

**Output:**
```json
{
  "success": true,
  "blocker": {
    "id": "650e8400-e29b-41d4-a716-446655440000",
    "description": "Message broker not available",
    "impact": "HIGH",
    "affectedState": "TESTING",
    "affectedAgent": "Tester / QA",
    "status": "OPEN",
    "createdAt": "2025-10-07T14:30:00Z"
  }
}
```

**Priority Levels:** `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

#### `resolve-blocker` - Resolve Blocker

```bash
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id "650e8400-e29b-41d4-a716-446655440000" \
  --resolution "Configured test message broker instance on port 9093"
```

**Output:**
```json
{
  "success": true,
  "blockerId": "650e8400-e29b-41d4-a716-446655440000"
}
```

#### `list-blockers` - Show Active Blockers

```bash
python3 .coordinator/coordinator_cli.py list-blockers
```

**Output:**
```json
{
  "count": 1,
  "blockers": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440000",
      "description": "Message broker not available",
      "impact": "HIGH",
      "affectedState": "TESTING",
      "affectedAgent": "Tester / QA",
      "status": "OPEN",
      "createdAt": "2025-10-07T14:30:00Z"
    }
  ]
}
```

### Action Management Commands

#### `add-action` - Create Pending Action

```bash
python3 .coordinator/coordinator_cli.py add-action \
  --action "Add integration tests for event producer" \
  --owner "Tester / QA" \
  --priority HIGH \
  --due-by "2025-10-08T12:00:00Z"
```

**Output:**
```json
{
  "success": true,
  "action": {
    "id": "750e8400-e29b-41d4-a716-446655440000",
    "action": "Add integration tests",
    "owner": "Tester / QA",
    "priority": "HIGH",
    "status": "PENDING",
    "createdAt": "2025-10-07T14:30:00Z",
    "dueBy": "2025-10-08T12:00:00Z"
  }
}
```

#### `complete-action` - Complete Action

```bash
python3 .coordinator/coordinator_cli.py complete-action \
  --action-id "750e8400-e29b-41d4-a716-446655440000" \
  --outcome "Integration tests added and passing"
```

**Output:**
```json
{
  "success": true,
  "actionId": "750e8400-e29b-41d4-a716-446655440000"
}
```

### Decision Recording Commands

#### `record-decision` - Record Decision

```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use at-least-once delivery for message events" \
  --rationale "Balance between reliability and complexity" \
  --impact "Consumers must handle duplicate events" \
  --context '{"alternative":"exactly-once","tradeoff":"complexity vs reliability"}'
```

**Output:**
```json
{
  "success": true,
  "decision": {
    "id": "850e8400-e29b-41d4-a716-446655440000",
    "decision": "Use at-least-once delivery",
    "rationale": "Balance between reliability and complexity",
    "outcome": "Consumers must handle duplicate events",
    "timestamp": "2025-10-07T14:30:00Z"
  }
}
```

#### `list-decisions` - Query Decisions

```bash
# All decisions
python3 .coordinator/coordinator_cli.py list-decisions

# Since date
python3 .coordinator/coordinator_cli.py list-decisions --since 2025-10-01T00:00:00Z
```

**Output:**
```json
{
  "count": 3,
  "decisions": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440000",
      "decision": "Use at-least-once delivery",
      "rationale": "Balance between reliability and complexity",
      "outcome": "Consumers must handle duplicate events",
      "timestamp": "2025-10-07T14:30:00Z"
    }
  ]
}
```

### Metrics Commands

#### `metrics` - Show Workflow Metrics

```bash
python3 .coordinator/coordinator_cli.py metrics
```

**Output:**
```json
{
  "totalFeatures": 5,
  "totalHandovers": 47,
  "rejectedHandovers": 3,
  "averageCycleTime": 4.5,
  "stateCycleTimes": {
    "DEVELOPMENT": 2.3,
    "REVIEW": 0.5,
    "TESTING": 1.2
  },
  "reworkPatterns": [
    {
      "fromState": "REVIEW",
      "toState": "DEVELOPMENT",
      "count": 2,
      "reason": "Missing error handling"
    }
  ],
  "agentUtilization": {
    "Developer": 8.5,
    "Tester / QA": 3.2
  }
}
```

## Python API

For advanced programmatic usage, import the Python module directly:

### Basic Usage

```python
from coordinator_memory import CoordinatorMemory, WorkflowState

# Initialize (loads from .coordinator/coordinator-state.json)
memory = CoordinatorMemory()

# Get current state
current = memory.get_current_state()
print(f"Current state: {current.value}")

# Transition state
result = memory.transition_state(
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Feature implementation complete",
    context="Added 3 new endpoints"
)

if result.success:
    print(f"Transitioned at {result.transition.timestamp}")
else:
    print(f"Transition failed: {result.error_message}")
```

### Feature Management

```python
# Set current feature
memory.set_current_feature(
    name="event-streaming",
    branch="feature/event-streaming",
    description="Add event streaming",
    acceptance_criteria=["Events published successfully", "Retry policy configured"],
    linked_issues=["#123"]
)

# Get current feature
feature = memory.get_current_feature()
print(f"Working on: {feature.name}")

# Clear feature when complete
memory.clear_current_feature()
```

### Handover Management

```python
from coordinator_memory import HandoverStatus

# Record handover
result = memory.add_handover(
    from_agent="Developer",
    to_agent="DevOps Engineer",
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Code ready for build verification",
    context="Implemented event producers",
    artifacts=["src/messaging/producers/event_producer.py"]
)

if result.success:
    print(f"Handover approved: {result.handover.id}")
else:
    print(f"Handover rejected: {result.error_message}")

# Query handover history
handovers = memory.get_handover_history(
    agent="Developer",
    status=HandoverStatus.APPROVED
)

rejected = memory.get_handover_history(
    status=HandoverStatus.REJECTED
)
```

### Agent Context

```python
from coordinator_memory import AgentStatus

# Update agent context
memory.update_agent_context(
    agent_name="Developer",
    status=AgentStatus.WORKING,
    last_output="Implementing event producer",
    work_products=["src/messaging/producers/event_producer.py"]
)

# Get agent context
context = memory.get_agent_context("Developer")
if context:
    print(f"Developer status: {context.status}")
    print(f"Last active: {context.last_active}")
```

### Blockers and Actions

```python
from coordinator_memory import Priority

# Add blocker
blocker = memory.add_blocker(
    description="Message broker not available",
    impact=Priority.HIGH,
    affected_state="TESTING",
    affected_agent="Tester / QA"
)

# Resolve blocker
memory.resolve_blocker(
    blocker_id=blocker.id,
    resolution="Configured test message broker instance"
)

# Get active blockers
active = memory.get_active_blockers()

# Add pending action
action = memory.add_pending_action(
    action="Add integration tests",
    owner="Tester / QA",
    priority=Priority.HIGH,
    due_by=datetime(2025, 10, 8, 12, 0)
)

# Complete action
memory.complete_pending_action(action.id, outcome="Tests added")
```

### Metrics and Analysis

```python
# Get metrics
metrics = memory.get_metrics()
print(f"Total features: {metrics.total_features}")
print(f"Average cycle time: {metrics.average_cycle_time}h")

# Identify bottlenecks
slowest = max(metrics.state_cycle_times.items(), key=lambda x: x[1])
print(f"Slowest state: {slowest[0]} ({slowest[1]}h)")

# Analyze rework patterns
for pattern in metrics.rework_patterns:
    print(f"{pattern.from_state} → {pattern.to_state}: {pattern.count} times")
```

### Decision Recording

```python
from datetime import datetime, timedelta

# Record decision
decision = memory.record_decision(
    decision="Use at-least-once delivery",
    rationale="Balance reliability and complexity",
    outcome="Consumers handle duplicates",
    context={"alternative": "exactly-once"}
)

# Query recent decisions
since = datetime.utcnow() - timedelta(days=7)
recent = memory.get_decisions(since=since)
```

## Query Patterns

### Find Rejected Handovers

```bash
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED
```

```python
rejected = memory.get_handover_history(status=HandoverStatus.REJECTED)
for h in rejected:
    print(f"[{h.timestamp}] {h.from_agent} → {h.to_agent}")
    print(f"  Rejection: {h.rejection_reason}")
```

### Identify Workflow Bottlenecks

```bash
python3 .coordinator/coordinator_cli.py metrics
```

```python
metrics = memory.get_metrics()
slowest = max(metrics.state_cycle_times.items(), key=lambda x: x[1])
print(f"Bottleneck: {slowest[0]} ({slowest[1]}h average)")
```

### Track Agent Workload

```python
metrics = memory.get_metrics()
for agent, hours in sorted(metrics.agent_utilization.items(), key=lambda x: x[1], reverse=True):
    print(f"{agent}: {hours}h")
```

### Analyze Rework Patterns

```python
metrics = memory.get_metrics()
common = sorted(metrics.rework_patterns, key=lambda p: p.count, reverse=True)[:3]

for pattern in common:
    print(f"{pattern.from_state} → {pattern.to_state}: {pattern.count} occurrences")
    print(f"  Reason: {pattern.reason}")
```

### Review Feature History

```python
from datetime import datetime, timedelta

# Transitions in last 7 days
cutoff = datetime.utcnow() - timedelta(days=7)
recent = [t for t in memory.state.state_history if t.timestamp >= cutoff and t.approved]

print(f"Transitions in last 7 days: {len(recent)}")
```

## Troubleshooting

### File Lock Conflicts

**Symptom:** CLI hangs or times out

**Solution:**
```bash
# Check for stale lock files
ls -la .coordinator/*.lock

# Remove stale locks (ensure no coordinator running)
rm .coordinator/coordinator-state.json.lock
```

**Prevention:** The CLI uses `fcntl` locks with automatic cleanup. Stale locks only occur if the process is killed with `kill -9`.

### JSON Corruption

**Symptom:** `Failed to parse coordinator-state.json`

**Solution:**
```bash
# Check for backup
ls -la .coordinator/*.backup.*

# Restore from backup
cp .coordinator/coordinator-state.json.backup.20251007143000 \
   .coordinator/coordinator-state.json

# Verify restoration
python3 .coordinator/coordinator_cli.py status
```

**Prevention:** Automatic backups are created on every load. The CLI uses atomic writes (temp file + rename) to prevent corruption.

### Invalid State Recovery

**Symptom:** Transition rejected unexpectedly

**Diagnosis:**
```bash
# Check current state
python3 .coordinator/coordinator_cli.py status

# Review recent transitions
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-07T00:00:00Z
```

**Solution:**
```python
# Manually inspect state file
import json
with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
    print(f"Current state: {state['currentState']}")
    print(f"Last transition: {state['stateHistory'][-1]}")
```

### Permission Errors

**Symptom:** `Permission denied` when accessing state file

**Solution:**
```bash
# Check file permissions
ls -la .coordinator/coordinator-state.json

# Fix permissions
chmod 644 .coordinator/coordinator-state.json
```

### Python Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'coordinator_memory'`

**Solution:**
```bash
# Ensure you're in the correct directory
cd /path/to/project-root

# Use full path to CLI
python3 .coordinator/coordinator_cli.py status

# Or add to PYTHONPATH
export PYTHONPATH=".coordinator:$PYTHONPATH"
```

### Debugging Tips

**Enable verbose output:**
```python
# Add to coordinator_memory.py temporarily
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect state directly:**
```bash
# Pretty-print state file
python3 -m json.tool .coordinator/coordinator-state.json
```

**Validate schema:**
```bash
# Install jsonschema
pip install jsonschema

# Validate
python3 -c "
import json
import jsonschema

with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
with open('.coordinator/memory-schema.json') as f:
    schema = json.load(f)

jsonschema.validate(state, schema)
print('✅ State is valid')
"
```

## Maintenance Guidelines

### State File Management

- **Location:** `.coordinator/coordinator-state.json` (project root)
- **Format:** JSON with camelCase properties (2-space indent)
- **Backups:** Automatic `.backup.{timestamp}` on corruption
- **Size:** Monitor file growth (archive if > 10 MB)
- **Version Control:** Add to `.gitignore` if causing merge conflicts

### Archiving Old Data

For long-running projects with 1000+ handovers:

```python
from datetime import datetime, timedelta

memory = CoordinatorMemory()
state = memory.get_state()

# Archive transitions older than 30 days
cutoff = datetime.utcnow() - timedelta(days=30)
old = [t for t in state.state_history if t.timestamp < cutoff]

# Save to archive
import json
archive = {"archived_at": datetime.utcnow().isoformat(), "transitions": old}
with open(f"archive-{datetime.utcnow():%Y%m%d}.json", "w") as f:
    json.dump(archive, f, indent=2)

print(f"Archived {len(old)} transitions")
```

### Schema Evolution

When adding new properties:

1. Update `memory-schema.json` with new property
2. Add to Python dataclasses in `coordinator_memory.py`
3. Update `_create_initial_state()` with default value
4. Add API methods for new property
5. Document in this README
6. Update tests in `test_coordinator_memory.py`

### Performance Considerations

- **File I/O:** All operations read/write full state file (~1ms for 1MB)
- **Concurrency:** File locks prevent race conditions (wait up to 10s)
- **Memory:** Entire state loaded into memory (typically < 10 MB)
- **Startup:** Cold start ~50ms, warm ~10ms

**Optimization tips:**
- For high-frequency updates, batch operations when possible
- Archive old data to keep state file < 1 MB
- Use `get_state()` once and query in-memory for multiple reads

### Testing

```bash
# Run all tests (35 tests)
python3 -m pytest .coordinator/test_coordinator_memory.py -v

# Run specific test
python3 -m pytest .coordinator/test_coordinator_memory.py::test_valid_handover -v

# Run with coverage
python3 -m pytest .coordinator/test_coordinator_memory.py --cov=coordinator_memory
```

## Integration with Multi-Agent Workflow

### Coordinator Agent Usage

The Coordinator agent is the **only** agent that directly executes CLI commands:

```
1. Agent completes work
2. Agent requests: "@coordinator handover from DEVELOPMENT to CI_CD, reason: Code ready"
3. Coordinator validates request
4. Coordinator executes: python3 .coordinator/coordinator_cli.py handover ...
5. Coordinator responds to agent with approval/rejection
```

**Coordinator responsibilities:**
- Validate state transitions against state machine
- Execute all CLI commands
- Approve/reject handover requests
- Track workflow metrics
- Enforce no-human-contact policy
- Learn from workflow patterns

### Agent Integration Pattern

**Agents should NOT:**
- ❌ Call `coordinator_cli.py` directly
- ❌ Modify `coordinator-state.json` directly
- ❌ Import `coordinator_memory.py` directly

**Agents SHOULD:**
- ✅ Request handovers via `@coordinator`
- ✅ Report work products in handover requests
- ✅ Check for blockers affecting their state
- ✅ Update status when starting/completing work (via @coordinator)

**Example agent workflow:**

```
Developer completes implementation:
→ "@coordinator handover from DEVELOPMENT to CI_CD
   Reason: Feature implementation complete
   Context: Added 3 event producer endpoints
   Artifacts: src/messaging/producers/event_producer.py"

Coordinator validates and executes:
→ python3 .coordinator/coordinator_cli.py handover \
    --from-agent "Developer" \
    --to-agent "DevOps Engineer" \
    --from-state DEVELOPMENT \
    --to-state CI_CD \
    --reason "Feature implementation complete" \
    --context "Added 3 event producer endpoints" \
    --artifacts "src/messaging/producers/event_producer.py"

Coordinator responds:
→ "✅ APPROVED - Handover from Developer to DevOps Engineer
   Transition: DEVELOPMENT → CI_CD
   DevOps Engineer: Please verify build and run tests"
```

### CI/CD Integration

```bash
# In CI pipeline, coordinator can:

# Record build status
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "DevOps Engineer" \
  --status COMPLETE \
  --output "Build passed: all tests green"

# Automatic handover on success
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "DevOps Engineer" \
  --to-agent "Reviewer" \
  --from-state CI_CD \
  --to-state REVIEW \
  --reason "Build succeeded" \
  --context "All 47 tests passed"
```

## Workflow State Machine

### Valid States

```
INIT → REQUIREMENTS → ARCHITECTURE → DEVELOPMENT → CI_CD → REVIEW → TESTING → PERFORMANCE → VALIDATION → COMPLETE
```

### Valid Transitions

| From State      | Valid Targets                          | Purpose                |
|-----------------|----------------------------------------|------------------------|
| INIT            | REQUIREMENTS                           | Start feature          |
| REQUIREMENTS    | ARCHITECTURE                           | Design phase           |
| ARCHITECTURE    | DEVELOPMENT, REQUIREMENTS              | Implement or clarify   |
| DEVELOPMENT     | CI_CD, ARCHITECTURE                    | Build or redesign      |
| CI_CD           | REVIEW, DEVELOPMENT                    | Review or fix build    |
| REVIEW          | TESTING, DEVELOPMENT, ARCHITECTURE     | Test, fix, or redesign |
| TESTING         | PERFORMANCE, DEVELOPMENT               | Optimize or fix tests  |
| PERFORMANCE     | VALIDATION, DEVELOPMENT                | Validate or optimize   |
| VALIDATION      | COMPLETE, REQUIREMENTS                 | Finish or redefine     |
| COMPLETE        | *(terminal state)*                     | Feature merged         |

### Feedback Loops

- **ARCHITECTURE → REQUIREMENTS:** Clarify ambiguous requirements
- **DEVELOPMENT → ARCHITECTURE:** Design changes needed
- **CI_CD → DEVELOPMENT:** Build failures
- **REVIEW → DEVELOPMENT:** Code issues found
- **REVIEW → ARCHITECTURE:** Design flaws discovered
- **TESTING → DEVELOPMENT:** Test failures
- **PERFORMANCE → DEVELOPMENT:** Performance issues
- **VALIDATION → REQUIREMENTS:** Acceptance criteria not met

## Agent Roles

- **Coordinator** - Orchestrates workflow, validates transitions
- **Requirements Engineer** - Defines features, validates acceptance
- **Tech Lead** - Architecture decisions, design reviews
- **Developer** - Code implementation
- **DevOps Engineer** - CI/CD, builds, deployments
- **Reviewer** - Code review, quality checks
- **Tester / QA** - Test creation, execution
- **Performance Engineer** - Performance optimization
- **Documentation Agent** - Documentation updates

## Autonomy Policy

The coordinator enforces a strict autonomy policy to ensure workflow efficiency and minimize human interruption:

### Core Principles

**Agents operate autonomously from REQUIREMENTS to VALIDATION**
- No human confirmation required for technical decisions
- Agents consult specialist agents via @coordinator, never humans
- Only humans initiate features (INIT state) and approve final PR merge (COMPLETE state)

### Decision Authority

**Technical Decisions:**
- Agents have full authority within their domain (Developer → code structure, Tech Lead → architecture, etc.)
- Uncertain decisions escalated to relevant specialist agent (e.g., @tech-lead for architecture)
- Best judgment based on project conventions and existing patterns
- **NEVER escalate technical decisions to humans mid-workflow**

**Handover Validation:**
- Coordinator validates all transitions against state machine
- Invalid transitions rejected with required path, never escalated to humans
- Coordinator provides guidance on correct workflow path

### Human Interaction Points

**Only 2 human touchpoints per feature:**

1. **INIT → REQUIREMENTS**: Human defines feature request
2. **VALIDATION → COMPLETE**: Human approves PR merge to main

**Between these points, agents are fully autonomous.**

### Enforcement

**Coordinator MUST reject:**
- ❌ Agent requests for human confirmation before VALIDATION state
- ❌ Agent questions asking "Should I proceed?" or "Does the user want X?"
- ❌ Agent attempts to delegate decisions to humans instead of specialist agents

**Coordinator MUST provide:**
- ✅ Clear guidance on which specialist agent to consult
- ✅ Context from previous work to inform decisions
- ✅ Approval/rejection of transitions with actionable next steps

**Example rejection:**
```
Agent: "Should I ask the user if they want error logging?"
Coordinator: ❌ REJECTED - Do not contact humans mid-workflow.
Decision: Consult @tech-lead for architecture decision, or follow project conventions in existing error handling code.
```

## Error Handling

The coordinator memory system includes comprehensive error handling to ensure reliability and recoverability.

### CLI Error Responses

All CLI commands return structured JSON with `success` boolean:

**Success:**
```json
{
  "success": true,
  "handover": { "id": "...", "status": "APPROVED" }
}
```

**Failure:**
```json
{
  "success": false,
  "error": "Invalid transition: DEVELOPMENT → TESTING"
}
```

### Common Error Scenarios

#### Invalid State Transition

**Error:** `Invalid transition: [FROM_STATE] → [TO_STATE]`

**Cause:** Attempted transition not in allowed state matrix

**Resolution:**
```bash
# Check current state
python3 .coordinator/coordinator_cli.py status

# Review valid transitions for current state (see Workflow State Machine section)
# Example: DEVELOPMENT can only go to CI_CD or ARCHITECTURE
```

**Coordinator action:** Reject handover with required path

#### File Lock Timeout

**Error:** `Failed to acquire file lock after 10s`

**Cause:** Another process holds lock on state file, or stale lock from killed process

**Resolution:**
```bash
# Check for stale lock files
ls -la .coordinator/*.lock

# If no coordinator running, remove stale lock
rm .coordinator/coordinator-state.json.lock

# Retry operation
python3 .coordinator/coordinator_cli.py status
```

**Prevention:** Avoid `kill -9` on coordinator process; use `Ctrl+C` for clean shutdown

#### JSON Parse Error

**Error:** `Failed to parse coordinator-state.json: Expecting ',' delimiter`

**Cause:** State file corrupted (incomplete write, manual edit, merge conflict)

**Resolution:**
```bash
# Check for automatic backup
ls -la .coordinator/*.backup.*

# Restore most recent backup
cp .coordinator/coordinator-state.json.backup.20251007143000 \
   .coordinator/coordinator-state.json

# Verify restoration
python3 .coordinator/coordinator_cli.py status
```

**Prevention:** Never manually edit state file; automatic backups created on every load

#### Schema Validation Error

**Error:** `State does not conform to schema: 'currentState' is required`

**Cause:** State file missing required properties or has wrong types

**Resolution:**
```bash
# Validate schema manually
python3 -c "
import json
import jsonschema

with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
with open('.coordinator/memory-schema.json') as f:
    schema = json.load(f)

jsonschema.validate(state, schema)
print('✅ State is valid')
"

# If validation fails, restore from backup or re-initialize
```

#### Permission Denied

**Error:** `Permission denied: .coordinator/coordinator-state.json`

**Cause:** Incorrect file permissions

**Resolution:**
```bash
# Check permissions
ls -la .coordinator/coordinator-state.json

# Fix permissions (read/write for owner, read for group)
chmod 644 .coordinator/coordinator-state.json
```

#### Blocker Not Found

**Error:** `Blocker with id [...] not found`

**Cause:** Blocker already resolved or invalid ID

**Resolution:**
```bash
# List active blockers
python3 .coordinator/coordinator_cli.py list-blockers

# Use correct blocker ID from list
```

#### Action Not Found

**Error:** `Action with id [...] not found`

**Cause:** Action already completed or invalid ID

**Resolution:**
```bash
# List pending actions (not yet implemented in CLI, use Python API)
from coordinator_memory import CoordinatorMemory
memory = CoordinatorMemory()
actions = [a for a in memory.state.pending_actions if a.status == "PENDING"]
```

### Python Exception Handling

When using the Python API, catch specific exceptions:

```python
from coordinator_memory import CoordinatorMemory, WorkflowState

memory = CoordinatorMemory()

try:
    result = memory.transition_state(
        from_state=WorkflowState.DEVELOPMENT,
        to_state=WorkflowState.TESTING,
        reason="Tests ready"
    )
    if not result.success:
        print(f"Transition rejected: {result.error_message}")
except FileNotFoundError:
    print("State file not found - initializing new state")
    memory = CoordinatorMemory()  # Creates new state file
except json.JSONDecodeError as e:
    print(f"State file corrupted: {e}")
    # Restore from backup
except PermissionError:
    print("Permission denied - check file permissions")
```

### Logging and Diagnostics

**Enable debug logging:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from coordinator_memory import CoordinatorMemory
memory = CoordinatorMemory()
```

**Inspect state file directly:**
```bash
# Pretty-print state
python3 -m json.tool .coordinator/coordinator-state.json

# Check file size
ls -lh .coordinator/coordinator-state.json

# Check last modified
ls -l .coordinator/coordinator-state.json
```

## Recovery Procedures

When workflow issues occur, follow these procedures to restore operation.

### Corrupted State Recovery

**Symptom:** CLI returns JSON parse errors or schema validation failures

**Procedure:**

1. **Identify issue:**
```bash
python3 .coordinator/coordinator_cli.py status
# Error: Failed to parse coordinator-state.json
```

2. **Locate backups:**
```bash
ls -lt .coordinator/*.backup.* | head -5
# Find most recent uncorrupted backup
```

3. **Restore from backup:**
```bash
# Copy backup (preserves original corrupt file)
cp .coordinator/coordinator-state.json.backup.20251007120000 \
   .coordinator/coordinator-state.json

# Verify restoration
python3 .coordinator/coordinator_cli.py status
```

4. **Validate restored state:**
```bash
# Check that handover log is complete
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-07T00:00:00Z

# Check metrics
python3 .coordinator/coordinator_cli.py metrics
```

5. **Document data loss:**
   - Compare corrupt file timestamp with backup timestamp
   - Identify any lost handovers (between backup and corruption)
   - Manually re-record lost handovers if critical

### Stuck Workflow Recovery

**Symptom:** Workflow stuck in state with no progress (e.g., DEVELOPMENT for 24+ hours)

**Procedure:**

1. **Diagnose stuck state:**
```bash
# Check current state and duration
python3 .coordinator/coordinator_cli.py status

# Check recent handovers
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-06T00:00:00Z

# Check for blockers
python3 .coordinator/coordinator_cli.py list-blockers
```

2. **Identify cause:**
   - **Active blocker:** Resolve blocker first
   - **Agent stalled:** Check agent context for last output
   - **Invalid state:** Handovers rejected due to invalid transitions

3. **Resolve blocker (if present):**
```bash
# Example: Database dependency blocking testing
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id <id> \
  --resolution "Test database configured on port 5433"
```

4. **Resume workflow:**
```bash
# If agent stalled, manually trigger handover
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Resuming after stall" \
  --context "Implementation complete, ready for build"
```

5. **Prevent recurrence:**
   - Document why agent stalled (missing context? unclear requirements?)
   - Add decision to project knowledge
   - Update agent guidance to prevent similar stalls

### Invalid State Recovery

**Symptom:** Current state doesn't match actual workflow progress (e.g., state is DEVELOPMENT but code already merged)

**Procedure:**

1. **Confirm mismatch:**
```bash
# Check state
python3 .coordinator/coordinator_cli.py status

# Check git branch state
git status
git log --oneline -5
```

2. **Determine correct state:**
   - Review state history: `list-handovers --since <date>`
   - Identify where mismatch occurred
   - Determine correct current state based on actual progress

3. **Manual state correction (emergency only):**

**WARNING:** Only use when automated transitions failed. Prefer retrying correct handover.

```python
from coordinator_memory import CoordinatorMemory, WorkflowState
import json

# Load state
memory = CoordinatorMemory()
state = memory.get_state()

# Manually set correct state
state.current_state = WorkflowState.REVIEW  # Example: correct state

# Save (use with caution!)
memory._save_state(state)

# Verify
print(memory.get_current_state())
```

4. **Record correction:**
```bash
# Document manual intervention
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Manually corrected workflow state from DEVELOPMENT to REVIEW" \
  --rationale "Automated handover failed due to [reason]" \
  --impact "Lost audit trail for DEVELOPMENT → CI_CD → REVIEW transitions"
```

5. **Resume normal workflow:**
   - From corrected state, proceed with valid handovers
   - Monitor for repeated invalid states (indicates systemic issue)

### Lost Handover Recovery

**Symptom:** Handover should have occurred but not recorded in log

**Procedure:**

1. **Confirm missing handover:**
```bash
# Check handover log
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-07T00:00:00Z

# Expected: Developer → DevOps → Reviewer
# Actual: Developer → Reviewer (missing DevOps handover)
```

2. **Determine if functional impact:**
   - Was DevOps work actually completed? (check git log, CI runs)
   - Is state machine still valid? (current state matches actual progress)

3. **Backfill missing handover (if needed for audit):**

```python
from coordinator_memory import CoordinatorMemory, WorkflowState, Handover, HandoverStatus
from datetime import datetime

memory = CoordinatorMemory()

# Create missing handover record
missing_handover = Handover(
    id=str(uuid.uuid4()),
    from_agent="Developer",
    to_agent="DevOps Engineer",
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    status=HandoverStatus.APPROVED,
    timestamp=datetime(2025, 10, 7, 14, 30),  # Use actual time if known
    reason="[BACKFILLED] Build verification",
    context="Handover occurred but not logged",
    artifacts=[]
)

# Add to log
state = memory.get_state()
state.handover_log.append(missing_handover)
memory._save_state(state)
```

4. **Document backfill:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Backfilled missing handover: Developer → DevOps Engineer" \
  --rationale "Handover occurred but not logged due to [reason]" \
  --impact "Audit trail incomplete for this transition"
```

### Complete State Reset (last resort)

**Symptom:** State file unrecoverable and no valid backups

**WARNING:** Loses all workflow history. Only use when state file completely lost.

**Procedure:**

1. **Confirm no recovery possible:**
```bash
# Check all backups
ls -la .coordinator/*.backup.*

# All backups corrupted or missing
```

2. **Archive corrupt state:**
```bash
mkdir -p .coordinator/archive
mv .coordinator/coordinator-state.json \
   .coordinator/archive/corrupt-$(date +%Y%m%d%H%M%S).json
```

3. **Initialize fresh state:**
```bash
# CLI creates new state file automatically if missing
python3 .coordinator/coordinator_cli.py status

# Output: Fresh initialized state at INIT
```

4. **Manually set current progress:**

```python
from coordinator_memory import CoordinatorMemory, WorkflowState

memory = CoordinatorMemory()

# Set feature if mid-workflow
memory.set_current_feature(
    name="event-streaming",
    branch="feature/event-streaming",
    description="Add event streaming",
    acceptance_criteria=["Events published successfully", "Retry configured"]
)

# Set state to match actual progress
# Example: If code written but not reviewed yet
result = memory.transition_state(
    from_state=WorkflowState.INIT,
    to_state=WorkflowState.REQUIREMENTS,
    reason="Manual recovery - state lost"
)
result = memory.transition_state(
    from_state=WorkflowState.REQUIREMENTS,
    to_state=WorkflowState.ARCHITECTURE,
    reason="Manual recovery - state lost"
)
result = memory.transition_state(
    from_state=WorkflowState.ARCHITECTURE,
    to_state=WorkflowState.DEVELOPMENT,
    reason="Manual recovery - resuming from current progress"
)
```

5. **Document reset:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Performed complete state reset due to unrecoverable corruption" \
  --rationale "State file and all backups corrupted/missing" \
  --impact "Lost entire workflow history before $(date -Iseconds)"
```

6. **Resume workflow:**
   - From manually set state, proceed with normal handovers
   - All future handovers will be properly logged
   - Previous history permanently lost (accept and continue)

## License

Part of multi-agent workflow system. See project root for license information.
