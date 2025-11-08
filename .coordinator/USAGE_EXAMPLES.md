# Coordinator Memory - Usage Examples

This guide provides real-world workflow scenarios with complete CLI commands for the coordinator.

## Table of Contents

1. [Complete Feature Workflow](#1-complete-feature-workflow)
2. [Handling Rejected Handovers](#2-handling-rejected-handovers)
3. [Managing Blockers During Development](#3-managing-blockers-during-development)
4. [Recording Architectural Decisions](#4-recording-architectural-decisions)
5. [Finding Workflow Bottlenecks](#5-finding-workflow-bottlenecks)
6. [Handling Concurrent Agent Work](#6-handling-concurrent-agent-work)
7. [Recovering from Failed Transitions](#7-recovering-from-failed-transitions)
8. [Multi-Feature Tracking](#8-multi-feature-tracking)
9. [Analyzing Rework Patterns](#9-analyzing-rework-patterns)
10. [Managing Pending Actions](#10-managing-pending-actions)

---

## 1. Complete Feature Workflow

**Scenario:** Walk through an entire feature from INIT to COMPLETE.

### Initial Setup

```bash
# Check starting state
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "currentState": "INIT",
  "currentFeature": null
}
```

### Human Defines Feature (Product Owner)

Agent receives feature request:
```
@coordinator New feature: Add event streaming for bet operations
Requirements:
- Publish events on create/update/delete
- Configure retry policy with exponential backoff
- Add integration tests
Linked to issue #245
```

### Requirements Phase

**Coordinator creates feature:**
```bash
python3 .coordinator/coordinator_cli.py set-feature \
  --name "event-streaming" \
  --branch "feature/event-streaming" \
  --description "Add event publishing for bet CRUD operations" \
  --criteria "Events published on create/update/delete,Retry policy with exponential backoff,Integration tests passing" \
  --issues "#245"
```

**Output:**
```json
{
  "success": true,
  "feature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming",
    "description": "Add event publishing for bet CRUD operations",
    "startedAt": "2025-10-07T09:00:00Z",
    "acceptanceCriteria": [
      "Events published on create/update/delete",
      "Retry policy with exponential backoff",
      "Integration tests passing"
    ],
    "linkedIssues": ["#245"]
  }
}
```

**Coordinator transitions to REQUIREMENTS:**
```bash
python3 .coordinator/coordinator_cli.py transition \
  --from-state INIT \
  --to-state REQUIREMENTS \
  --reason "Feature defined by product owner" \
  --context "3 acceptance criteria defined, linked to #245"
```

**Requirements Engineer completes analysis:**
```bash
# Update agent status
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Requirements Engineer" \
  --status COMPLETE \
  --output "Requirements analysis complete, ready for architecture"
```

**Requirements Engineer requests handover:**
```
@coordinator handover from REQUIREMENTS to ARCHITECTURE
Reason: Requirements clarified and documented
Context: Created feature branch, defined 3 acceptance criteria
```

**Coordinator executes:**
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Requirements Engineer" \
  --to-agent "Tech Lead" \
  --from-state REQUIREMENTS \
  --to-state ARCHITECTURE \
  --reason "Requirements clarified and documented" \
  --context "Created feature branch, defined 3 acceptance criteria"
```

**Output:**
```json
{
  "success": true,
  "handover": {
    "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    "fromAgent": "Requirements Engineer",
    "toAgent": "Tech Lead",
    "fromState": "REQUIREMENTS",
    "toState": "ARCHITECTURE",
    "status": "APPROVED",
    "timestamp": "2025-10-07T09:30:00Z"
  }
}
```

### Architecture Phase

**Tech Lead analyzes design:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Tech Lead" \
  --status WORKING \
  --output "Designing event producer architecture"
```

**Tech Lead records decision:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use at-least-once delivery semantics for event publishing" \
  --rationale "Balances reliability with implementation complexity. Exactly-once is overkill for bet events." \
  --impact "Consumers must handle duplicate events idempotently" \
  --context '{"alternatives":["exactly-once","fire-and-forget"],"risk":"LOW","complexity":"MEDIUM"}'
```

**Tech Lead completes design:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Tech Lead" \
  --status COMPLETE \
  --output "Architecture design complete"
```

**Tech Lead requests handover:**
```
@coordinator handover from ARCHITECTURE to DEVELOPMENT
Reason: Architecture approved, ready for implementation
Context: Event producer pattern defined, retry policy designed
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Tech Lead" \
  --to-agent "Developer" \
  --from-state ARCHITECTURE \
  --to-state DEVELOPMENT \
  --reason "Architecture approved" \
  --context "Event producer pattern defined, retry policy designed"
```

### Development Phase

**Developer implements feature:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Implementing event producer and event classes"
```

**Developer completes implementation:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status COMPLETE \
  --output "Implementation complete, all code committed" \
  --work-products "src/messaging/producers/event_producer.py,src/messaging/events/bet_created_event.py,src/messaging/configuration/retry_policy_config.py"
```

**Developer requests handover:**
```
@coordinator handover from DEVELOPMENT to CI_CD
Reason: Feature implementation complete
Context: Added event producer with retry policy, 3 event classes created
Artifacts: src/messaging/producers/event_producer.py, src/messaging/events/bet_created_event.py
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Feature implementation complete" \
  --context "Added event producer with retry policy" \
  --artifacts "src/messaging/producers/event_producer.py,src/messaging/events/bet_created_event.py"
```

### CI/CD Phase

**DevOps Engineer monitors build:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "DevOps Engineer" \
  --status WORKING \
  --output "Running build and unit tests"
```

**Build succeeds:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "DevOps Engineer" \
  --status COMPLETE \
  --output "Build successful: all 52 unit tests passed"
```

**DevOps Engineer requests handover:**
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "DevOps Engineer" \
  --to-agent "Reviewer" \
  --from-state CI_CD \
  --to-state REVIEW \
  --reason "Build succeeded" \
  --context "All 52 unit tests passed, code coverage 87%"
```

### Review Phase

**Reviewer examines code:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Reviewer" \
  --status WORKING \
  --output "Reviewing event producer implementation"
```

**Reviewer approves:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Reviewer" \
  --status COMPLETE \
  --output "Code review approved, ready for testing"
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Reviewer" \
  --to-agent "Tester / QA" \
  --from-state REVIEW \
  --to-state TESTING \
  --reason "Code review approved" \
  --context "No issues found, code quality excellent"
```

### Testing Phase

**QA creates tests:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Tester / QA" \
  --status WORKING \
  --output "Creating integration tests for event producer"
```

**QA completes testing:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Tester / QA" \
  --status COMPLETE \
  --output "All integration tests passing" \
  --work-products "tests/integration/event_producer_tests.py"
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Tester / QA" \
  --to-agent "Performance Engineer" \
  --from-state TESTING \
  --to-state PERFORMANCE \
  --reason "All tests passing" \
  --context "10 integration tests added and passing"
```

### Performance Phase

**Performance Engineer benchmarks:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Performance Engineer" \
  --status WORKING \
  --output "Running performance benchmarks"
```

**Performance acceptable:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Performance Engineer" \
  --status COMPLETE \
  --output "Performance within acceptable limits"
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Performance Engineer" \
  --to-agent "Requirements Engineer" \
  --from-state PERFORMANCE \
  --to-state VALIDATION \
  --reason "Performance validated" \
  --context "Event publishing: 5000 events/sec, latency p99: 45ms"
```

### Validation Phase

**Requirements Engineer validates:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Requirements Engineer" \
  --status WORKING \
  --output "Validating acceptance criteria"
```

**All criteria met:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Requirements Engineer" \
  --status COMPLETE \
  --output "All acceptance criteria validated, creating PR"
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Requirements Engineer" \
  --to-agent "Coordinator" \
  --from-state VALIDATION \
  --to-state COMPLETE \
  --reason "All acceptance criteria met" \
  --context "PR #256 created and approved, merging to main"
```

### Complete Phase

**Feature complete:**
```bash
python3 .coordinator/coordinator_cli.py clear-feature
```

**Output:**
```json
{
  "success": true
}
```

**Check final metrics:**
```bash
python3 .coordinator/coordinator_cli.py metrics
```

---

## 2. Handling Rejected Handovers

**Scenario:** Developer tries to skip CI/CD and go directly to testing.

**Developer requests invalid handover:**
```
@coordinator handover from DEVELOPMENT to TESTING
Reason: Code complete and tests passing locally
```

**Coordinator attempts:**
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "Tester / QA" \
  --from-state DEVELOPMENT \
  --to-state TESTING \
  --reason "Code complete and tests passing locally"
```

**Output (REJECTED):**
```json
{
  "success": false,
  "error": "Invalid transition: DEVELOPMENT → TESTING. Required path: DEVELOPMENT → CI_CD → REVIEW → TESTING",
  "handover": {
    "id": "b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e",
    "status": "REJECTED",
    "rejectionReason": "Cannot skip CI_CD and REVIEW states. Must go through: DEVELOPMENT → CI_CD → REVIEW → TESTING"
  }
}
```

**Coordinator responds to Developer:**
```
❌ REJECTED - Invalid state transition

Required path:
  DEVELOPMENT → CI_CD → REVIEW → TESTING

You cannot skip CI_CD and REVIEW states.

Please request:
  @coordinator handover from DEVELOPMENT to CI_CD
  Reason: Feature implementation complete
```

**Developer corrects request:**
```
@coordinator handover from DEVELOPMENT to CI_CD
Reason: Feature implementation complete
```

```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Feature implementation complete"
```

**Output (APPROVED):**
```json
{
  "success": true,
  "handover": {
    "id": "c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f",
    "fromAgent": "Developer",
    "toAgent": "DevOps Engineer",
    "fromState": "DEVELOPMENT",
    "toState": "CI_CD",
    "status": "APPROVED",
    "timestamp": "2025-10-07T11:45:00Z"
  }
}
```

**Query all rejections to learn patterns:**
```bash
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED
```

---

## 3. Managing Blockers During Development

**Scenario:** Developer encounters missing message broker during development.

**Developer reports blocker:**
```
@coordinator blocker: Message broker not available in development environment
Impact: HIGH - Cannot test event publishing
Affected: DEVELOPMENT, Developer
```

**Coordinator records blocker:**
```bash
python3 .coordinator/coordinator_cli.py add-blocker \
  --description "Message broker not available in development environment" \
  --impact HIGH \
  --affected-state DEVELOPMENT \
  --affected-agent "Developer"
```

**Output:**
```json
{
  "success": true,
  "blocker": {
    "id": "d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a",
    "description": "Message broker not available in development environment",
    "impact": "HIGH",
    "affectedState": "DEVELOPMENT",
    "affectedAgent": "Developer",
    "status": "OPEN",
    "createdAt": "2025-10-07T10:30:00Z"
  }
}
```

**Coordinator creates action for DevOps:**
```bash
python3 .coordinator/coordinator_cli.py add-action \
  --action "Set up message broker in development environment" \
  --owner "DevOps Engineer" \
  --priority CRITICAL \
  --due-by "2025-10-07T14:00:00Z"
```

**Output:**
```json
{
  "success": true,
  "action": {
    "id": "e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b",
    "action": "Set up message broker in development environment",
    "owner": "DevOps Engineer",
    "priority": "CRITICAL",
    "status": "PENDING",
    "createdAt": "2025-10-07T10:30:00Z",
    "dueBy": "2025-10-07T14:00:00Z"
  }
}
```

**Developer waits, updates status:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status BLOCKED \
  --output "Waiting for message broker setup"
```

**DevOps Engineer resolves:**
```bash
python3 .coordinator/coordinator_cli.py complete-action \
  --action-id "e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b" \
  --outcome "Message broker configured on localhost:5672"
```

**Coordinator resolves blocker:**
```bash
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id "d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a" \
  --resolution "Message broker configured on localhost:5672, developer can proceed"
```

**Output:**
```json
{
  "success": true,
  "blockerId": "d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a"
}
```

**Developer resumes:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Blocker resolved, continuing implementation"
```

**Check active blockers:**
```bash
python3 .coordinator/coordinator_cli.py list-blockers
```

**Output:**
```json
{
  "count": 0,
  "blockers": []
}
```

---

## 4. Recording Architectural Decisions

**Scenario:** Tech Lead makes key architectural decisions during design phase.

**Decision 1: Event Schema Design**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use CloudEvents specification for event schema" \
  --rationale "Industry standard, provides interoperability, well-documented" \
  --impact "All events must conform to CloudEvents format" \
  --context '{"alternative":"Custom schema","benefits":["Standardization","Tooling support","Documentation"],"cost":"Learning curve"}'
```

**Decision 2: Message Delivery Semantics**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Implement at-least-once delivery semantics" \
  --rationale "Simpler than exactly-once, sufficient for event processing. Consumers can deduplicate." \
  --impact "Consumers must implement idempotent processing" \
  --context '{"alternative":"Exactly-once semantics","tradeoff":"Complexity vs reliability","risk":"LOW"}'
```

**Decision 3: Retry Policy**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use exponential backoff with max 5 retries for message publishing" \
  --rationale "Balances resilience with avoiding infinite loops. Backoff prevents broker overload." \
  --impact "Failed events after 5 retries go to dead letter queue" \
  --context '{"initial_delay":"100ms","max_delay":"30s","max_retries":5,"dead_letter_topic":"events-dlq"}'
```

**Query recent decisions:**
```bash
python3 .coordinator/coordinator_cli.py list-decisions --since 2025-10-07T00:00:00Z
```

**Output:**
```json
{
  "count": 3,
  "decisions": [
    {
      "id": "f6a7b8c9-d0e1-4f2a-3b4c-5d6e7f8a9b0c",
      "decision": "Use CloudEvents specification for event schema",
      "rationale": "Industry standard, provides interoperability",
      "outcome": "All events must conform to CloudEvents format",
      "timestamp": "2025-10-07T09:45:00Z"
    },
    {
      "id": "a7b8c9d0-e1f2-4a3b-4c5d-6e7f8a9b0c1d",
      "decision": "Implement at-least-once delivery semantics",
      "rationale": "Simpler than exactly-once, sufficient for event processing",
      "outcome": "Consumers must implement idempotent processing",
      "timestamp": "2025-10-07T09:50:00Z"
    },
    {
      "id": "b8c9d0e1-f2a3-4b4c-5d6e-7f8a9b0c1d2e",
      "decision": "Use exponential backoff with max 5 retries",
      "rationale": "Balances resilience with avoiding infinite loops",
      "outcome": "Failed events after 5 retries go to DLQ",
      "timestamp": "2025-10-07T09:55:00Z"
    }
  ]
}
```

---

## 5. Finding Workflow Bottlenecks

**Scenario:** After 5 features, coordinator analyzes metrics to find bottlenecks.

**Query metrics:**
```bash
python3 .coordinator/coordinator_cli.py metrics
```

**Output:**
```json
{
  "totalFeatures": 5,
  "totalHandovers": 67,
  "rejectedHandovers": 4,
  "averageCycleTime": 5.2,
  "stateCycleTimes": {
    "REQUIREMENTS": 0.8,
    "ARCHITECTURE": 1.2,
    "DEVELOPMENT": 3.5,
    "CI_CD": 0.3,
    "REVIEW": 1.8,
    "TESTING": 2.1,
    "PERFORMANCE": 0.4,
    "VALIDATION": 0.3
  },
  "reworkPatterns": [
    {
      "fromState": "REVIEW",
      "toState": "DEVELOPMENT",
      "count": 3,
      "reason": "Missing error handling"
    },
    {
      "fromState": "TESTING",
      "toState": "DEVELOPMENT",
      "count": 2,
      "reason": "Integration test failures"
    }
  ],
  "agentUtilization": {
    "Developer": 17.5,
    "Tester / QA": 10.5,
    "Reviewer": 9.0,
    "Tech Lead": 6.0,
    "DevOps Engineer": 1.5,
    "Requirements Engineer": 5.5,
    "Performance Engineer": 2.0
  }
}
```

**Analysis:**

**Bottleneck #1: DEVELOPMENT (3.5h average)**
- 67% of total cycle time
- Longest state by far

**Action:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Pair programming for complex features to reduce development time" \
  --rationale "Development is 67% of cycle time. Pair programming can reduce rework and speed implementation." \
  --impact "Expect development time to decrease by 20-30%" \
  --context '{"current_avg":"3.5h","target_avg":"2.5h","method":"Pair programming"}'
```

**Bottleneck #2: TESTING (2.1h average)**
- Second longest state
- 40% of total cycle time

**Action:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Parallelize integration test execution to reduce testing time" \
  --rationale "Testing takes 2.1h on average. Parallel execution can reduce by 50%." \
  --impact "CI pipeline needs test parallelization support" \
  --context '{"current_avg":"2.1h","target_avg":"1.0h","method":"Parallel test execution"}'
```

**Bottleneck #3: Rework (REVIEW → DEVELOPMENT)**
- 3 occurrences of "Missing error handling"

**Action:**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Add error handling checklist to development template" \
  --rationale "60% of rework is due to missing error handling. Checklist can prevent this." \
  --impact "Expect REVIEW → DEVELOPMENT rework to decrease by 66%" \
  --context '{"rework_count":3,"reason":"Missing error handling","prevention":"Checklist"}'
```

---

## 6. Handling Concurrent Agent Work

**Scenario:** Multiple agents working simultaneously (Developer on feature, QA on another).

**Feature A: Developer working**
```bash
# Current feature
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "kafka-event-streaming",
    "branch": "feature/event-streaming"
  }
}
```

**Developer updates:**
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Implementing event producer for feature A"
```

**Feature B: QA testing previous feature**

Note: Coordinator tracks one active feature at a time (the one in the workflow). Other work can happen but isn't the "current" feature.

```bash
# QA working on previous feature (already merged, follow-up tests)
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Tester / QA" \
  --status WORKING \
  --output "Adding additional tests for previous feature"
```

**Both agents can update their status independently. File locking ensures no conflicts.**

**Check all agent statuses (Python API):**
```python
from coordinator_memory import CoordinatorMemory

memory = CoordinatorMemory()
state = memory.get_state()

for agent_name, context in state.agent_context.items():
    if context.status != "IDLE":
        print(f"{agent_name}: {context.status} - {context.last_output}")
```

**Output:**
```
Developer: WORKING - Implementing event producer for feature A
Tester / QA: WORKING - Adding additional tests for previous feature
```

**File locking prevents race conditions:**
- Each CLI command acquires exclusive lock
- Waits up to 10 seconds for lock
- Operations are atomic (read-modify-write)
- Lock automatically released on exit

---

## 7. Recovering from Failed Transitions

**Scenario:** Coordinator state file corrupted or invalid state detected.

**Symptom: JSON parse error**
```bash
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "error": "Failed to parse coordinator-state.json: Expecting property name enclosed in double quotes"
}
```

**Recovery:**

**Step 1: Check for backups**
```bash
ls -la .coordinator/*.backup.*
```

**Output:**
```
-rw-r--r--  1 user  staff  12543 Oct  7 10:30 coordinator-state.json.backup.20251007103000
-rw-r--r--  1 user  staff  12456 Oct  7 09:45 coordinator-state.json.backup.20251007094500
```

**Step 2: Restore from backup**
```bash
cp .coordinator/coordinator-state.json.backup.20251007103000 \
   .coordinator/coordinator-state.json
```

**Step 3: Verify restoration**
```bash
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "event-streaming"
  }
}
```

**Step 4: Validate state**
```bash
# Check recent history
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-07T10:00:00Z

# Check metrics
python3 .coordinator/coordinator_cli.py metrics
```

**Prevention:**
- Backups created automatically on every load
- Atomic writes (temp file + rename) prevent corruption
- Don't edit `coordinator-state.json` manually

---

## 8. Multi-Feature Tracking

**Scenario:** Tracking multiple features across different stages (using metrics).

**Current active feature:**
```bash
python3 .coordinator/coordinator_cli.py status
```

**Output:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "kafka-event-streaming",
    "startedAt": "2025-10-07T09:00:00Z"
  }
}
```

**View all recent handovers across features:**
```bash
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-01T00:00:00Z
```

**Output shows handovers from all features:**
```json
{
  "count": 67,
  "handovers": [
    {
      "id": "...",
      "fromAgent": "Requirements Engineer",
      "toAgent": "Tech Lead",
      "fromState": "REQUIREMENTS",
      "toState": "ARCHITECTURE",
      "timestamp": "2025-10-07T09:30:00Z"
    }
  ]
}
```

**View workflow metrics across all features:**
```bash
python3 .coordinator/coordinator_cli.py metrics
```

**Output:**
```json
{
  "totalFeatures": 5,
  "averageCycleTime": 5.2,
  "stateCycleTimes": {
    "DEVELOPMENT": 3.5
  }
}
```

**Note:** The system tracks **one active feature** at a time in the workflow state machine. Historical features are preserved in metrics and handover logs.

**To start a new feature:**
```bash
# Complete current feature first
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Requirements Engineer" \
  --to-agent "Coordinator" \
  --from-state VALIDATION \
  --to-state COMPLETE \
  --reason "PR merged to main"

python3 .coordinator/coordinator_cli.py clear-feature

# Start new feature
python3 .coordinator/coordinator_cli.py set-feature \
  --name "new-feature-name" \
  --branch "feature/new-feature" \
  --description "New feature description"

python3 .coordinator/coordinator_cli.py transition \
  --from-state COMPLETE \
  --to-state INIT \
  --reason "Starting new feature"

python3 .coordinator/coordinator_cli.py transition \
  --from-state INIT \
  --to-state REQUIREMENTS \
  --reason "Feature defined"
```

---

## 9. Analyzing Rework Patterns

**Scenario:** Identify common causes of rework to improve process.

**Query metrics:**
```bash
python3 .coordinator/coordinator_cli.py metrics
```

**Extract rework patterns:**
```json
{
  "reworkPatterns": [
    {
      "fromState": "REVIEW",
      "toState": "DEVELOPMENT",
      "count": 5,
      "reason": "Missing error handling"
    },
    {
      "fromState": "TESTING",
      "toState": "DEVELOPMENT",
      "count": 3,
      "reason": "Integration test failures"
    },
    {
      "fromState": "REVIEW",
      "toState": "DEVELOPMENT",
      "count": 2,
      "reason": "Missing null checks"
    }
  ]
}
```

**Analysis:**

**Pattern 1: Missing error handling (5 occurrences)**
```bash
# Record improvement action
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Add error handling section to development checklist" \
  --rationale "40% of rework is missing error handling. Checklist can prevent this." \
  --impact "Developers must verify error handling before requesting handover" \
  --context '{"rework_count":5,"total_rework":12,"percentage":41.6}'
```

**Pattern 2: Integration test failures (3 occurrences)**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Require local integration test run before handover to CI_CD" \
  --rationale "25% of rework is test failures caught in CI. Running locally first prevents this." \
  --impact "Developers must run integration tests locally and provide evidence" \
  --context '{"rework_count":3,"prevention":"Local test execution"}'
```

**Pattern 3: Missing null checks (2 occurrences)**
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Enable nullable reference types analyzer (CS8600-CS8604)" \
  --rationale "16% of rework is null-related. Compiler can catch these at build time." \
  --impact "Build will fail with null safety warnings" \
  --context '{"rework_count":2,"prevention":"Compiler enforcement"}'
```

**Create actions for implementation:**
```bash
# Action 1
python3 .coordinator/coordinator_cli.py add-action \
  --action "Create development checklist with error handling section" \
  --owner "Tech Lead" \
  --priority HIGH

# Action 2
python3 .coordinator/coordinator_cli.py add-action \
  --action "Update AGENTS.md to require local integration test execution" \
  --owner "Documentation Agent" \
  --priority MEDIUM

# Action 3
python3 .coordinator/coordinator_cli.py add-action \
  --action "Enable nullable reference type analyzers in .editorconfig" \
  --owner "Developer" \
  --priority HIGH
```

---

## 10. Managing Pending Actions

**Scenario:** Track and manage pending actions across agents.

**Create multiple actions:**
```bash
# Action for Developer
python3 .coordinator/coordinator_cli.py add-action \
  --action "Refactor BetRepository to use async/await pattern" \
  --owner "Developer" \
  --priority MEDIUM \
  --due-by "2025-10-10T17:00:00Z"

# Action for QA
python3 .coordinator/coordinator_cli.py add-action \
  --action "Add performance tests for event producer" \
  --owner "Tester / QA" \
  --priority LOW \
  --due-by "2025-10-15T17:00:00Z"

# Action for DevOps
python3 .coordinator/coordinator_cli.py add-action \
  --action "Set up message broker monitoring in production" \
  --owner "DevOps Engineer" \
  --priority CRITICAL \
  --due-by "2025-10-08T12:00:00Z"
```

**Query all pending actions (Python API):**
```python
from coordinator_memory import CoordinatorMemory
from datetime import datetime

memory = CoordinatorMemory()
state = memory.get_state()

# Filter pending actions
pending = [a for a in state.pending_actions if a.status == "PENDING"]

# Sort by due date
pending.sort(key=lambda a: a.due_by if a.due_by else datetime.max)

for action in pending:
    print(f"[{action.priority}] {action.owner}: {action.action}")
    if action.due_by:
        print(f"  Due: {action.due_by}")
```

**Output:**
```
[CRITICAL] DevOps Engineer: Set up message broker monitoring in production
  Due: 2025-10-08T12:00:00Z
[MEDIUM] Developer: Refactor BetRepository to use async/await pattern
  Due: 2025-10-10T17:00:00Z
[LOW] Tester / QA: Add performance tests for event producer
  Due: 2025-10-15T17:00:00Z
```

**Complete an action:**
```bash
python3 .coordinator/coordinator_cli.py complete-action \
  --action-id "c9d0e1f2-a3b4-4c5d-6e7f-8a9b0c1d2e3f" \
  --outcome "Message broker monitoring configured in Grafana dashboard"
```

**Query overdue actions (Python API):**
```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
overdue = [a for a in state.pending_actions 
           if a.status == "PENDING" and a.due_by and a.due_by < now]

if overdue:
    print(f"⚠️ {len(overdue)} overdue actions:")
    for action in overdue:
        print(f"  {action.owner}: {action.action} (due {action.due_by})")
```

---

## Tips and Best Practices

### For Coordinator

1. **Always validate state before transitions**
   ```bash
   python3 .coordinator/coordinator_cli.py status
   ```

2. **Record rejection reasons clearly**
   - Include required path
   - Explain why transition is invalid
   - Guide agent to correct request

3. **Track decisions immediately**
   - Record as Tech Lead makes them
   - Include context and alternatives
   - Link to affected features

4. **Monitor active blockers**
   ```bash
   python3 .coordinator/coordinator_cli.py list-blockers
   ```

5. **Review metrics regularly**
   ```bash
   python3 .coordinator/coordinator_cli.py metrics
   ```

### For Agents (requesting via @coordinator)

1. **Include complete context in handover requests**
   - Clear reason
   - Work products created
   - Artifacts to review

2. **Report blockers immediately**
   - Don't wait until handover
   - Include impact assessment
   - Suggest resolution if known

3. **Update status when starting/completing work**
   - Keeps coordinator aware
   - Enables concurrent work tracking

4. **Request correct state transitions**
   - Check valid transitions in AGENTS.md
   - Don't try to skip states

### CLI Best Practices

1. **Use ISO 8601 timestamps**
   ```bash
   --since 2025-10-07T00:00:00Z
   ```

2. **Parse JSON output programmatically**
   ```bash
   python3 .coordinator/coordinator_cli.py status | jq '.currentState'
   ```

3. **Check exit codes**
   ```bash
   if python3 .coordinator/coordinator_cli.py handover ...; then
     echo "Handover approved"
   else
     echo "Handover rejected"
   fi
   ```

4. **Use comma-separated lists**
   ```bash
   --criteria "Criterion 1,Criterion 2,Criterion 3"
   --artifacts "file1.cs,file2.cs"
   ```

5. **Quote strings with spaces**
   ```bash
   --context "This is a longer context with spaces"
   ```
