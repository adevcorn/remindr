# Troubleshooting Guide

## Quick Diagnosis

```bash
# Check if system is operational
python3 .coordinator/coordinator_cli.py status

# If that fails, try:
ls -la .coordinator/coordinator-state.json
python3 -m json.tool .coordinator/coordinator-state.json
```

**Common Exit Codes:**
- `0` - Success
- `1` - Error (check stderr for details)

---

## Common Issues

### 1. File Lock Conflicts

#### Symptoms
- CLI command hangs indefinitely
- Error message: `Unable to acquire lock`
- Timeout after 10 seconds waiting for lock

#### Causes
- **Concurrent coordinator instances** - Multiple processes trying to access state file simultaneously
- **Stale lock files** - Process killed with `kill -9` leaving orphaned lock
- **Hung process** - Coordinator process frozen but holding lock

#### Solutions

**Check for active locks:**
```bash
# List lock files
ls -la .coordinator/*.lock

# Example output:
# -rw-r--r-- 1 user staff 0 Oct  7 14:30 coordinator-state.json.lock
```

**Identify blocking process:**
```bash
# Find which process holds the lock (Linux/macOS)
lsof .coordinator/coordinator-state.json.lock

# Example output:
# COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
# python3 12345 user   3w   REG   1,4      0  123456 .coordinator/coordinator-state.json.lock
```

**Force unlock (safe when no coordinator running):**
```bash
# Verify no coordinator processes running
ps aux | grep coordinator_cli.py

# If none found, remove lock file
rm .coordinator/coordinator-state.json.lock

# Retry operation
python3 .coordinator/coordinator_cli.py status
```

**Wait and retry:**
```bash
# Locks auto-release after 10 seconds
# Just retry the command
python3 .coordinator/coordinator_cli.py status
```

#### Prevention

1. **Run single coordinator instance** - Only one coordinator agent should be active
2. **Use proper shutdown** - Always let CLI commands complete naturally (don't use `kill -9`)
3. **Monitor hung processes** - Set up process monitoring to detect frozen coordinators
4. **Implement timeout handling** - CLI will timeout after 10 seconds and release lock

**Example: Check before starting coordinator:**
```bash
#!/bin/bash
# coordinator-check.sh

if pgrep -f "coordinator_cli.py" > /dev/null; then
    echo "ERROR: Coordinator already running"
    exit 1
fi

# Safe to start coordinator operations
python3 .coordinator/coordinator_cli.py status
```

---

### 2. JSON Corruption

#### Symptoms
- `JSONDecodeError: Expecting value: line 1 column 1`
- `Failed to parse coordinator-state.json`
- `Invalid control character at: line 45 column 3`
- Schema validation errors

#### Causes
- **Partial writes** - Process killed during state save
- **Manual edits** - Direct editing of JSON file with syntax errors
- **Disk full** - No space left on device during write
- **Power failure** - System crash during file write
- **Text encoding issues** - Non-UTF8 characters in JSON

#### Solutions

**Check for backups:**
```bash
# List available backups (created automatically on corruption detection)
ls -lah .coordinator/*.backup.*

# Example output:
# -rw-r--r-- 1 user staff 45K Oct  7 14:25 coordinator-state.json.backup.20251007142500
# -rw-r--r-- 1 user staff 46K Oct  7 14:30 coordinator-state.json.backup.20251007143000
```

**Restore from backup:**
```bash
# Choose most recent backup
BACKUP=$(ls -t .coordinator/coordinator-state.json.backup.* | head -1)

# Create safety copy of corrupted file
cp .coordinator/coordinator-state.json .coordinator/corrupted-$(date +%Y%m%d%H%M%S).json

# Restore backup
cp "$BACKUP" .coordinator/coordinator-state.json

# Verify restoration
python3 .coordinator/coordinator_cli.py status
```

**Expected output after successful restore:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming",
    "description": "Add event streaming",
    "startedAt": "2025-10-07T10:00:00Z",
    "acceptanceCriteria": ["Events published successfully"]
  }
}
```

**Validate JSON syntax:**
```bash
# Check if file is valid JSON
python3 -c "import json; json.load(open('.coordinator/coordinator-state.json'))"

# If valid: No output (exit code 0)
# If invalid: JSONDecodeError with line/column details
```

**Reset to clean INIT state (LAST RESORT):**
```bash
# DANGER: This loses ALL workflow history!
# Only use if no backup available and restoration critical

# Backup corrupted file first
mv .coordinator/coordinator-state.json .coordinator/corrupted-$(date +%Y%m%d%H%M%S).json

# Delete state file (will auto-create clean INIT state)
python3 .coordinator/coordinator_cli.py status

# Output will show fresh INIT state:
# {
#   "currentState": "INIT",
#   "currentFeature": null
# }
```

**Recover data from corrupted file (advanced):**
```python
# recover.py - Attempt to salvage data from corrupted JSON
import json
import re

with open('.coordinator/coordinator-state.json', 'r', errors='ignore') as f:
    content = f.read()
    
# Try to find valid JSON fragments
# Extract state history
matches = re.findall(r'"stateHistory":\s*\[(.*?)\]', content, re.DOTALL)
if matches:
    print("Found state history fragment")
    
# Extract handover log
matches = re.findall(r'"handoverLog":\s*\[(.*?)\]', content, re.DOTALL)
if matches:
    print("Found handover log fragment")
```

#### Prevention

1. **Never edit JSON manually** - Always use CLI commands
2. **Monitor disk space** - Alert when disk < 10% free
3. **Use atomic writes** - CLI already does this (temp file + rename)
4. **Regular backups** - Automatic backups on every load prevent data loss
5. **Validate after changes** - Always check status after operations

**Example: Pre-commit hook to validate state file:**
```bash
#!/bin/bash
# .git/hooks/pre-commit

if [ -f .coordinator/coordinator-state.json ]; then
    python3 -c "import json; json.load(open('.coordinator/coordinator-state.json'))" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR: coordinator-state.json is invalid JSON"
        exit 1
    fi
fi
```

---

### 3. Invalid State Transitions

#### Symptoms
- `Invalid transition from DEVELOPMENT to TESTING`
- Handover rejected with error message
- CLI returns exit code 1 with error in stderr

#### Causes
- **Skipped states** - Attempting to jump multiple states (e.g., DEVELOPMENT → TESTING)
- **Wrong current state** - State machine out of sync with expectations
- **Misunderstanding workflow** - Not following required state sequence

#### Solutions

**Check current workflow state:**
```bash
python3 .coordinator/coordinator_cli.py status
```

**Expected output:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming"
  }
}
```

**Understand valid transitions:**
```
Current state: DEVELOPMENT
Valid targets: CI_CD, ARCHITECTURE
Invalid: TESTING, REVIEW, VALIDATION (must go through CI_CD and REVIEW first)
```

**Review state transition matrix:**

| From State      | Valid Targets                          |
|-----------------|----------------------------------------|
| INIT            | REQUIREMENTS                           |
| REQUIREMENTS    | ARCHITECTURE                           |
| ARCHITECTURE    | DEVELOPMENT, REQUIREMENTS              |
| DEVELOPMENT     | CI_CD, ARCHITECTURE                    |
| CI_CD           | REVIEW, DEVELOPMENT                    |
| REVIEW          | TESTING, DEVELOPMENT, ARCHITECTURE     |
| TESTING         | PERFORMANCE, DEVELOPMENT               |
| PERFORMANCE     | VALIDATION, DEVELOPMENT                |
| VALIDATION      | COMPLETE, REQUIREMENTS                 |
| COMPLETE        | *(terminal state)*                     |

**Correct invalid transition:**
```bash
# WRONG: Skip states
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "Tester / QA" \
  --from-state DEVELOPMENT \
  --to-state TESTING \
  --reason "Tests needed"

# Output:
# {
#   "success": false,
#   "error": "Invalid transition from DEVELOPMENT to TESTING. Valid targets: CI_CD, ARCHITECTURE"
# }

# CORRECT: Follow proper sequence
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready for build"

# Output:
# {
#   "success": true,
#   "handover": {
#     "id": "550e8400-e29b-41d4-a716-446655440000",
#     "status": "APPROVED"
#   }
# }
```

#### Common Invalid Paths and Corrections

**❌ REQUIREMENTS → DEVELOPMENT**
```
Invalid: Skips ARCHITECTURE
Correct: REQUIREMENTS → ARCHITECTURE → DEVELOPMENT
Reason: Must design before implementing
```

**❌ DEVELOPMENT → TESTING**
```
Invalid: Skips CI_CD and REVIEW
Correct: DEVELOPMENT → CI_CD → REVIEW → TESTING
Reason: Must build and review before testing
```

**❌ REVIEW → VALIDATION**
```
Invalid: Skips TESTING and PERFORMANCE
Correct: REVIEW → TESTING → PERFORMANCE → VALIDATION
Reason: Must verify functionality and performance
```

**✅ Feedback Loops (Valid Backward Transitions)**
```
Valid: REVIEW → DEVELOPMENT (code issues found)
Valid: TESTING → DEVELOPMENT (test failures)
Valid: CI_CD → DEVELOPMENT (build failures)
Valid: ARCHITECTURE → REQUIREMENTS (clarification needed)
Valid: VALIDATION → REQUIREMENTS (acceptance criteria not met)
```

#### Prevention

1. **Understand workflow** - Review state machine before requesting handovers
2. **Check current state** - Always verify current state before transition
3. **Follow sequences** - Respect the forward path through states
4. **Use feedback loops** - Go back when issues found, not skip ahead

---

### 4. Permission Errors

#### Symptoms
- `Permission denied: .coordinator/coordinator-state.json`
- `OSError: [Errno 13] Permission denied`
- Cannot create lock file

#### Causes
- **Wrong file ownership** - File owned by different user
- **Restrictive permissions** - File mode too restrictive (e.g., 400)
- **Directory permissions** - Cannot write to `.coordinator` directory
- **SELinux/AppArmor** - Security policies blocking access

#### Solutions

**Check file permissions:**
```bash
ls -la .coordinator/coordinator-state.json

# Expected output (user-readable/writable, group-readable):
# -rw-r--r-- 1 user staff 45678 Oct  7 14:30 coordinator-state.json

# Bad examples:
# -r--r--r-- (read-only, cannot write)
# -rw------- (only owner can access, breaks shared access)
# -rw-r--r-- root root (wrong owner)
```

**Fix file permissions:**
```bash
# Make file writable by owner
chmod 644 .coordinator/coordinator-state.json

# If working in team, allow group write:
chmod 664 .coordinator/coordinator-state.json

# Verify
ls -la .coordinator/coordinator-state.json
# Should show: -rw-rw-r--
```

**Fix directory permissions:**
```bash
# Ensure directory is writable
chmod 755 .coordinator/

# Verify
ls -lad .coordinator/
# Should show: drwxr-xr-x
```

**Fix file ownership:**
```bash
# Change owner to current user
sudo chown $(whoami):$(id -gn) .coordinator/coordinator-state.json

# Or for entire directory:
sudo chown -R $(whoami):$(id -gn) .coordinator/
```

**Check for SELinux issues (Linux):**
```bash
# Check SELinux status
getenforce
# If enforcing, check file context
ls -Z .coordinator/coordinator-state.json

# Fix context if needed
chcon -t user_home_t .coordinator/coordinator-state.json
```

**Test after fixes:**
```bash
# Try write test
echo "test" > .coordinator/test-write.txt && rm .coordinator/test-write.txt
echo "Write test successful"

# Try CLI
python3 .coordinator/coordinator_cli.py status
```

#### Prevention

1. **Consistent user** - Always run coordinator as same user
2. **Proper umask** - Set `umask 022` for correct default permissions
3. **Team access** - Use group permissions (664) for shared repositories
4. **Avoid sudo** - Don't run CLI with sudo unless necessary

**Example: Set up correct permissions:**
```bash
# In repository root
chmod 755 .coordinator/
chmod 644 .coordinator/coordinator-state.json
chmod 644 .coordinator/*.py
chmod +x .coordinator/coordinator_cli.py
```

---

### 5. Stale Agent Context

#### Symptoms
- Agent context shows wrong status (e.g., WORKING when actually IDLE)
- Last active timestamp is old
- Work products list is empty or outdated
- Agent appears active but isn't responding

#### Causes
- **Context not updated after handover** - Handover recorded but agent context not updated
- **Agent crash** - Agent died without updating status
- **Missed status updates** - Agent forgot to update context
- **Manual state manipulation** - Direct JSON edits bypassed context updates

#### Solutions

**Check current agent context:**
```bash
python3 .coordinator/coordinator_cli.py status

# Or query specific agent (via Python):
python3 -c "
from coordinator_memory import CoordinatorMemory
memory = CoordinatorMemory()
context = memory.get_agent_context('Developer')
print(f'Status: {context.status}')
print(f'Last active: {context.last_active}')
print(f'Last output: {context.last_output}')
"
```

**Expected output:**
```
Status: WORKING
Last active: 2025-10-07T14:30:00Z
Last output: Implementing event producer
```

**Stale context example:**
```
Status: WORKING
Last active: 2025-10-06T09:00:00Z  # 29 hours ago!
Last output: Starting implementation  # Never updated
```

**Manually update stale context:**
```bash
# Reset agent to IDLE
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status IDLE \
  --output "Context reset due to stale state"

# Output:
# {
#   "success": true,
#   "agent": "Developer",
#   "context": {
#     "status": "IDLE",
#     "lastActive": "2025-10-07T14:35:00Z",
#     "lastOutput": "Context reset due to stale state",
#     "workProducts": []
#   }
# }
```

**Clear work products:**
```bash
# Update with empty work products
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --work-products ""
```

**Batch reset all agents (Python):**
```python
from coordinator_memory import CoordinatorMemory, AgentStatus

memory = CoordinatorMemory()
agents = [
    "Developer", "DevOps Engineer", "Reviewer",
    "Tester / QA", "Performance Engineer", "Documentation Agent"
]

for agent in agents:
    memory.update_agent_context(
        agent_name=agent,
        status=AgentStatus.IDLE,
        output="Context reset during cleanup",
        work_products=[]
    )
    print(f"Reset {agent}")
```

#### Prevention

1. **Always update context after handover** - CLI handover command does this automatically
2. **Update status at work start/end** - Agents should update when starting and completing work
3. **Use handover command** - Don't manually transition state (bypasses context updates)
4. **Monitor active agents** - Check for agents "WORKING" for >24 hours

**Example: Proper agent workflow:**
```bash
# Agent starts work (update context)
python3 .coordinator/coordinator_cli.py update-agent \
  --agent "Developer" \
  --status WORKING \
  --output "Starting event producer implementation"

# Agent completes work (handover updates context automatically)
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Implementation complete" \
  --work-products "src/messaging/producers/event_producer.py"
```

---

### 6. Missing Handovers in Log

#### Symptoms
- Handover log is empty or incomplete
- State transitions occurred but no handover records
- Gaps in audit trail
- Cannot find who performed transition

#### Causes
- **Direct state transition** - Used `transition` command instead of `handover`
- **Manual state edits** - Edited JSON directly
- **Lost data** - Corruption or rollback lost handover records

#### Solutions

**Check handover log:**
```bash
# List all handovers
python3 .coordinator/coordinator_cli.py list-handovers

# Output (empty):
# {
#   "count": 0,
#   "handovers": []
# }
```

**Check state history (transitions without handovers):**
```python
# list-state-history.py
from coordinator_memory import CoordinatorMemory

memory = CoordinatorMemory()
state = memory.get_state()

print(f"State transitions: {len(state.state_history)}")
print(f"Handovers: {len(state.handover_log)}")

# Show transitions
for t in state.state_history[-5:]:
    print(f"{t.timestamp}: {t.from_state} → {t.to_state}")
    print(f"  Reason: {t.reason}")
```

**Reconstruct from git history:**
```bash
# Find commits during timeframe
git log --since="2025-10-07" --until="2025-10-08" --pretty=format:"%h %ai %s" --author="Developer"

# Example output:
# a1b2c3d 2025-10-07 14:30:00 feat: Add event producer
# b2c3d4e 2025-10-07 15:45:00 test: Add integration tests

# Manually add handover for reconstruction:
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Reconstructed from git commit a1b2c3d" \
  --artifacts "src/messaging/producers/event_producer.py"
```

**Check for backup with complete handover log:**
```bash
# List backups
ls -la .coordinator/*.backup.*

# Inspect backup handover count
python3 -c "
import json
import sys
backup = sys.argv[1]
with open(backup) as f:
    state = json.load(f)
    print(f\"Handovers in backup: {len(state.get('handoverLog', []))}\")
" .coordinator/coordinator-state.json.backup.20251007143000
```

#### Prevention

1. **Always use `handover` command** - Don't use `transition` directly (it doesn't create handover record)
2. **Never edit JSON manually** - All changes via CLI
3. **Verify handover created** - Check CLI output for handover ID
4. **Regular audits** - Periodically verify handover log is complete

**Correct workflow:**
```bash
# ❌ WRONG: Direct transition (no handover record)
python3 .coordinator/coordinator_cli.py transition \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready"

# ✅ CORRECT: Use handover (creates both transition and handover record)
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready"
```

---

### 7. Metrics Calculation Errors

#### Symptoms
- Average cycle time shows NaN or 0.0
- State cycle times are all zeros
- Agent utilization is empty
- Rework patterns not updating

#### Causes
- **Missing timestamps** - State transitions lack timestamps
- **Incomplete state history** - Not enough data points for calculations
- **No completed features** - Metrics calculated on feature completion
- **Clock skew** - System time changed during workflow

#### Solutions

**Check current metrics:**
```bash
python3 .coordinator/coordinator_cli.py metrics
```

**Expected output:**
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
      "reason": "Code issues"
    }
  ],
  "agentUtilization": {
    "Developer": 8.5,
    "Tester / QA": 3.2
  }
}
```

**Problem output:**
```json
{
  "totalFeatures": 0,
  "totalHandovers": 0,
  "rejectedHandovers": 0,
  "averageCycleTime": 0.0,
  "stateCycleTimes": {
    "DEVELOPMENT": 0.0,
    "REVIEW": 0.0
  },
  "reworkPatterns": [],
  "agentUtilization": {}
}
```

**Validate state history:**
```python
# validate-metrics.py
from coordinator_memory import CoordinatorMemory
from datetime import datetime

memory = CoordinatorMemory()
state = memory.get_state()

print(f"Total transitions: {len(state.state_history)}")
print(f"Total handovers: {len(state.handover_log)}")

# Check for missing timestamps
for i, t in enumerate(state.state_history):
    if not t.timestamp:
        print(f"ERROR: Transition {i} missing timestamp")
    else:
        try:
            datetime.fromisoformat(t.timestamp)
        except ValueError:
            print(f"ERROR: Transition {i} has invalid timestamp: {t.timestamp}")

# Check for completed features
completed = [t for t in state.state_history if t.to_state == "COMPLETE"]
print(f"Completed features: {len(completed)}")
```

**Recalculate metrics manually (Python):**
```python
from coordinator_memory import CoordinatorMemory, WorkflowState
from datetime import datetime

memory = CoordinatorMemory()
state = memory.get_state()

# Force metric recalculation by completing a transition
# (Metrics update automatically on transition)
if state.current_state == WorkflowState.VALIDATION.value:
    # Transition to COMPLETE to trigger metric calculation
    result = memory.transition_state(
        from_state=WorkflowState.VALIDATION,
        to_state=WorkflowState.COMPLETE,
        reason="Force metrics recalculation"
    )
    
    if result.success:
        metrics = memory.get_metrics()
        print(f"Total features: {metrics.total_features}")
```

#### Prevention

1. **Complete features** - Metrics calculate when transitioning to COMPLETE
2. **Ensure timestamps** - All transitions must have valid timestamps (automatic)
3. **Don't skip states** - Follow full workflow for accurate cycle time data
4. **Regular checks** - Monitor metrics periodically to catch issues early

---

## Debugging Tips

### Enable Debug Logging

Add temporary debug output to coordinator operations:

```bash
# Set environment variable
export COORDINATOR_DEBUG=1

# Run command with verbose output
python3 .coordinator/coordinator_cli.py status 2>&1 | tee coordinator-debug.log
```

**Add debug logging to Python module:**
```python
# Add to top of coordinator_memory.py temporarily
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
```

**Example debug output:**
```
2025-10-07 14:30:00 [DEBUG] Loading state from .coordinator/coordinator-state.json
2025-10-07 14:30:00 [DEBUG] Acquiring file lock
2025-10-07 14:30:00 [DEBUG] Lock acquired
2025-10-07 14:30:00 [DEBUG] State loaded successfully
2025-10-07 14:30:00 [DEBUG] Current state: DEVELOPMENT
```

### Inspect State File

**Pretty-print JSON:**
```bash
# Format with indentation
python3 -m json.tool .coordinator/coordinator-state.json

# Save formatted version
python3 -m json.tool .coordinator/coordinator-state.json > state-formatted.json
```

**Query specific fields:**
```bash
# Get current state
python3 -c "
import json
with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
    print(f\"Current state: {state['currentState']}\")
    print(f\"Feature: {state.get('currentFeature', {}).get('name', 'None')}\")
"

# Count handovers
python3 -c "
import json
with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
    print(f\"Total handovers: {len(state.get('handoverLog', []))}\")
    approved = sum(1 for h in state.get('handoverLog', []) if h['status'] == 'APPROVED')
    print(f\"Approved: {approved}\")
    rejected = sum(1 for h in state.get('handoverLog', []) if h['status'] == 'REJECTED')
    print(f\"Rejected: {rejected}\")
"
```

**Check file size:**
```bash
ls -lah .coordinator/coordinator-state.json

# If > 10 MB, consider archiving
du -h .coordinator/coordinator-state.json
```

### Verify File Integrity

**Check JSON syntax:**
```bash
# Validate JSON
python3 -c "import json; json.load(open('.coordinator/coordinator-state.json'))"

# If valid: No output (exit code 0)
# If invalid: Error with line/column number
```

**Validate schema (if jsonschema installed):**
```bash
pip install jsonschema

python3 -c "
import json
import jsonschema

with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
with open('.coordinator/memory-schema.json') as f:
    schema = json.load(f)

try:
    jsonschema.validate(state, schema)
    print('✅ State is valid against schema')
except jsonschema.ValidationError as e:
    print(f'❌ Schema validation failed: {e.message}')
    print(f'Path: {list(e.path)}')
"
```

**Check for binary corruption:**
```bash
# Ensure file is text (UTF-8)
file .coordinator/coordinator-state.json
# Expected: ASCII text or UTF-8 Unicode text

# Check for null bytes (corruption indicator)
grep -c $'\x00' .coordinator/coordinator-state.json
# Should be: 0
```

### Query Recent Activity

**Last 5 handovers:**
```bash
python3 -c "
from coordinator_memory import CoordinatorMemory

memory = CoordinatorMemory()
handovers = memory.get_handover_history()[:5]

for h in handovers:
    print(f\"{h.timestamp}: {h.from_agent} → {h.to_agent}\")
    print(f\"  {h.from_state} → {h.to_state}: {h.status}\")
"
```

**Recent state transitions:**
```bash
python3 -c "
from coordinator_memory import CoordinatorMemory
from datetime import datetime, timedelta, timezone

memory = CoordinatorMemory()
state = memory.get_state()

# Last 24 hours
cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
recent = [t for t in state.state_history if t.timestamp >= cutoff]

print(f\"Transitions in last 24 hours: {len(recent)}\")
for t in recent:
    print(f\"{t.timestamp}: {t.from_state} → {t.to_state}\")
"
```

**Active blockers:**
```bash
python3 .coordinator/coordinator_cli.py list-blockers | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f\"Active blockers: {data['count']}\")
for b in data['blockers']:
    print(f\"  [{b['impact']}] {b['description']}\")
"
```

### Compare with Backup

**Diff state files:**
```bash
# Compare with backup
BACKUP=$(ls -t .coordinator/coordinator-state.json.backup.* | head -1)

# Show differences
diff -u "$BACKUP" .coordinator/coordinator-state.json

# Or use JSON-aware diff
python3 -c "
import json
import sys

with open('$BACKUP') as f:
    backup = json.load(f)
with open('.coordinator/coordinator-state.json') as f:
    current = json.load(f)

if backup == current:
    print('Files are identical')
else:
    print(f\"Current state: {current['currentState']}\")
    print(f\"Backup state: {backup['currentState']}\")
    print(f\"Current handovers: {len(current['handoverLog'])}\")
    print(f\"Backup handovers: {len(backup['handoverLog'])}\")
"
```

---

## Recovery Procedures

### Reset to Clean State

**⚠️ WARNING: This loses ALL workflow history, handovers, and metrics!**

**When to use:**
- Corrupted state with no valid backup
- Testing/development reset
- Irrecoverable schema mismatch

**Steps:**

```bash
# 1. Backup everything first
mkdir -p .coordinator/recovery-$(date +%Y%m%d%H%M%S)
cp .coordinator/coordinator-state.json .coordinator/recovery-*/
cp .coordinator/*.backup.* .coordinator/recovery-*/ 2>/dev/null

# 2. List what will be lost
python3 -c "
import json
with open('.coordinator/coordinator-state.json') as f:
    state = json.load(f)
    print(f\"State: {state['currentState']}\")
    print(f\"Feature: {state.get('currentFeature', {}).get('name', 'None')}\")
    print(f\"Handovers: {len(state.get('handoverLog', []))}\")
    print(f\"Metrics: {state.get('metrics', {}).get('totalFeatures', 0)} features completed\")
"

# 3. Confirm (manually type 'yes')
read -p "Type 'yes' to confirm reset: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Reset cancelled"
    exit 1
fi

# 4. Delete state file (will auto-create clean INIT state)
rm .coordinator/coordinator-state.json
rm .coordinator/coordinator-state.json.lock 2>/dev/null

# 5. Verify clean state
python3 .coordinator/coordinator_cli.py status

# Expected output:
# {
#   "currentState": "INIT",
#   "currentFeature": null
# }
```

**What gets lost:**
- Current workflow state
- Current feature details
- All state transition history
- All handover records
- All agent context
- All blockers and pending actions
- All decisions
- All workflow metrics
- All project knowledge

**What is NOT lost:**
- Backed up files in recovery directory
- Git history (code changes are safe)
- Actual code and tests

**After reset:**
```bash
# Start fresh workflow
python3 .coordinator/coordinator_cli.py set-feature \
  --name "new-feature" \
  --branch "feature/new-feature" \
  --description "Fresh start" \
  --criteria "Criteria 1,Criteria 2"

# Transition to REQUIREMENTS
python3 .coordinator/coordinator_cli.py transition \
  --from-state INIT \
  --to-state REQUIREMENTS \
  --reason "Starting new feature"
```

### Restore from Backup

**When to use:**
- Recent corruption detected
- Accidental state deletion
- Need to rollback bad transition

**Steps:**

```bash
# 1. List available backups (newest first)
ls -lt .coordinator/*.backup.*

# Example output:
# -rw-r--r-- 1 user staff 45678 Oct  7 14:30 coordinator-state.json.backup.20251007143000
# -rw-r--r-- 1 user staff 45234 Oct  7 14:25 coordinator-state.json.backup.20251007142500

# 2. Inspect backup content
BACKUP=".coordinator/coordinator-state.json.backup.20251007143000"

python3 -c "
import json
with open('$BACKUP') as f:
    state = json.load(f)
    print(f\"State: {state['currentState']}\")
    feature = state.get('currentFeature')
    if feature:
        print(f\"Feature: {feature['name']}\")
        print(f\"Started: {feature['startedAt']}\")
    print(f\"Handovers: {len(state['handoverLog'])}\")
    if state['handoverLog']:
        last = state['handoverLog'][-1]
        print(f\"Last handover: {last['timestamp']}\")
        print(f\"  {last['fromAgent']} → {last['toAgent']}\")
"

# 3. Create safety backup of current state
cp .coordinator/coordinator-state.json \
   .coordinator/before-restore-$(date +%Y%m%d%H%M%S).json

# 4. Restore backup
cp "$BACKUP" .coordinator/coordinator-state.json

# 5. Verify restoration
python3 .coordinator/coordinator_cli.py status

# 6. Validate integrity
python3 -c "import json; json.load(open('.coordinator/coordinator-state.json'))"
echo "✅ State restored successfully"
```

**Validation checklist after restore:**
- [ ] State file is valid JSON
- [ ] Current state matches expectations
- [ ] Feature details are correct
- [ ] Handover count is reasonable
- [ ] No critical data missing

**If restore fails:**
```bash
# Try older backup
OLDER_BACKUP=".coordinator/coordinator-state.json.backup.20251007142500"
cp "$OLDER_BACKUP" .coordinator/coordinator-state.json
python3 .coordinator/coordinator_cli.py status

# If all backups fail, reset to clean state (see above)
```

### Manual State Repair

**⚠️ EMERGENCY ONLY: Last resort when CLI cannot load state**

**When to use:**
- All backups are corrupted
- Schema changes broke compatibility
- Need to salvage partial data

**Procedure:**

```python
# repair-state.py - Manual state repair script
import json
from datetime import datetime, timezone

# 1. Load corrupted state (ignoring errors where possible)
try:
    with open('.coordinator/coordinator-state.json', 'r', errors='ignore') as f:
        content = f.read()
        # Try to parse
        state = json.loads(content)
except json.JSONDecodeError as e:
    print(f"Parse error at line {e.lineno}, column {e.colno}")
    print("Attempting partial recovery...")
    
    # Try to extract valid fragments
    # (This is very manual - inspect file and extract what you can)
    state = {
        "currentState": "DEVELOPMENT",  # Set manually
        "currentFeature": None,
        "stateHistory": [],
        "handoverLog": [],
        "agentContext": {},
        "pendingActions": [],
        "blockers": [],
        "decisions": [],
        "metrics": {
            "totalFeatures": 0,
            "totalHandovers": 0,
            "rejectedHandovers": 0,
            "averageCycleTime": 0.0,
            "stateCycleTimes": {},
            "reworkPatterns": [],
            "agentUtilization": {}
        },
        "projectKnowledge": {
            "conventions": [],
            "commonDecisions": [],
            "successPatterns": [],
            "antiPatterns": []
        }
    }

# 2. Validate required fields
required_fields = [
    "currentState",
    "metrics",
    "projectKnowledge"
]

for field in required_fields:
    if field not in state:
        print(f"ERROR: Missing required field: {field}")
        state[field] = {} if field != "currentState" else "INIT"

# 3. Fix agent context structure
if "agentContext" not in state or not isinstance(state["agentContext"], dict):
    state["agentContext"] = {}

# Add standard agents if missing
agents = [
    "Coordinator", "Requirements Engineer", "Tech Lead",
    "Developer", "DevOps Engineer", "Reviewer",
    "Tester / QA", "Performance Engineer", "Documentation Agent"
]

for agent in agents:
    if agent not in state["agentContext"]:
        state["agentContext"][agent] = {
            "status": "IDLE",
            "lastActive": None,
            "lastOutput": None,
            "workProducts": [],
            "metadata": {}
        }

# 4. Validate handover log
if "handoverLog" in state:
    valid_handovers = []
    for h in state["handoverLog"]:
        # Ensure required fields
        if all(k in h for k in ["id", "timestamp", "fromAgent", "toAgent", "status"]):
            valid_handovers.append(h)
    state["handoverLog"] = valid_handovers

# 5. Save repaired state
backup_path = f".coordinator/pre-repair-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
with open(backup_path, 'w') as f:
    json.dump(state, f, indent=2)
print(f"Backup saved to: {backup_path}")

# 6. Write repaired state
with open('.coordinator/coordinator-state.json', 'w') as f:
    json.dump(state, f, indent=2)
print("Repaired state written")

# 7. Validate with CLI
import subprocess
result = subprocess.run(
    ["python3", ".coordinator/coordinator_cli.py", "status"],
    capture_output=True
)
if result.returncode == 0:
    print("✅ Repair successful - CLI can load state")
else:
    print(f"❌ Repair failed - CLI error: {result.stderr.decode()}")
```

**Run repair script:**
```bash
python3 repair-state.py

# If successful, verify
python3 .coordinator/coordinator_cli.py status
```

**Post-repair validation:**
```bash
# 1. Check metrics
python3 .coordinator/coordinator_cli.py metrics

# 2. List handovers
python3 .coordinator/coordinator_cli.py list-handovers

# 3. Try a transition
python3 .coordinator/coordinator_cli.py transition \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Test transition after repair"
```

---

## Prevention Best Practices

### 1. Always Use CLI, Never Edit JSON Manually

**✅ CORRECT:**
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready"
```

**❌ WRONG:**
```bash
# DON'T DO THIS
vim .coordinator/coordinator-state.json  # Manual edit = corruption risk
```

**Why:**
- CLI ensures atomic writes (temp file + rename)
- CLI validates state transitions
- CLI maintains referential integrity
- CLI updates metrics automatically
- Manual edits bypass all safety checks

### 2. Run Single Coordinator Instance

**Check for running coordinators:**
```bash
# Before starting coordinator
pgrep -f "coordinator_cli.py" && echo "Coordinator already running!" || echo "Safe to start"
```

**Use process guard:**
```bash
#!/bin/bash
# start-coordinator.sh

LOCKFILE="/tmp/coordinator.lock"

# Try to acquire lock
if ! mkdir "$LOCKFILE" 2>/dev/null; then
    echo "ERROR: Coordinator already running (lock exists: $LOCKFILE)"
    exit 1
fi

# Ensure cleanup on exit
trap "rm -rf $LOCKFILE" EXIT

# Run coordinator operations
python3 .coordinator/coordinator_cli.py "$@"
```

### 3. Complete Handovers for Every Transition

**Always use handover command (not transition):**
```bash
# ✅ Creates both transition record AND handover audit log
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "DevOps Engineer" \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready"

# ❌ Only creates transition (missing audit trail)
python3 .coordinator/coordinator_cli.py transition \
  --from-state DEVELOPMENT \
  --to-state CI_CD \
  --reason "Code ready"
```

### 4. Monitor Disk Space

**Set up disk space monitoring:**
```bash
# check-disk-space.sh
THRESHOLD=10  # Percentage

USAGE=$(df -h .coordinator | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$USAGE" -gt "$THRESHOLD" ]; then
    echo "WARNING: Disk usage at ${USAGE}%"
    
    # Clean up old backups (keep last 10)
    cd .coordinator
    ls -t coordinator-state.json.backup.* | tail -n +11 | xargs rm -f
fi
```

**Add to cron:**
```bash
# Check every hour
0 * * * * /path/to/check-disk-space.sh
```

### 5. Regular State File Backups

**Automated backup script:**
```bash
#!/bin/bash
# backup-coordinator-state.sh

BACKUP_DIR=".coordinator/backups"
mkdir -p "$BACKUP_DIR"

# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
cp .coordinator/coordinator-state.json "$BACKUP_DIR/state-$TIMESTAMP.json"

# Compress old backups (>1 day old)
find "$BACKUP_DIR" -name "*.json" -mtime +1 -exec gzip {} \;

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.json.gz" -mtime +30 -delete

echo "Backup created: $BACKUP_DIR/state-$TIMESTAMP.json"
```

**Add to cron:**
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup-coordinator-state.sh
```

### 6. Validate After Major Changes

**Post-change validation:**
```bash
# After any state change, verify
python3 .coordinator/coordinator_cli.py status

# Check for errors
if [ $? -ne 0 ]; then
    echo "ERROR: State validation failed"
    # Restore from backup
    BACKUP=$(ls -t .coordinator/*.backup.* | head -1)
    cp "$BACKUP" .coordinator/coordinator-state.json
fi
```

**Validation checklist:**
- [ ] `status` command succeeds
- [ ] `metrics` command returns valid data
- [ ] `list-handovers` shows recent handovers
- [ ] State file is < 10 MB
- [ ] No stale lock files

---

## Getting Help

### Check Logs

**Coordinator doesn't have centralized logs, but you can create them:**

```bash
# Redirect stderr to log file
python3 .coordinator/coordinator_cli.py status 2> coordinator-error.log

# If error occurred, check log
cat coordinator-error.log
```

**Enable logging in Python module:**
```python
# Add to coordinator_memory.py
import logging

logging.basicConfig(
    filename='.coordinator/coordinator.log',
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)
```

### Run Test Suite

**Comprehensive test validation:**
```bash
# Run all tests (35 tests)
python3 -m pytest .coordinator/test_coordinator_memory.py -v

# Example output (success):
# test_coordinator_memory.py::test_create_initial_state PASSED
# test_coordinator_memory.py::test_valid_transition PASSED
# test_coordinator_memory.py::test_invalid_transition PASSED
# ...
# ===================== 35 passed in 2.34s ======================
```

**Run specific test categories:**
```bash
# Test state transitions
python3 -m pytest .coordinator/test_coordinator_memory.py -v -k "transition"

# Test handovers
python3 -m pytest .coordinator/test_coordinator_memory.py -v -k "handover"

# Test file operations
python3 -m pytest .coordinator/test_coordinator_memory.py -v -k "file"
```

**Test output interpretation:**
- `PASSED` - Test succeeded
- `FAILED` - Test failed (indicates bug)
- `ERROR` - Test couldn't run (setup issue)
- `SKIPPED` - Test intentionally skipped

**If tests fail:**
```bash
# Get detailed failure information
python3 -m pytest .coordinator/test_coordinator_memory.py -v --tb=long

# This shows full error traces
```

### Validate State

**Quick validation:**
```bash
python3 .coordinator/coordinator_cli.py status
python3 .coordinator/coordinator_cli.py metrics
```

**Deep validation:**
```python
# validate-deep.py
from coordinator_memory import CoordinatorMemory
import sys

memory = CoordinatorMemory()
state = memory.get_state()

errors = []

# Check state integrity
if not state.current_state:
    errors.append("Missing current_state")

if state.current_state not in [
    "INIT", "REQUIREMENTS", "ARCHITECTURE", "DEVELOPMENT",
    "CI_CD", "REVIEW", "TESTING", "PERFORMANCE", "VALIDATION", "COMPLETE"
]:
    errors.append(f"Invalid current_state: {state.current_state}")

# Check feature
if state.current_feature:
    if not state.current_feature.name:
        errors.append("Feature missing name")
    if not state.current_feature.branch:
        errors.append("Feature missing branch")

# Check handovers have IDs
for i, h in enumerate(state.handover_log):
    if not h.id:
        errors.append(f"Handover {i} missing ID")

# Check agents
expected_agents = [
    "Coordinator", "Requirements Engineer", "Tech Lead",
    "Developer", "DevOps Engineer", "Reviewer",
    "Tester / QA", "Performance Engineer", "Documentation Agent"
]

for agent in expected_agents:
    if agent not in state.agent_context:
        errors.append(f"Missing agent context: {agent}")

if errors:
    print("❌ Validation failed:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✅ State validation passed")
```

### Report Issues

**When reporting coordinator issues, include:**

1. **Error message** (exact text)
2. **Command that failed** (full command line)
3. **Current state** (output of `status` command)
4. **Recent handovers** (last 5 handovers)
5. **State file size** (`ls -lah .coordinator/coordinator-state.json`)
6. **Python version** (`python3 --version`)
7. **OS** (`uname -a`)

**Example issue report:**

```markdown
## Coordinator Error Report

**Error:**
```
{
  "success": false,
  "error": "Invalid transition from DEVELOPMENT to TESTING"
}
```

**Command:**
```bash
python3 .coordinator/coordinator_cli.py handover \
  --from-agent "Developer" \
  --to-agent "Tester / QA" \
  --from-state DEVELOPMENT \
  --to-state TESTING \
  --reason "Tests needed"
```

**Current State:**
```json
{
  "currentState": "DEVELOPMENT",
  "currentFeature": {
    "name": "event-streaming",
    "branch": "feature/event-streaming"
  }
}
```

**Recent Handovers:**
```json
{
  "count": 3,
  "handovers": [
    {
      "timestamp": "2025-10-07T14:00:00Z",
      "fromAgent": "Requirements Engineer",
      "toAgent": "Tech Lead",
      "fromState": "REQUIREMENTS",
      "toState": "ARCHITECTURE"
    }
  ]
}
```

**Environment:**
- State file size: 45K
- Python version: 3.11.5
- OS: macOS 14.0 (Darwin 23.0.0)
```

**Attach files:**
- `.coordinator/coordinator-state.json` (sanitize if needed)
- Error logs (if any)
- Backup files (if corruption occurred)

---

## Quick Reference

### Emergency Commands

```bash
# Check if coordinator operational
python3 .coordinator/coordinator_cli.py status

# Remove stale lock (NO coordinator running)
rm .coordinator/coordinator-state.json.lock

# Restore from latest backup
cp $(ls -t .coordinator/*.backup.* | head -1) .coordinator/coordinator-state.json

# Reset to clean state (LOSES ALL DATA)
rm .coordinator/coordinator-state.json && python3 .coordinator/coordinator_cli.py status

# Validate JSON syntax
python3 -c "import json; json.load(open('.coordinator/coordinator-state.json'))"
```

### Common Fixes

| Problem | Quick Fix |
|---------|-----------|
| CLI hangs | `rm .coordinator/coordinator-state.json.lock` |
| JSON corrupt | `cp .coordinator/*.backup.* .coordinator/coordinator-state.json` |
| Invalid transition | Check valid state matrix, use correct sequence |
| Permission denied | `chmod 644 .coordinator/coordinator-state.json` |
| Missing handovers | Use `handover` command, not `transition` |
| Stale agent context | `update-agent --agent "Name" --status IDLE` |
| Metrics show 0.0 | Complete a feature (transition to COMPLETE) |

### Diagnostic Commands

```bash
# System health check
python3 .coordinator/coordinator_cli.py status && echo "✅ OK" || echo "❌ FAIL"

# Recent activity
python3 .coordinator/coordinator_cli.py list-handovers --since $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%SZ)

# Active issues
python3 .coordinator/coordinator_cli.py list-blockers

# Workflow metrics
python3 .coordinator/coordinator_cli.py metrics

# File integrity
python3 -m json.tool .coordinator/coordinator-state.json > /dev/null && echo "✅ Valid JSON"
```

---

**For additional help, see:**
- `.coordinator/README.md` - Complete documentation
- `.coordinator/USAGE_EXAMPLES.md` - Example workflows
- `.coordinator/test_coordinator_memory.py` - Test suite examples
- `AGENTS.md` - Agent workflow documentation
