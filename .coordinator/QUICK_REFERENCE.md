# Coordinator Memory - Quick Reference

## Overview

Python CLI for coordinator-only workflow state management.

**Access Control:**
- ✅ **Coordinator** executes CLI commands
- ❌ **Agents** request via `@coordinator` (NO direct CLI access)
- 🔒 File locking prevents concurrent access conflicts

## File Structure

```
.coordinator/
├── coordinator_memory.py       # Core Python implementation
├── coordinator_cli.py          # CLI interface
├── coordinator-state.json      # Persistent state (auto-saved)
├── memory-schema.json          # JSON Schema definition
├── test_coordinator_memory.py  # Test suite (35 tests)
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation
├── USAGE_EXAMPLES.md           # Workflow scenarios
├── QUICK_REFERENCE.md          # This file
└── TROUBLESHOOTING.md          # Common issues
```

## Installation

```bash
# Install dependencies
pip install -r .coordinator/requirements.txt

# Verify installation
python3 .coordinator/coordinator_cli.py status
```

## Workflow States

```
INIT → REQUIREMENTS → ARCHITECTURE → DEVELOPMENT → CI_CD → REVIEW → TESTING → PERFORMANCE → VALIDATION → COMPLETE
```

**Feedback Loops:**
- ARCHITECTURE → REQUIREMENTS (clarify requirements)
- DEVELOPMENT → ARCHITECTURE (design changes)
- CI_CD → DEVELOPMENT (build failures)
- REVIEW → DEVELOPMENT, ARCHITECTURE (code/design issues)
- TESTING → DEVELOPMENT (test failures)
- PERFORMANCE → DEVELOPMENT (performance issues)
- VALIDATION → REQUIREMENTS (criteria not met)

## CLI Commands by Category

### State Management

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
    "acceptanceCriteria": ["Events published successfully", "Retry policy configured"]
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

**Options:**
- `--from-state` (required): Current state
- `--to-state` (required): Target state
- `--reason` (required): Transition reason
- `--context` (optional): Additional context

### Feature Management

#### `set-feature` - Set Current Feature
```bash
python3 .coordinator/coordinator_cli.py set-feature \
  --name "event-streaming" \
  --branch "feature/event-streaming" \
  --description "Add event streaming" \
  --criteria "Events published successfully,Retry policy,Tests passing" \
  --issues "#123,#124"
```

**Options:**
- `--name` (required): Feature name
- `--branch` (required): Git branch
- `--description` (required): Feature description
- `--criteria` (optional): Comma-separated acceptance criteria
- `--issues` (optional): Comma-separated issue IDs

#### `clear-feature` - Clear Current Feature
```bash
python3 .coordinator/coordinator_cli.py clear-feature
```

### Handover Management

#### `handover` - Record Agent Handover
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready for build" \
  --context "Implemented event producers" \
  --artifacts "src/messaging/producers/event_producer.py"
```

**Options:**
- `--from-agent` (required): Agent handing over
- `--to-agent` (required): Agent receiving
- `--from-state` (required): Current state
- `--to-state` (required): Target state
- `--reason` (required): Handover reason
- `--context` (optional): Additional context
- `--artifacts` (optional): Comma-separated file paths

#### `list-handovers` - Query Handover History
```bash
# All handovers
python3 .coordinator/coordinator_cli.py list-handovers

# Filter by agent
python3 .coordinator/coordinator_cli.py list-handovers --agent "Developer"

# Filter by status
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED

# Filter by date
python3 .coordinator/coordinator_cli.py list-handovers --since 2025-10-07T00:00:00Z

# Combined filters
python3 .coordinator/coordinator_cli.py list-handovers \
  --agent "Developer" \
  --status APPROVED \
  --since 2025-10-07T00:00:00Z
```

**Options:**
- `--agent` (optional): Filter by agent name
- `--status` (optional): `APPROVED` or `REJECTED`
- `--since` (optional): ISO 8601 timestamp

### Agent Context

#### `update-agent` - Update Agent Status
```bash
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Implementing event producer" \
  --work-products "src/messaging/event_producer.py,src/events/bet_created_event.py"
```

**Options:**
- `--agent` (required): Agent name
- `--status` (optional): `IDLE`, `WORKING`, `BLOCKED`, `COMPLETE`
- `--output` (optional): Last output message
- `--work-products` (optional): Comma-separated file paths

### Blocker Management

#### `add-blocker` - Create Blocker
```bash
python3 .coordinator/coordinator_cli.py add-blocker \
  --description "Message broker not available" \
  --impact HIGH \
  --affected-state TESTING \
  --affected-agent "Tester / QA"
```

**Options:**
- `--description` (required): Blocker description
- `--impact` (required): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `--affected-state` (optional): Affected workflow state
- `--affected-agent` (optional): Affected agent name

#### `resolve-blocker` - Resolve Blocker
```bash
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id "550e8400-e29b-41d4-a716-446655440000" \
  --resolution "Message broker configured on localhost:9092"
```

**Options:**
- `--blocker-id` (required): Blocker UUID
- `--resolution` (required): Resolution description

#### `list-blockers` - Show Active Blockers
```bash
python3 .coordinator/coordinator_cli.py list-blockers
```

### Action Management

#### `add-action` - Create Pending Action
```bash
python3 .coordinator/coordinator_cli.py add-action \
  --action "Add integration tests for event producer" \
  --owner "Tester / QA" \
  --priority HIGH \
  --due-by "2025-10-08T12:00:00Z"
```

**Options:**
- `--action` (required): Action description
- `--owner` (required): Responsible agent
- `--priority` (optional): `LOW`, `MEDIUM` (default), `HIGH`, `CRITICAL`
- `--due-by` (optional): ISO 8601 timestamp

#### `complete-action` - Complete Action
```bash
python3 .coordinator/coordinator_cli.py complete-action \
  --action-id "650e8400-e29b-41d4-a716-446655440001" \
  --outcome "Integration tests added and passing"
```

**Options:**
- `--action-id` (required): Action UUID
- `--outcome` (optional): Outcome description

### Decision Recording

#### `record-decision` - Record Decision
```bash
python3 .coordinator/coordinator_cli.py record-decision \
  --decision "Use at-least-once delivery for events" \
  --rationale "Balance between reliability and complexity" \
  --impact "Consumers must handle duplicate events" \
  --context '{"alternative":"exactly-once","tradeoff":"complexity vs reliability"}'
```

**Options:**
- `--decision` (required): Decision made
- `--rationale` (required): Decision rationale
- `--impact` (optional): Expected impact
- `--context` (optional): JSON context object

#### `list-decisions` - Query Decisions
```bash
# All decisions
python3 .coordinator/coordinator_cli.py list-decisions

# Since date
python3 .coordinator/coordinator_cli.py list-decisions --since 2025-10-01T00:00:00Z
```

**Options:**
- `--since` (optional): ISO 8601 timestamp

### Metrics and Analysis

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

## Common Workflows

### 1. Start Feature
```bash
# Set feature
python3 .coordinator/coordinator_cli.py set-feature \
  --name "feature-name" \
  --branch "feature/branch-name" \
  --description "Feature description"

# Transition from INIT
python3 .coordinator/coordinator_cli.py transition \
  --from-state INIT \
  --to-state REQUIREMENTS \
  --reason "Feature defined"
```

### 2. Agent Handover
```bash
# Agent requests: "@coordinator handover from DEVELOPMENT to CI_CD, reason: Code ready"

# Coordinator executes:
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready for build"
```

### 3. Handle Blocker
```bash
# Add blocker
python3 .coordinator/coordinator_cli.py add-blocker \
  --description "Message broker not available" \
  --impact HIGH \
  --affected-state DEVELOPMENT

# Update agent status
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status BLOCKED \
  --output "Waiting for message broker"

# Resolve blocker
python3 .coordinator/coordinator_cli.py resolve-blocker \
  --blocker-id "<id>" \
  --resolution "Message broker configured"

# Resume work
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Continuing implementation"
```

### 4. Complete Feature
```bash
# Final validation
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Requirements Engineer" \
  --to-agent "Coordinator" \
  --from-state VALIDATION \
  --to-state COMPLETE \
  --reason "PR merged to main"

# Clear feature
python3 .coordinator/coordinator_cli.py clear-feature
```

### 5. Analyze Workflow
```bash
# Check current status
python3 .coordinator/coordinator_cli.py status

# View metrics
python3 .coordinator/coordinator_cli.py metrics

# Find rejected handovers
python3 .coordinator/coordinator_cli.py list-handovers --status REJECTED

# Check active blockers
python3 .coordinator/coordinator_cli.py list-blockers
```

## Valid State Transitions

| From         | To                                  | Reason                 |
|--------------|-------------------------------------|------------------------|
| INIT         | REQUIREMENTS                        | Start feature          |
| REQUIREMENTS | ARCHITECTURE                        | Requirements approved  |
| ARCHITECTURE | DEVELOPMENT, REQUIREMENTS           | Implement or clarify   |
| DEVELOPMENT  | CI_CD, ARCHITECTURE                 | Build or redesign      |
| CI_CD        | REVIEW, DEVELOPMENT                 | Review or fix build    |
| REVIEW       | TESTING, DEVELOPMENT, ARCHITECTURE  | Test, fix, or redesign |
| TESTING      | PERFORMANCE, DEVELOPMENT            | Optimize or fix tests  |
| PERFORMANCE  | VALIDATION, DEVELOPMENT             | Validate or optimize   |
| VALIDATION   | COMPLETE, REQUIREMENTS              | Finish or redefine     |
| COMPLETE     | *(terminal state)*                  | Feature merged         |

## Agent Roles

- **Coordinator** - Orchestrates workflow, validates transitions (CLI executor)
- **Requirements Engineer** - Defines features, validates acceptance
- **Tech Lead** - Architecture decisions, design reviews
- **Developer** - Code implementation
- **DevOps Engineer** - CI/CD, builds, deployments
- **Reviewer** - Code review, quality checks
- **Tester / QA** - Test creation, execution
- **Performance Engineer** - Performance optimization
- **Documentation Agent** - Documentation updates

## Enums and Values

### WorkflowState
`INIT`, `REQUIREMENTS`, `ARCHITECTURE`, `DEVELOPMENT`, `CI_CD`, `REVIEW`, `TESTING`, `PERFORMANCE`, `VALIDATION`, `COMPLETE`

### AgentStatus
`IDLE`, `WORKING`, `BLOCKED`, `COMPLETE`

### Priority
`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`

### HandoverStatus
`APPROVED`, `REJECTED`

## Output Format

All commands output JSON to stdout (success) or stderr (error).

**Success Example:**
```json
{
  "success": true,
  "transition": {
    "fromState": "DEVELOPMENT",
    "toState": "CI_CD",
    "timestamp": "2025-10-07T14:30:00Z"
  }
}
```

**Error Example:**
```json
{
  "success": false,
  "error": "Invalid transition: DEVELOPMENT → TESTING. Required path: DEVELOPMENT → CI_CD → REVIEW → TESTING"
}
```

**Exit Codes:**
- `0` - Success
- `1` - Error

## Python API (Advanced)

For programmatic access:

```python
from coordinator_memory import (
    CoordinatorMemory,
    WorkflowState,
    AgentStatus,
    Priority,
    HandoverStatus
)

# Initialize
memory = CoordinatorMemory()

# Get current state
current = memory.get_current_state()

# Transition state
result = memory.transition_state(
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Feature complete",
    context="Added event producers"
)

# Record handover
handover = memory.add_handover(
    from_agent="Developer",
    to_agent="DevOps Engineer",
    from_state=WorkflowState.DEVELOPMENT,
    to_state=WorkflowState.CI_CD,
    reason="Code ready",
    artifacts=["src/messaging/event_producer.py"]
)

# Update agent context
memory.update_agent_context(
    agent_name="Developer",
    status=AgentStatus.WORKING,
    last_output="Implementing feature"
)

# Get metrics
metrics = memory.get_metrics()
```

## Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Invalid transition: X → Y` | Invalid state transition | Check valid transitions table |
| `Failed to parse coordinator-state.json` | JSON corruption | Restore from `.backup.*` file |
| `Permission denied` | File permissions | `chmod 644 coordinator-state.json` |
| `Failed to acquire lock` | Concurrent access | Wait or remove stale `.lock` file |
| `Blocker not found` | Invalid blocker ID | Use `list-blockers` to find correct ID |
| `Action not found` | Invalid action ID | Check action ID from `add-action` output |
| `Agent not found` | Invalid agent name | Use exact agent name with spaces |

## Best Practices

1. **Always validate state** before transitions
   ```bash
   python3 .coordinator/coordinator_cli.py status
   ```

2. **Check handover result** for approval/rejection
   ```bash
   if python3 .coordinator/coordinator_cli.py handover ...; then
     echo "Approved"
   else
     echo "Rejected"
   fi
   ```

3. **Record decisions** immediately when Tech Lead makes them
   ```bash
   python3 .coordinator/coordinator_cli.py record-decision ...
   ```

4. **Track blockers** as soon as discovered
   ```bash
   python3 .coordinator/coordinator_cli.py add-blocker ...
   ```

5. **Update agent status** when starting/completing work
   ```bash
   python3 .coordinator/coordinator_cli.py update-agent ...
   ```

6. **Monitor metrics** regularly to find bottlenecks
   ```bash
   python3 .coordinator/coordinator_cli.py metrics
   ```

7. **Use ISO 8601 timestamps** for date filters
   ```bash
   --since 2025-10-07T00:00:00Z
   ```

8. **Quote strings with spaces** in shell commands
   ```bash
   --context "This has spaces"
   ```

9. **Use comma-separated lists** for multiple values
   ```bash
   --criteria "Criterion 1,Criterion 2,Criterion 3"
   ```

10. **Parse JSON output** with `jq` for scripting
    ```bash
    python3 .coordinator/coordinator_cli.py status | jq '.currentState'
    ```

## Performance

- **File I/O**: ~1ms per operation (1MB state file)
- **Concurrency**: File locking with 10s timeout
- **Memory**: Full state loaded (<10MB typical)
- **Startup**: ~50ms cold, ~10ms warm

## Testing

```bash
# Run all tests
python3 -m pytest .coordinator/test_coordinator_memory.py -v

# Run specific test
python3 -m pytest .coordinator/test_coordinator_memory.py::test_valid_handover -v

# Run with coverage
python3 -m pytest .coordinator/test_coordinator_memory.py --cov=coordinator_memory
```

## Quick Debugging

```bash
# Check state file syntax
python3 -m json.tool .coordinator/coordinator-state.json

# List backups
ls -la .coordinator/*.backup.*

# Check file locks
ls -la .coordinator/*.lock

# Validate state manually
python3 -c "
from coordinator_memory import CoordinatorMemory
m = CoordinatorMemory()
print(f'State: {m.get_current_state().value}')
print(f'Feature: {m.get_current_feature()}')
"
```

## More Information

- **Full Documentation**: `.coordinator/README.md`
- **Workflow Examples**: `.coordinator/USAGE_EXAMPLES.md`
- **Troubleshooting**: `.coordinator/TROUBLESHOOTING.md`
- **Migration Guide**: `.coordinator/MIGRATION_GUIDE.md`
- **JSON Schema**: `.coordinator/memory-schema.json`
- **Test Suite**: `.coordinator/test_coordinator_memory.py`

## License

Part of multi-agent workflow system.
