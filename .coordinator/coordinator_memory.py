"""
Coordinator Memory System - Python Implementation

This module provides persistent state management for the multi-agent workflow.
It tracks workflow state, handovers, decisions, blockers, and metrics across
all agent interactions.

IMPORTANT: This module is intended for COORDINATOR USE ONLY.
Other agents must interact through the coordinator, not directly with this system.
"""

import json
import fcntl
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


# ============================================================================
# Enumerations
# ============================================================================

class WorkflowState(str, Enum):
    """Workflow state enumeration matching the coordinator state machine."""
    INIT = "INIT"
    REQUIREMENTS = "REQUIREMENTS"
    ARCHITECTURE = "ARCHITECTURE"
    DEVELOPMENT = "DEVELOPMENT"
    CI_CD = "CI_CD"
    REVIEW = "REVIEW"
    TESTING = "TESTING"
    PERFORMANCE = "PERFORMANCE"
    VALIDATION = "VALIDATION"
    COMPLETE = "COMPLETE"


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    IDLE = "IDLE"
    WORKING = "WORKING"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"


class Priority(str, Enum):
    """Priority levels for actions and blockers."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionStatus(str, Enum):
    """Action status enumeration."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"


class BlockerStatus(str, Enum):
    """Blocker status enumeration."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class HandoverStatus(str, Enum):
    """Handover status enumeration."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Feature:
    """Feature information for active development."""
    name: str
    branch: str
    description: str
    started_at: str
    acceptance_criteria: List[str] = field(default_factory=list)
    linked_issues: List[str] = field(default_factory=list)


@dataclass
class StateTransition:
    """State transition record."""
    from_state: str
    to_state: str
    timestamp: str
    reason: str
    approved: bool
    context: Optional[str] = None


@dataclass
class HandoverRecord:
    """Handover record between agents."""
    id: str
    timestamp: str
    from_agent: str
    to_agent: str
    from_state: str
    to_state: str
    reason: str
    status: str
    context: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None


@dataclass
class AgentContext:
    """Agent context information."""
    status: str = "IDLE"
    last_active: Optional[str] = None
    last_output: Optional[str] = None
    work_products: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PendingAction:
    """Pending action record."""
    id: str
    action: str
    owner: str
    created_at: str
    priority: str = "MEDIUM"
    status: str = "PENDING"
    due_by: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Blocker:
    """Blocker record."""
    id: str
    description: str
    impact: str
    created_at: str
    status: str = "OPEN"
    affected_state: Optional[str] = None
    affected_agent: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None


@dataclass
class ReworkPattern:
    """Rework pattern tracking."""
    from_state: str
    to_state: str
    count: int
    reason: Optional[str] = None


@dataclass
class WorkflowMetrics:
    """Workflow metrics."""
    total_features: int = 0
    total_handovers: int = 0
    rejected_handovers: int = 0
    average_cycle_time: float = 0.0
    state_cycle_times: Dict[str, float] = field(default_factory=dict)
    rework_patterns: List[ReworkPattern] = field(default_factory=list)
    agent_utilization: Dict[str, float] = field(default_factory=dict)


@dataclass
class Convention:
    """Convention pattern."""
    category: str
    pattern: str
    confidence: float
    examples: List[str] = field(default_factory=list)


@dataclass
class CommonDecision:
    """Common decision record."""
    situation: str
    decision: str
    rationale: str
    timestamp: str


@dataclass
class ProjectKnowledge:
    """Project knowledge base."""
    conventions: List[Convention] = field(default_factory=list)
    common_decisions: List[CommonDecision] = field(default_factory=list)
    success_patterns: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)


@dataclass
class DecisionRecord:
    """Coordinator decision record."""
    id: str
    timestamp: str
    decision: str
    rationale: str
    context: Optional[Dict[str, Any]] = None
    outcome: Optional[str] = None


@dataclass
class CoordinatorState:
    """Root coordinator state."""
    current_state: str
    metrics: WorkflowMetrics
    project_knowledge: ProjectKnowledge
    current_feature: Optional[Feature] = None
    state_history: List[StateTransition] = field(default_factory=list)
    handover_log: List[HandoverRecord] = field(default_factory=list)
    agent_context: Dict[str, AgentContext] = field(default_factory=dict)
    pending_actions: List[PendingAction] = field(default_factory=list)
    blockers: List[Blocker] = field(default_factory=list)
    decisions: List[DecisionRecord] = field(default_factory=list)


# ============================================================================
# State Transitions
# ============================================================================

class StateTransitions:
    """Valid state transitions matrix."""
    
    _VALID_TRANSITIONS = {
        WorkflowState.INIT: {WorkflowState.REQUIREMENTS},
        WorkflowState.REQUIREMENTS: {WorkflowState.ARCHITECTURE},
        WorkflowState.ARCHITECTURE: {WorkflowState.DEVELOPMENT, WorkflowState.REQUIREMENTS},
        WorkflowState.DEVELOPMENT: {WorkflowState.CI_CD, WorkflowState.ARCHITECTURE},
        WorkflowState.CI_CD: {WorkflowState.REVIEW, WorkflowState.DEVELOPMENT},
        WorkflowState.REVIEW: {WorkflowState.TESTING, WorkflowState.DEVELOPMENT, WorkflowState.ARCHITECTURE},
        WorkflowState.TESTING: {WorkflowState.PERFORMANCE, WorkflowState.DEVELOPMENT},
        WorkflowState.PERFORMANCE: {WorkflowState.VALIDATION, WorkflowState.DEVELOPMENT},
        WorkflowState.VALIDATION: {WorkflowState.COMPLETE, WorkflowState.REQUIREMENTS},
        WorkflowState.COMPLETE: set()
    }
    
    @classmethod
    def is_valid_transition(cls, from_state: WorkflowState, to_state: WorkflowState) -> bool:
        """Check if a state transition is valid."""
        return to_state in cls._VALID_TRANSITIONS.get(from_state, set())
    
    @classmethod
    def get_valid_targets(cls, from_state: WorkflowState) -> set:
        """Get valid target states for a given state."""
        return cls._VALID_TRANSITIONS.get(from_state, set())


# ============================================================================
# Result Types
# ============================================================================

@dataclass
class TransitionResult:
    """Result type for state transitions."""
    success: bool
    error_message: Optional[str] = None
    transition: Optional[StateTransition] = None


@dataclass
class HandoverResult:
    """Result type for handovers."""
    success: bool
    error_message: Optional[str] = None
    handover: Optional[HandoverRecord] = None


# ============================================================================
# Coordinator Memory
# ============================================================================

class CoordinatorMemory:
    """
    Coordinator memory manager for multi-agent workflow state persistence and querying.
    
    IMPORTANT: This class is intended for COORDINATOR USE ONLY.
    Other agents must not directly instantiate or use this class.
    """
    
    def __init__(self, state_file_path: Optional[str] = None):
        """
        Initialize coordinator memory.
        
        Args:
            state_file_path: Path to state file (defaults to .coordinator/coordinator-state.json)
        """
        self._state_file_path = Path(state_file_path or ".coordinator/coordinator-state.json")
        self._state: CoordinatorState = self._load_state()
    
    @contextmanager
    def _file_lock(self):
        """Context manager for file locking to prevent concurrent access."""
        lock_file = self._state_file_path.with_suffix('.lock')
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def _load_state(self) -> CoordinatorState:
        """
        Load state from JSON file.
        
        Returns:
            CoordinatorState: Loaded state or initial state if file doesn't exist
        """
        if not self._state_file_path.exists():
            return self._create_initial_state()
        
        try:
            with self._file_lock():
                with open(self._state_file_path, 'r') as f:
                    data = json.load(f)
                    return self._deserialize_state(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Backup corrupted file and create new state
            backup_path = self._state_file_path.with_suffix(
                f'.backup.{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'
            )
            self._state_file_path.rename(backup_path)
            print(f"Warning: Corrupted state file backed up to {backup_path}. Error: {e}")
            return self._create_initial_state()
    
    def _save_state(self):
        """Save current state to JSON file with atomic write."""
        self._state_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomic write: write to temp file, then rename
        temp_path = self._state_file_path.with_suffix('.tmp')
        
        with self._file_lock():
            with open(temp_path, 'w') as f:
                json.dump(self._serialize_state(self._state), f, indent=2)
            temp_path.replace(self._state_file_path)
    
    def _serialize_state(self, state: CoordinatorState) -> Dict[str, Any]:
        """Serialize state to JSON-compatible dict with camelCase keys."""
        def to_camel_case(snake_str: str) -> str:
            components = snake_str.split('_')
            return components[0] + ''.join(x.title() for x in components[1:])
        
        def should_convert_key(key: str) -> bool:
            """Check if a key should be converted to camelCase."""
            # Don't convert keys that are all uppercase (enum values like "INIT", "DEVELOPMENT")
            if key.isupper():
                return False
            # Don't convert agent names (contain spaces)
            if ' ' in key:
                return False
            # Convert snake_case field names
            return '_' in key
        
        def convert_keys(obj: Any) -> Any:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    new_key = to_camel_case(k) if should_convert_key(k) else k
                    result[new_key] = convert_keys(v)
                return result
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return convert_keys(asdict(obj))
            else:
                return obj
        
        result = convert_keys(asdict(state))
        return result  # type: ignore
    
    def _deserialize_state(self, data: Dict[str, Any]) -> CoordinatorState:
        """Deserialize JSON dict to CoordinatorState with snake_case keys."""
        def to_snake_case(camel_str: str) -> str:
            result = []
            for i, char in enumerate(camel_str):
                if char.isupper() and i > 0:
                    result.append('_')
                result.append(char.lower())
            return ''.join(result)
        
        def should_convert_key(key: str, parent_key: str = "") -> bool:
            """Check if a key should be converted from camelCase to snake_case."""
            # Don't convert keys in stateCycleTimes or agentUtilization (they should remain as-is)
            if parent_key in ("stateCycleTimes", "agentUtilization"):
                return False
            # Don't convert agent names (contain spaces)
            if ' ' in key:
                return False
            # Don't convert keys that are all uppercase (enum values)
            if key.isupper():
                return False
            # Convert camelCase field names
            return any(c.isupper() for c in key)
        
        def convert_keys(obj: Any, parent_key: str = "") -> Any:
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    new_key = to_snake_case(k) if should_convert_key(k, parent_key) else k
                    result[new_key] = convert_keys(v, k)
                return result
            elif isinstance(obj, list):
                return [convert_keys(item, parent_key) for item in obj]
            else:
                return obj
        
        data = convert_keys(data)  # type: ignore
        
        # Convert nested structures
        metrics_data = data.get('metrics', {})
        metrics = WorkflowMetrics(
            total_features=metrics_data.get('total_features', 0),
            total_handovers=metrics_data.get('total_handovers', 0),
            rejected_handovers=metrics_data.get('rejected_handovers', 0),
            average_cycle_time=metrics_data.get('average_cycle_time', 0.0),
            state_cycle_times=metrics_data.get('state_cycle_times', {}),
            rework_patterns=[
                ReworkPattern(**p) for p in metrics_data.get('rework_patterns', [])
            ],
            agent_utilization=metrics_data.get('agent_utilization', {})
        )
        
        knowledge_data = data.get('project_knowledge', {})
        project_knowledge = ProjectKnowledge(
            conventions=[Convention(**c) for c in knowledge_data.get('conventions', [])],
            common_decisions=[CommonDecision(**d) for d in knowledge_data.get('common_decisions', [])],
            success_patterns=knowledge_data.get('success_patterns', []),
            anti_patterns=knowledge_data.get('anti_patterns', [])
        )
        
        return CoordinatorState(
            current_state=data['current_state'],
            current_feature=Feature(**data['current_feature']) if data.get('current_feature') else None,
            state_history=[StateTransition(**s) for s in data.get('state_history', [])],
            handover_log=[HandoverRecord(**h) for h in data.get('handover_log', [])],
            agent_context={k: AgentContext(**v) for k, v in data.get('agent_context', {}).items()},
            pending_actions=[PendingAction(**a) for a in data.get('pending_actions', [])],
            blockers=[Blocker(**b) for b in data.get('blockers', [])],
            metrics=metrics,
            project_knowledge=project_knowledge,
            decisions=[DecisionRecord(**d) for d in data.get('decisions', [])]
        )
    
    def _create_initial_state(self) -> CoordinatorState:
        """Create initial coordinator state."""
        agents = [
            "Coordinator",
            "Requirements Engineer",
            "Tech Lead",
            "Developer",
            "DevOps Engineer",
            "Reviewer",
            "Tester / QA",
            "Performance Engineer",
            "Documentation Agent"
        ]
        
        agent_context = {
            agent: AgentContext(
                status=AgentStatus.IDLE.value,
                last_output="Coordinator initialized" if agent == "Coordinator" else None,
                last_active=datetime.now(timezone.utc).isoformat() if agent == "Coordinator" else None
            )
            for agent in agents
        }
        
        state_names = [s.value for s in WorkflowState]
        state_cycle_times = {state: 0.0 for state in state_names}
        agent_utilization = {agent: 0.0 for agent in agents}
        
        return CoordinatorState(
            current_state=WorkflowState.INIT.value,
            current_feature=None,
            state_history=[],
            handover_log=[],
            agent_context=agent_context,
            pending_actions=[],
            blockers=[],
            metrics=WorkflowMetrics(
                total_features=0,
                total_handovers=0,
                rejected_handovers=0,
                average_cycle_time=0.0,
                state_cycle_times=state_cycle_times,
                rework_patterns=[],
                agent_utilization=agent_utilization
            ),
            project_knowledge=ProjectKnowledge(),
            decisions=[]
        )
    
    # ========================================================================
    # Public API - State Management
    # ========================================================================
    
    def get_current_state(self) -> WorkflowState:
        """Get the current workflow state."""
        return WorkflowState(self._state.current_state)
    
    def get_current_feature(self) -> Optional[Feature]:
        """Get the current feature being worked on."""
        return self._state.current_feature
    
    def set_current_feature(
        self,
        name: str,
        branch: str,
        description: str,
        criteria: Optional[List[str]] = None,
        linked_issues: Optional[List[str]] = None
    ):
        """
        Set the current feature.
        
        Args:
            name: Feature name
            branch: Git branch name
            description: Feature description
            criteria: Acceptance criteria
            linked_issues: Linked issue URLs
        """
        feature = Feature(
            name=name,
            branch=branch,
            description=description,
            started_at=datetime.now(timezone.utc).isoformat(),
            acceptance_criteria=criteria or [],
            linked_issues=linked_issues or []
        )
        self._state.current_feature = feature
        self._save_state()
    
    def clear_current_feature(self):
        """Clear the current feature (when complete)."""
        self._state.current_feature = None
        self._save_state()
    
    def transition_state(
        self,
        from_state: WorkflowState,
        to_state: WorkflowState,
        reason: str,
        context: Optional[str] = None
    ) -> TransitionResult:
        """
        Validate and record a state transition.
        
        Args:
            from_state: Expected current state
            to_state: Target state
            reason: Reason for transition
            context: Optional additional context
            
        Returns:
            TransitionResult: Success status and transition record
        """
        current = WorkflowState(self._state.current_state)
        
        if current != from_state:
            return TransitionResult(
                success=False,
                error_message=f"Current state is {current.value}, expected {from_state.value}"
            )
        
        if not StateTransitions.is_valid_transition(from_state, to_state):
            valid_targets = StateTransitions.get_valid_targets(from_state)
            valid_str = ", ".join(s.value for s in valid_targets)
            return TransitionResult(
                success=False,
                error_message=f"Invalid transition from {from_state.value} to {to_state.value}. Valid targets: {valid_str}"
            )
        
        transition = StateTransition(
            from_state=from_state.value,
            to_state=to_state.value,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            context=context,
            approved=True
        )
        
        self._state.state_history.append(transition)
        self._state.current_state = to_state.value
        self._update_metrics(transition)
        self._save_state()
        
        return TransitionResult(success=True, transition=transition)
    
    # ========================================================================
    # Public API - Handovers
    # ========================================================================
    
    def add_handover(
        self,
        from_agent: str,
        to_agent: str,
        from_state: WorkflowState,
        to_state: WorkflowState,
        reason: str,
        context: Optional[str] = None,
        artifacts: Optional[List[str]] = None
    ) -> HandoverResult:
        """
        Record a handover between agents.
        
        Args:
            from_agent: Agent handing over
            to_agent: Agent receiving handover
            from_state: Current state
            to_state: Target state
            reason: Reason for handover
            context: Optional context
            artifacts: Optional list of artifact paths
            
        Returns:
            HandoverResult: Success status and handover record
        """
        current = WorkflowState(self._state.current_state)
        
        if current != from_state:
            return HandoverResult(
                success=False,
                error_message=f"Current state is {current.value}, expected {from_state.value}"
            )
        
        if not StateTransitions.is_valid_transition(from_state, to_state):
            valid_targets = StateTransitions.get_valid_targets(from_state)
            valid_str = ", ".join(s.value for s in valid_targets)
            rejection_reason = f"Invalid transition from {from_state.value} to {to_state.value}. Valid targets: {valid_str}"
            
            handover = HandoverRecord(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                from_agent=from_agent,
                to_agent=to_agent,
                from_state=from_state.value,
                to_state=to_state.value,
                reason=reason,
                context=context,
                artifacts=artifacts or [],
                status=HandoverStatus.REJECTED.value,
                rejection_reason=rejection_reason
            )
            
            self._state.handover_log.append(handover)
            self._state.metrics.rejected_handovers += 1
            self._state.metrics.total_handovers += 1
            self._save_state()
            
            return HandoverResult(
                success=False,
                error_message=rejection_reason,
                handover=handover
            )
        
        # Valid transition - approve handover
        handover = HandoverRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            from_state=from_state.value,
            to_state=to_state.value,
            reason=reason,
            context=context,
            artifacts=artifacts or [],
            status=HandoverStatus.APPROVED.value,
            rejection_reason=None
        )
        
        self._state.handover_log.append(handover)
        
        # Perform state transition
        transition_result = self.transition_state(from_state, to_state, f"Handover from {from_agent} to {to_agent}", context)
        if not transition_result.success:
            return HandoverResult(
                success=False,
                error_message=transition_result.error_message,
                handover=handover
            )
        
        # Update agent contexts
        self.update_agent_context(from_agent, AgentStatus.IDLE, f"Handed over to {to_agent}")
        self.update_agent_context(to_agent, AgentStatus.WORKING, f"Received handover from {from_agent}")
        
        self._state.metrics.total_handovers += 1
        self._save_state()
        
        return HandoverResult(success=True, handover=handover)
    
    def get_handover_history(
        self,
        agent: Optional[str] = None,
        status: Optional[HandoverStatus] = None,
        since: Optional[datetime] = None,
        from_state: Optional[WorkflowState] = None,
        to_state: Optional[WorkflowState] = None
    ) -> List[HandoverRecord]:
        """
        Get handover history with optional filtering.
        
        Args:
            agent: Filter by agent (from or to)
            status: Filter by handover status
            since: Filter by timestamp (after this date)
            from_state: Filter by from_state
            to_state: Filter by to_state
            
        Returns:
            List of matching handover records, ordered by timestamp (newest first)
        """
        handovers = self._state.handover_log
        
        if agent:
            handovers = [h for h in handovers if h.from_agent == agent or h.to_agent == agent]
        
        if status:
            handovers = [h for h in handovers if h.status == status.value]
        
        if since:
            since_iso = since.isoformat()
            handovers = [h for h in handovers if h.timestamp >= since_iso]
        
        if from_state:
            handovers = [h for h in handovers if h.from_state == from_state.value]
        
        if to_state:
            handovers = [h for h in handovers if h.to_state == to_state.value]
        
        return sorted(handovers, key=lambda h: h.timestamp, reverse=True)
    
    # ========================================================================
    # Public API - Agent Context
    # ========================================================================
    
    def get_agent_context(self, agent_name: str) -> Optional[AgentContext]:
        """Get the context for a specific agent."""
        return self._state.agent_context.get(agent_name)
    
    def update_agent_context(
        self,
        agent_name: str,
        status: Optional[AgentStatus] = None,
        output: Optional[str] = None,
        work_products: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Update the context for a specific agent.
        
        Args:
            agent_name: Name of the agent
            status: New status (if provided)
            output: Last output message (if provided)
            work_products: Work products list (if provided)
            metadata: Metadata dict (if provided)
        """
        existing = self._state.agent_context.get(agent_name, AgentContext())
        
        updated = AgentContext(
            last_active=datetime.now(timezone.utc).isoformat(),
            status=status.value if status else existing.status,
            last_output=output if output is not None else existing.last_output,
            work_products=work_products if work_products is not None else existing.work_products,
            metadata=metadata if metadata is not None else existing.metadata
        )
        
        self._state.agent_context[agent_name] = updated
        self._save_state()
    
    # ========================================================================
    # Public API - Blockers
    # ========================================================================
    
    def add_blocker(
        self,
        description: str,
        impact: Priority,
        affected_state: Optional[str] = None,
        affected_agent: Optional[str] = None
    ) -> Blocker:
        """
        Add a blocker to the workflow.
        
        Args:
            description: Blocker description
            impact: Impact priority
            affected_state: Affected workflow state (optional)
            affected_agent: Affected agent (optional)
            
        Returns:
            Created blocker record
        """
        blocker = Blocker(
            id=str(uuid.uuid4()),
            description=description,
            impact=impact.value,
            affected_state=affected_state,
            affected_agent=affected_agent,
            created_at=datetime.now(timezone.utc).isoformat(),
            status=BlockerStatus.OPEN.value
        )
        
        self._state.blockers.append(blocker)
        self._save_state()
        return blocker
    
    def resolve_blocker(self, blocker_id: str, resolution: str) -> bool:
        """
        Resolve a blocker by ID.
        
        Args:
            blocker_id: ID of the blocker to resolve
            resolution: Resolution description
            
        Returns:
            True if blocker was found and resolved, False otherwise
        """
        for i, blocker in enumerate(self._state.blockers):
            if blocker.id == blocker_id:
                resolved = Blocker(
                    id=blocker.id,
                    description=blocker.description,
                    impact=blocker.impact,
                    affected_state=blocker.affected_state,
                    affected_agent=blocker.affected_agent,
                    created_at=blocker.created_at,
                    status=BlockerStatus.RESOLVED.value,
                    resolved_at=datetime.now(timezone.utc).isoformat(),
                    resolution=resolution
                )
                self._state.blockers[i] = resolved
                self._save_state()
                return True
        return False
    
    def get_active_blockers(self) -> List[Blocker]:
        """
        Get all active blockers.
        
        Returns:
            List of active blockers, ordered by impact (highest first), then by created_at
        """
        active = [
            b for b in self._state.blockers
            if b.status in (BlockerStatus.OPEN.value, BlockerStatus.IN_PROGRESS.value)
        ]
        
        priority_order = {
            Priority.CRITICAL.value: 0,
            Priority.HIGH.value: 1,
            Priority.MEDIUM.value: 2,
            Priority.LOW.value: 3
        }
        
        return sorted(active, key=lambda b: (priority_order.get(b.impact, 99), b.created_at))
    
    # ========================================================================
    # Public API - Pending Actions
    # ========================================================================
    
    def add_pending_action(
        self,
        action: str,
        owner: str,
        priority: Priority = Priority.MEDIUM,
        due_by: Optional[datetime] = None
    ) -> PendingAction:
        """
        Add a pending action.
        
        Args:
            action: Action description
            owner: Agent responsible
            priority: Action priority
            due_by: Optional due date
            
        Returns:
            Created pending action record
        """
        pending_action = PendingAction(
            id=str(uuid.uuid4()),
            action=action,
            owner=owner,
            created_at=datetime.now(timezone.utc).isoformat(),
            priority=priority.value,
            status=ActionStatus.PENDING.value,
            due_by=due_by.isoformat() if due_by else None
        )
        
        self._state.pending_actions.append(pending_action)
        self._save_state()
        return pending_action
    
    def complete_pending_action(self, action_id: str, outcome: Optional[str] = None) -> bool:
        """
        Complete a pending action.
        
        Args:
            action_id: ID of the action to complete
            outcome: Optional outcome description
            
        Returns:
            True if action was found and completed, False otherwise
        """
        for i, action in enumerate(self._state.pending_actions):
            if action.id == action_id:
                completed = PendingAction(
                    id=action.id,
                    action=action.action,
                    owner=action.owner,
                    created_at=action.created_at,
                    priority=action.priority,
                    status=ActionStatus.COMPLETE.value,
                    due_by=action.due_by,
                    completed_at=datetime.now(timezone.utc).isoformat()
                )
                self._state.pending_actions[i] = completed
                self._save_state()
                return True
        return False
    
    # ========================================================================
    # Public API - Decisions
    # ========================================================================
    
    def record_decision(
        self,
        decision: str,
        rationale: str,
        impact: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DecisionRecord:
        """
        Record a coordinator decision.
        
        Args:
            decision: The decision made
            rationale: Rationale for the decision
            impact: Expected impact (stored in outcome field)
            context: Optional context dictionary
            
        Returns:
            Created decision record
        """
        decision_record = DecisionRecord(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision=decision,
            rationale=rationale,
            context=context,
            outcome=impact
        )
        
        self._state.decisions.append(decision_record)
        self._save_state()
        return decision_record
    
    def get_decisions(self, since: Optional[datetime] = None) -> List[DecisionRecord]:
        """
        Get all decisions with optional filtering.
        
        Args:
            since: Optional datetime filter (after this date)
            
        Returns:
            List of decision records, ordered by timestamp (newest first)
        """
        decisions = self._state.decisions
        
        if since:
            since_iso = since.isoformat()
            decisions = [d for d in decisions if d.timestamp >= since_iso]
        
        return sorted(decisions, key=lambda d: d.timestamp, reverse=True)
    
    # ========================================================================
    # Public API - Metrics
    # ========================================================================
    
    def get_metrics(self) -> WorkflowMetrics:
        """Get current workflow metrics."""
        return self._state.metrics
    
    # ========================================================================
    # Public API - Project Knowledge
    # ========================================================================
    
    def add_convention(
        self,
        category: str,
        pattern: str,
        examples: Optional[List[str]] = None,
        confidence: float = 1.0
    ):
        """
        Add a learned convention to project knowledge.
        
        Args:
            category: Convention category
            pattern: Pattern description
            examples: Example list
            confidence: Confidence score (0.0 to 1.0)
        """
        convention = Convention(
            category=category,
            pattern=pattern,
            examples=examples or [],
            confidence=confidence
        )
        
        self._state.project_knowledge.conventions.append(convention)
        self._save_state()
    
    def add_common_decision(self, situation: str, decision: str, rationale: str):
        """
        Record a common decision pattern.
        
        Args:
            situation: Situation description
            decision: Decision made
            rationale: Rationale for decision
        """
        common_decision = CommonDecision(
            situation=situation,
            decision=decision,
            rationale=rationale,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        self._state.project_knowledge.common_decisions.append(common_decision)
        self._save_state()
    
    def get_state(self) -> CoordinatorState:
        """Get the complete coordinator state."""
        return self._state
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _update_metrics(self, transition: StateTransition):
        """Update metrics based on a state transition."""
        from_idx = list(WorkflowState).index(WorkflowState(transition.from_state))
        to_idx = list(WorkflowState).index(WorkflowState(transition.to_state))
        
        # Check for rework (backward transition)
        if to_idx < from_idx:
            # Find existing rework pattern
            existing = None
            for pattern in self._state.metrics.rework_patterns:
                if pattern.from_state == transition.from_state and pattern.to_state == transition.to_state:
                    existing = pattern
                    break
            
            if existing:
                # Update count
                existing.count += 1
            else:
                # Add new pattern
                self._state.metrics.rework_patterns.append(
                    ReworkPattern(
                        from_state=transition.from_state,
                        to_state=transition.to_state,
                        count=1,
                        reason=transition.reason
                    )
                )
        
        # Update feature count if transitioning to COMPLETE
        if transition.to_state == WorkflowState.COMPLETE.value:
            self._state.metrics.total_features += 1
