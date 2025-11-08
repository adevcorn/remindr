"""
Unit tests for Coordinator Memory System.

Tests cover:
- State transitions (valid and invalid)
- Handover logging
- Agent context management
- Blockers and pending actions
- Metrics calculation
- File locking
- JSON serialization/deserialization
"""

import json
import tempfile
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest  # type: ignore

from coordinator_memory import (
    CoordinatorMemory,
    WorkflowState,
    AgentStatus,
    Priority,
    ActionStatus,
    BlockerStatus,
    HandoverStatus,
    StateTransitions
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_state_file():
    """Create a temporary state file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    Path(temp_path).unlink(missing_ok=True)
    Path(temp_path).with_suffix('.lock').unlink(missing_ok=True)


@pytest.fixture
def memory(temp_state_file):
    """Create a CoordinatorMemory instance with temp file."""
    return CoordinatorMemory(temp_state_file)


# ============================================================================
# State Transition Tests
# ============================================================================

def test_initial_state(memory):
    """Test that initial state is INIT."""
    assert memory.get_current_state() == WorkflowState.INIT


def test_valid_transition(memory):
    """Test a valid state transition."""
    result = memory.transition_state(
        WorkflowState.INIT,
        WorkflowState.REQUIREMENTS,
        "Starting requirements phase"
    )
    
    assert result.success is True
    assert result.transition is not None
    assert result.transition.from_state == WorkflowState.INIT.value
    assert result.transition.to_state == WorkflowState.REQUIREMENTS.value
    assert memory.get_current_state() == WorkflowState.REQUIREMENTS


def test_invalid_transition(memory):
    """Test an invalid state transition."""
    result = memory.transition_state(
        WorkflowState.INIT,
        WorkflowState.DEVELOPMENT,
        "Attempting to skip requirements"
    )
    
    assert result.success is False
    assert result.error_message is not None
    assert "Invalid transition" in result.error_message
    assert memory.get_current_state() == WorkflowState.INIT


def test_transition_from_wrong_current_state(memory):
    """Test transition when current state doesn't match from_state."""
    result = memory.transition_state(
        WorkflowState.REQUIREMENTS,
        WorkflowState.ARCHITECTURE,
        "Attempting transition from wrong state"
    )
    
    assert result.success is False
    assert "Current state is INIT" in result.error_message


def test_state_transitions_matrix():
    """Test the state transitions matrix."""
    # Valid transitions
    assert StateTransitions.is_valid_transition(WorkflowState.INIT, WorkflowState.REQUIREMENTS)
    assert StateTransitions.is_valid_transition(WorkflowState.REQUIREMENTS, WorkflowState.ARCHITECTURE)
    assert StateTransitions.is_valid_transition(WorkflowState.REVIEW, WorkflowState.DEVELOPMENT)  # Rework
    
    # Invalid transitions
    assert not StateTransitions.is_valid_transition(WorkflowState.INIT, WorkflowState.DEVELOPMENT)
    assert not StateTransitions.is_valid_transition(WorkflowState.COMPLETE, WorkflowState.INIT)


def test_get_valid_targets():
    """Test getting valid target states."""
    targets = StateTransitions.get_valid_targets(WorkflowState.REVIEW)
    assert WorkflowState.TESTING in targets
    assert WorkflowState.DEVELOPMENT in targets
    assert WorkflowState.ARCHITECTURE in targets
    assert len(targets) == 3


# ============================================================================
# Feature Management Tests
# ============================================================================

def test_set_current_feature(memory):
    """Test setting the current feature."""
    memory.set_current_feature(
        "Add user authentication",
        "feature/auth",
        "Implement OAuth2 authentication",
        ["Users can log in", "Tokens are secure"],
        ["https://github.com/org/repo/issues/123"]
    )
    
    feature = memory.get_current_feature()
    assert feature is not None
    assert feature.name == "Add user authentication"
    assert feature.branch == "feature/auth"
    assert len(feature.acceptance_criteria) == 2
    assert len(feature.linked_issues) == 1


def test_clear_current_feature(memory):
    """Test clearing the current feature."""
    memory.set_current_feature("Test", "feature/test", "Test feature")
    assert memory.get_current_feature() is not None
    
    memory.clear_current_feature()
    assert memory.get_current_feature() is None


# ============================================================================
# Handover Tests
# ============================================================================

def test_valid_handover(memory):
    """Test a valid handover between agents."""
    result = memory.add_handover(
        "Requirements Engineer",
        "Tech Lead",
        WorkflowState.INIT,
        WorkflowState.REQUIREMENTS,
        "Requirements gathering complete",
        "3 user stories defined",
        ["requirements.md"]
    )
    
    assert result.success is True
    assert result.handover is not None
    assert result.handover.status == HandoverStatus.APPROVED.value
    assert memory.get_current_state() == WorkflowState.REQUIREMENTS


def test_invalid_handover(memory):
    """Test an invalid handover (bad state transition)."""
    result = memory.add_handover(
        "Requirements Engineer",
        "Developer",
        WorkflowState.INIT,
        WorkflowState.DEVELOPMENT,
        "Attempting invalid handover"
    )
    
    assert result.success is False
    assert result.handover is not None
    assert result.handover.status == HandoverStatus.REJECTED.value
    assert result.handover.rejection_reason is not None
    assert memory.get_current_state() == WorkflowState.INIT


def test_handover_updates_agent_context(memory):
    """Test that handover updates agent contexts."""
    memory.add_handover(
        "Requirements Engineer",
        "Tech Lead",
        WorkflowState.INIT,
        WorkflowState.REQUIREMENTS,
        "Handover complete"
    )
    
    from_context = memory.get_agent_context("Requirements Engineer")
    to_context = memory.get_agent_context("Tech Lead")
    
    assert from_context is not None
    assert from_context.status == AgentStatus.IDLE.value
    assert "Tech Lead" in from_context.last_output
    
    assert to_context is not None
    assert to_context.status == AgentStatus.WORKING.value
    assert "Requirements Engineer" in to_context.last_output


def test_get_handover_history(memory):
    """Test querying handover history."""
    # Create multiple handovers
    memory.add_handover("Coordinator", "Requirements Engineer", WorkflowState.INIT, WorkflowState.REQUIREMENTS, "Start")
    memory.transition_state(WorkflowState.REQUIREMENTS, WorkflowState.ARCHITECTURE, "Continue")
    memory.add_handover("Requirements Engineer", "Tech Lead", WorkflowState.ARCHITECTURE, WorkflowState.DEVELOPMENT, "Design done")
    
    # Get all handovers
    all_handovers = memory.get_handover_history()
    assert len(all_handovers) >= 2
    
    # Filter by agent
    req_eng_handovers = memory.get_handover_history(agent="Requirements Engineer")
    assert len(req_eng_handovers) >= 1
    
    # Filter by status
    approved = memory.get_handover_history(status=HandoverStatus.APPROVED)
    assert all(h.status == HandoverStatus.APPROVED.value for h in approved)


# ============================================================================
# Agent Context Tests
# ============================================================================

def test_update_agent_context(memory):
    """Test updating agent context."""
    memory.update_agent_context(
        "Developer",
        AgentStatus.WORKING,
        "Implementing feature X",
        ["src/feature.py", "tests/test_feature.py"]
    )
    
    context = memory.get_agent_context("Developer")
    assert context is not None
    assert context.status == AgentStatus.WORKING.value
    assert context.last_output == "Implementing feature X"
    assert len(context.work_products) == 2


def test_agent_context_partial_update(memory):
    """Test that partial updates preserve existing values."""
    memory.update_agent_context("Developer", AgentStatus.WORKING, "Initial work")
    memory.update_agent_context("Developer", output="Updated work")
    
    context = memory.get_agent_context("Developer")
    assert context.status == AgentStatus.WORKING.value
    assert context.last_output == "Updated work"


# ============================================================================
# Blocker Tests
# ============================================================================

def test_add_blocker(memory):
    """Test adding a blocker."""
    blocker = memory.add_blocker(
        "Database migration failing",
        Priority.HIGH,
        WorkflowState.DEVELOPMENT.value,
        "Developer"
    )
    
    assert blocker.id is not None
    assert blocker.status == BlockerStatus.OPEN.value
    assert blocker.impact == Priority.HIGH.value


def test_resolve_blocker(memory):
    """Test resolving a blocker."""
    blocker = memory.add_blocker("Test blocker", Priority.MEDIUM)
    
    success = memory.resolve_blocker(blocker.id, "Fixed by updating config")
    assert success is True
    
    # Verify it's no longer in active blockers
    active = memory.get_active_blockers()
    assert not any(b.id == blocker.id for b in active)


def test_get_active_blockers_sorted(memory):
    """Test that active blockers are sorted by impact."""
    memory.add_blocker("Low priority", Priority.LOW)
    memory.add_blocker("Critical issue", Priority.CRITICAL)
    memory.add_blocker("Medium issue", Priority.MEDIUM)
    
    active = memory.get_active_blockers()
    assert len(active) == 3
    assert active[0].impact == Priority.CRITICAL.value
    assert active[1].impact == Priority.MEDIUM.value
    assert active[2].impact == Priority.LOW.value


# ============================================================================
# Pending Action Tests
# ============================================================================

def test_add_pending_action(memory):
    """Test adding a pending action."""
    action = memory.add_pending_action(
        "Update documentation",
        "Documentation Agent",
        Priority.MEDIUM
    )
    
    assert action.id is not None
    assert action.status == ActionStatus.PENDING.value
    assert action.owner == "Documentation Agent"


def test_complete_pending_action(memory):
    """Test completing a pending action."""
    action = memory.add_pending_action("Test action", "Developer")
    
    success = memory.complete_pending_action(action.id)
    assert success is True


def test_complete_nonexistent_action(memory):
    """Test completing a non-existent action."""
    success = memory.complete_pending_action("nonexistent-id")
    assert success is False


# ============================================================================
# Decision Recording Tests
# ============================================================================

def test_record_decision(memory):
    """Test recording a decision."""
    decision = memory.record_decision(
        "Use PostgreSQL for data storage",
        "Best fit for our relational data model",
        "Positive performance impact",
        {"alternatives": ["MongoDB", "MySQL"]}
    )
    
    assert decision.id is not None
    assert decision.decision == "Use PostgreSQL for data storage"
    assert decision.context is not None


def test_get_decisions_filtered_by_date(memory):
    """Test filtering decisions by date."""
    memory.record_decision("Decision 1", "Rationale 1")
    time.sleep(0.1)
    
    cutoff = datetime.now(timezone.utc)
    time.sleep(0.1)
    
    memory.record_decision("Decision 2", "Rationale 2")
    
    recent = memory.get_decisions(since=cutoff)
    assert len(recent) >= 1
    assert all(datetime.fromisoformat(d.timestamp) >= cutoff for d in recent)


# ============================================================================
# Metrics Tests
# ============================================================================

def test_metrics_total_handovers(memory):
    """Test that metrics track total handovers."""
    initial_metrics = memory.get_metrics()
    initial_count = initial_metrics.total_handovers
    
    memory.add_handover("A", "B", WorkflowState.INIT, WorkflowState.REQUIREMENTS, "Test")
    
    updated_metrics = memory.get_metrics()
    assert updated_metrics.total_handovers == initial_count + 1


def test_metrics_rejected_handovers(memory):
    """Test that metrics track rejected handovers."""
    initial_metrics = memory.get_metrics()
    initial_rejected = initial_metrics.rejected_handovers
    
    memory.add_handover("A", "B", WorkflowState.INIT, WorkflowState.DEVELOPMENT, "Invalid")
    
    updated_metrics = memory.get_metrics()
    assert updated_metrics.rejected_handovers == initial_rejected + 1


def test_metrics_rework_patterns(memory):
    """Test that rework patterns are tracked."""
    # Progress forward
    memory.transition_state(WorkflowState.INIT, WorkflowState.REQUIREMENTS, "Start")
    memory.transition_state(WorkflowState.REQUIREMENTS, WorkflowState.ARCHITECTURE, "Continue")
    memory.transition_state(WorkflowState.ARCHITECTURE, WorkflowState.DEVELOPMENT, "Continue")
    
    # Backward transition (rework)
    memory.transition_state(WorkflowState.DEVELOPMENT, WorkflowState.ARCHITECTURE, "Need design changes")
    
    metrics = memory.get_metrics()
    assert len(metrics.rework_patterns) > 0
    
    rework = metrics.rework_patterns[0]
    assert rework.from_state == WorkflowState.DEVELOPMENT.value
    assert rework.to_state == WorkflowState.ARCHITECTURE.value
    assert rework.count >= 1


def test_metrics_total_features(memory):
    """Test that completing a feature increments total_features."""
    initial_metrics = memory.get_metrics()
    initial_features = initial_metrics.total_features
    
    # Progress through states to COMPLETE
    states = [
        WorkflowState.INIT,
        WorkflowState.REQUIREMENTS,
        WorkflowState.ARCHITECTURE,
        WorkflowState.DEVELOPMENT,
        WorkflowState.CI_CD,
        WorkflowState.REVIEW,
        WorkflowState.TESTING,
        WorkflowState.PERFORMANCE,
        WorkflowState.VALIDATION,
        WorkflowState.COMPLETE
    ]
    
    for i in range(len(states) - 1):
        memory.transition_state(states[i], states[i + 1], f"Step {i}")
    
    final_metrics = memory.get_metrics()
    assert final_metrics.total_features == initial_features + 1


# ============================================================================
# Project Knowledge Tests
# ============================================================================

def test_add_convention(memory):
    """Test adding a convention to project knowledge."""
    memory.add_convention(
        "Naming",
        "Use PascalCase for classes",
        ["MyClass", "UserController"],
        0.95
    )
    
    state = memory.get_state()
    assert len(state.project_knowledge.conventions) > 0
    
    convention = state.project_knowledge.conventions[-1]
    assert convention.category == "Naming"
    assert convention.confidence == 0.95


def test_add_common_decision(memory):
    """Test adding a common decision pattern."""
    memory.add_common_decision(
        "Need async I/O",
        "Use asyncio",
        "Best supported in Python ecosystem"
    )
    
    state = memory.get_state()
    assert len(state.project_knowledge.common_decisions) > 0
    
    decision = state.project_knowledge.common_decisions[-1]
    assert decision.situation == "Need async I/O"


# ============================================================================
# Persistence Tests
# ============================================================================

def test_state_persistence(temp_state_file):
    """Test that state persists across instances."""
    # Create first instance and modify state
    memory1 = CoordinatorMemory(temp_state_file)
    memory1.transition_state(WorkflowState.INIT, WorkflowState.REQUIREMENTS, "Test")
    memory1.set_current_feature("Test Feature", "feature/test", "Test")
    
    # Create second instance and verify state
    memory2 = CoordinatorMemory(temp_state_file)
    assert memory2.get_current_state() == WorkflowState.REQUIREMENTS
    feature = memory2.get_current_feature()
    assert feature is not None
    assert feature.name == "Test Feature"


def test_json_serialization(memory):
    """Test JSON serialization uses camelCase."""
    memory.transition_state(WorkflowState.INIT, WorkflowState.REQUIREMENTS, "Test")
    memory.set_current_feature("Test", "feature/test", "Description")
    
    # Read raw JSON
    with open(memory._state_file_path, 'r') as f:
        data = json.load(f)
    
    # Verify camelCase keys
    assert "currentState" in data
    assert "currentFeature" in data
    assert "stateHistory" in data
    assert "handoverLog" in data
    
    # Verify nested camelCase
    if data["currentFeature"]:
        assert "startedAt" in data["currentFeature"]
        assert "acceptanceCriteria" in data["currentFeature"]


def test_corrupted_state_creates_backup(temp_state_file):
    """Test that corrupted state file is backed up."""
    # Write invalid JSON
    with open(temp_state_file, 'w') as f:
        f.write("{ invalid json }")
    
    # Should create backup and return initial state
    memory = CoordinatorMemory(temp_state_file)
    assert memory.get_current_state() == WorkflowState.INIT
    
    # Verify backup was created
    backup_files = list(Path(temp_state_file).parent.glob("*.backup.*"))
    assert len(backup_files) > 0


# ============================================================================
# Concurrency Tests
# ============================================================================

def test_concurrent_writes(temp_state_file):
    """Test that file locking prevents race conditions."""
    memory = CoordinatorMemory(temp_state_file)
    errors = []
    
    def add_decision(idx):
        try:
            memory.record_decision(f"Decision {idx}", f"Rationale {idx}")
        except Exception as e:
            errors.append(e)
    
    # Create multiple threads writing concurrently
    threads = [threading.Thread(target=add_decision, args=(i,)) for i in range(10)]
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    # Verify no errors and all decisions recorded
    assert len(errors) == 0
    decisions = memory.get_decisions()
    assert len(decisions) >= 10


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_state_history(memory):
    """Test handling of empty state history."""
    assert len(memory.get_state().state_history) == 0


def test_nonexistent_agent_context(memory):
    """Test getting context for non-existent agent."""
    context = memory.get_agent_context("NonexistentAgent")
    assert context is None


def test_resolve_nonexistent_blocker(memory):
    """Test resolving non-existent blocker."""
    success = memory.resolve_blocker("nonexistent-id", "Resolution")
    assert success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
