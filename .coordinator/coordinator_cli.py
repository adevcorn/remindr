#!/usr/bin/env python3
"""
Coordinator CLI - Command-line interface for coordinator memory operations.

IMPORTANT: This CLI is intended for COORDINATOR USE ONLY.
Other agents must not directly use these commands.

Usage:
    python coordinator_cli.py <command> [options]

Commands:
    status              - Show current workflow state
    transition          - Transition workflow state
    handover            - Record agent handover
    update-agent        - Update agent context
    add-blocker         - Add a blocker
    resolve-blocker     - Resolve a blocker
    list-blockers       - List active blockers
    add-action          - Add pending action
    complete-action     - Complete pending action
    record-decision     - Record a decision
    list-decisions      - List recent decisions
    list-handovers      - List handover history
    metrics             - Show workflow metrics
    set-feature         - Set current feature
    clear-feature       - Clear current feature
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from coordinator_memory import (
    CoordinatorMemory,
    WorkflowState,
    AgentStatus,
    Priority,
    HandoverStatus
)


def format_output(data, format_type: str = "json"):
    """Format output for CLI."""
    if format_type == "json":
        return json.dumps(data, indent=2)
    return str(data)


def handle_status(memory: CoordinatorMemory, args):
    """Handle status command."""
    current_state = memory.get_current_state()
    current_feature = memory.get_current_feature()
    
    output = {
        "currentState": current_state.value,
        "currentFeature": {
            "name": current_feature.name,
            "branch": current_feature.branch,
            "description": current_feature.description,
            "startedAt": current_feature.started_at,
            "acceptanceCriteria": current_feature.acceptance_criteria
        } if current_feature else None
    }
    
    print(format_output(output))


def handle_transition(memory: CoordinatorMemory, args):
    """Handle transition command."""
    try:
        from_state = WorkflowState(args.from_state)
        to_state = WorkflowState(args.to_state)
    except ValueError as e:
        print(json.dumps({"error": f"Invalid state: {e}"}), file=sys.stderr)
        sys.exit(1)
    
    result = memory.transition_state(from_state, to_state, args.reason, args.context)
    
    if result.success and result.transition:
        output = {
            "success": True,
            "transition": {
                "fromState": result.transition.from_state,
                "toState": result.transition.to_state,
                "timestamp": result.transition.timestamp,
                "reason": result.transition.reason,
                "approved": result.transition.approved
            }
        }
        print(format_output(output))
    else:
        print(json.dumps({"success": False, "error": result.error_message}), file=sys.stderr)
        sys.exit(1)


def handle_handover(memory: CoordinatorMemory, args):
    """Handle handover command."""
    try:
        from_state = WorkflowState(args.from_state)
        to_state = WorkflowState(args.to_state)
    except ValueError as e:
        print(json.dumps({"error": f"Invalid state: {e}"}), file=sys.stderr)
        sys.exit(1)
    
    artifacts = args.artifacts.split(',') if args.artifacts else None
    
    result = memory.add_handover(
        args.from_agent,
        args.to_agent,
        from_state,
        to_state,
        args.reason,
        args.context,
        artifacts
    )
    
    if result.success and result.handover:
        output = {
            "success": True,
            "handover": {
                "id": result.handover.id,
                "fromAgent": result.handover.from_agent,
                "toAgent": result.handover.to_agent,
                "fromState": result.handover.from_state,
                "toState": result.handover.to_state,
                "status": result.handover.status,
                "timestamp": result.handover.timestamp
            }
        }
        print(format_output(output))
    else:
        output = {
            "success": False,
            "error": result.error_message,
            "handover": {
                "id": result.handover.id,
                "status": result.handover.status,
                "rejectionReason": result.handover.rejection_reason
            } if result.handover else None
        }
        print(json.dumps(output), file=sys.stderr)
        sys.exit(1)


def handle_update_agent(memory: CoordinatorMemory, args):
    """Handle update-agent command."""
    status = AgentStatus(args.status) if args.status else None
    
    memory.update_agent_context(
        args.agent,
        status,
        args.output,
        args.work_products.split(',') if args.work_products else None
    )
    
    context = memory.get_agent_context(args.agent)
    if context:
        output = {
            "success": True,
            "agent": args.agent,
            "context": {
                "status": context.status,
                "lastActive": context.last_active,
                "lastOutput": context.last_output,
                "workProducts": context.work_products
            }
        }
        print(format_output(output))
    else:
        print(json.dumps({"success": False, "error": "Agent not found"}), file=sys.stderr)
        sys.exit(1)


def handle_add_blocker(memory: CoordinatorMemory, args):
    """Handle add-blocker command."""
    impact = Priority(args.impact)
    
    blocker = memory.add_blocker(
        args.description,
        impact,
        args.affected_state,
        args.affected_agent
    )
    
    output = {
        "success": True,
        "blocker": {
            "id": blocker.id,
            "description": blocker.description,
            "impact": blocker.impact,
            "affectedState": blocker.affected_state,
            "affectedAgent": blocker.affected_agent,
            "status": blocker.status,
            "createdAt": blocker.created_at
        }
    }
    print(format_output(output))


def handle_resolve_blocker(memory: CoordinatorMemory, args):
    """Handle resolve-blocker command."""
    success = memory.resolve_blocker(args.blocker_id, args.resolution)
    
    if success:
        print(json.dumps({"success": True, "blockerId": args.blocker_id}))
    else:
        print(json.dumps({"success": False, "error": "Blocker not found"}), file=sys.stderr)
        sys.exit(1)


def handle_list_blockers(memory: CoordinatorMemory, args):
    """Handle list-blockers command."""
    blockers = memory.get_active_blockers()
    
    output = {
        "count": len(blockers),
        "blockers": [
            {
                "id": b.id,
                "description": b.description,
                "impact": b.impact,
                "affectedState": b.affected_state,
                "affectedAgent": b.affected_agent,
                "status": b.status,
                "createdAt": b.created_at
            }
            for b in blockers
        ]
    }
    print(format_output(output))


def handle_add_action(memory: CoordinatorMemory, args):
    """Handle add-action command."""
    priority = Priority(args.priority)
    due_by = datetime.fromisoformat(args.due_by) if args.due_by else None
    
    action = memory.add_pending_action(args.action, args.owner, priority, due_by)
    
    output = {
        "success": True,
        "action": {
            "id": action.id,
            "action": action.action,
            "owner": action.owner,
            "priority": action.priority,
            "status": action.status,
            "createdAt": action.created_at,
            "dueBy": action.due_by
        }
    }
    print(format_output(output))


def handle_complete_action(memory: CoordinatorMemory, args):
    """Handle complete-action command."""
    success = memory.complete_pending_action(args.action_id, args.outcome)
    
    if success:
        print(json.dumps({"success": True, "actionId": args.action_id}))
    else:
        print(json.dumps({"success": False, "error": "Action not found"}), file=sys.stderr)
        sys.exit(1)


def handle_record_decision(memory: CoordinatorMemory, args):
    """Handle record-decision command."""
    context = json.loads(args.context) if args.context else None
    
    decision = memory.record_decision(args.decision, args.rationale, args.impact, context)
    
    output = {
        "success": True,
        "decision": {
            "id": decision.id,
            "decision": decision.decision,
            "rationale": decision.rationale,
            "outcome": decision.outcome,
            "timestamp": decision.timestamp
        }
    }
    print(format_output(output))


def handle_list_decisions(memory: CoordinatorMemory, args):
    """Handle list-decisions command."""
    since = datetime.fromisoformat(args.since) if args.since else None
    decisions = memory.get_decisions(since)
    
    output = {
        "count": len(decisions),
        "decisions": [
            {
                "id": d.id,
                "decision": d.decision,
                "rationale": d.rationale,
                "outcome": d.outcome,
                "timestamp": d.timestamp
            }
            for d in decisions
        ]
    }
    print(format_output(output))


def handle_list_handovers(memory: CoordinatorMemory, args):
    """Handle list-handovers command."""
    status = HandoverStatus(args.status) if args.status else None
    since = datetime.fromisoformat(args.since) if args.since else None
    
    handovers = memory.get_handover_history(args.agent, status, since)
    
    output = {
        "count": len(handovers),
        "handovers": [
            {
                "id": h.id,
                "fromAgent": h.from_agent,
                "toAgent": h.to_agent,
                "fromState": h.from_state,
                "toState": h.to_state,
                "status": h.status,
                "reason": h.reason,
                "timestamp": h.timestamp,
                "rejectionReason": h.rejection_reason
            }
            for h in handovers
        ]
    }
    print(format_output(output))


def handle_metrics(memory: CoordinatorMemory, args):
    """Handle metrics command."""
    metrics = memory.get_metrics()
    
    output = {
        "totalFeatures": metrics.total_features,
        "totalHandovers": metrics.total_handovers,
        "rejectedHandovers": metrics.rejected_handovers,
        "averageCycleTime": metrics.average_cycle_time,
        "stateCycleTimes": metrics.state_cycle_times,
        "reworkPatterns": [
            {
                "fromState": p.from_state,
                "toState": p.to_state,
                "count": p.count,
                "reason": p.reason
            }
            for p in metrics.rework_patterns
        ],
        "agentUtilization": metrics.agent_utilization
    }
    print(format_output(output))


def handle_set_feature(memory: CoordinatorMemory, args):
    """Handle set-feature command."""
    criteria = args.criteria.split(',') if args.criteria else None
    issues = args.issues.split(',') if args.issues else None
    
    memory.set_current_feature(args.name, args.branch, args.description, criteria, issues)
    
    feature = memory.get_current_feature()
    if feature:
        output = {
            "success": True,
            "feature": {
                "name": feature.name,
                "branch": feature.branch,
                "description": feature.description,
                "startedAt": feature.started_at,
                "acceptanceCriteria": feature.acceptance_criteria,
                "linkedIssues": feature.linked_issues
            }
        }
        print(format_output(output))
    else:
        print(json.dumps({"success": False, "error": "Feature not set"}), file=sys.stderr)
        sys.exit(1)


def handle_clear_feature(memory: CoordinatorMemory, args):
    """Handle clear-feature command."""
    memory.clear_current_feature()
    print(json.dumps({"success": True}))


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Coordinator Memory CLI - For coordinator use only",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--state-file',
        help='Path to state file (default: .coordinator/coordinator-state.json)'
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Status command
    subparsers.add_parser('status', help='Show current workflow state')
    
    # Transition command
    transition_parser = subparsers.add_parser('transition', help='Transition workflow state')
    transition_parser.add_argument('--from-state', required=True, help='Current state')
    transition_parser.add_argument('--to-state', required=True, help='Target state')
    transition_parser.add_argument('--reason', required=True, help='Transition reason')
    transition_parser.add_argument('--context', help='Additional context')
    
    # Handover command
    handover_parser = subparsers.add_parser('handover', help='Record agent handover')
    handover_parser.add_argument('--from-agent', required=True, help='Agent handing over')
    handover_parser.add_argument('--to-agent', required=True, help='Agent receiving')
    handover_parser.add_argument('--from-state', required=True, help='Current state')
    handover_parser.add_argument('--to-state', required=True, help='Target state')
    handover_parser.add_argument('--reason', required=True, help='Handover reason')
    handover_parser.add_argument('--context', help='Additional context')
    handover_parser.add_argument('--artifacts', help='Comma-separated artifact paths')
    
    # Update agent command
    update_agent_parser = subparsers.add_parser('update-agent', help='Update agent context')
    update_agent_parser.add_argument('--agent', required=True, help='Agent name')
    update_agent_parser.add_argument('--status', help='Agent status')
    update_agent_parser.add_argument('--output', help='Last output message')
    update_agent_parser.add_argument('--work-products', help='Comma-separated work products')
    
    # Add blocker command
    add_blocker_parser = subparsers.add_parser('add-blocker', help='Add a blocker')
    add_blocker_parser.add_argument('--description', required=True, help='Blocker description')
    add_blocker_parser.add_argument('--impact', required=True, choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], help='Impact priority')
    add_blocker_parser.add_argument('--affected-state', help='Affected workflow state')
    add_blocker_parser.add_argument('--affected-agent', help='Affected agent')
    
    # Resolve blocker command
    resolve_blocker_parser = subparsers.add_parser('resolve-blocker', help='Resolve a blocker')
    resolve_blocker_parser.add_argument('--blocker-id', required=True, help='Blocker ID')
    resolve_blocker_parser.add_argument('--resolution', required=True, help='Resolution description')
    
    # List blockers command
    subparsers.add_parser('list-blockers', help='List active blockers')
    
    # Add action command
    add_action_parser = subparsers.add_parser('add-action', help='Add pending action')
    add_action_parser.add_argument('--action', required=True, help='Action description')
    add_action_parser.add_argument('--owner', required=True, help='Agent responsible')
    add_action_parser.add_argument('--priority', default='MEDIUM', choices=['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], help='Priority')
    add_action_parser.add_argument('--due-by', help='Due date (ISO format)')
    
    # Complete action command
    complete_action_parser = subparsers.add_parser('complete-action', help='Complete pending action')
    complete_action_parser.add_argument('--action-id', required=True, help='Action ID')
    complete_action_parser.add_argument('--outcome', help='Outcome description')
    
    # Record decision command
    record_decision_parser = subparsers.add_parser('record-decision', help='Record a decision')
    record_decision_parser.add_argument('--decision', required=True, help='Decision made')
    record_decision_parser.add_argument('--rationale', required=True, help='Decision rationale')
    record_decision_parser.add_argument('--impact', help='Expected impact')
    record_decision_parser.add_argument('--context', help='Context JSON')
    
    # List decisions command
    list_decisions_parser = subparsers.add_parser('list-decisions', help='List recent decisions')
    list_decisions_parser.add_argument('--since', help='Filter by date (ISO format)')
    
    # List handovers command
    list_handovers_parser = subparsers.add_parser('list-handovers', help='List handover history')
    list_handovers_parser.add_argument('--agent', help='Filter by agent')
    list_handovers_parser.add_argument('--status', choices=['APPROVED', 'REJECTED'], help='Filter by status')
    list_handovers_parser.add_argument('--since', help='Filter by date (ISO format)')
    
    # Metrics command
    subparsers.add_parser('metrics', help='Show workflow metrics')
    
    # Set feature command
    set_feature_parser = subparsers.add_parser('set-feature', help='Set current feature')
    set_feature_parser.add_argument('--name', required=True, help='Feature name')
    set_feature_parser.add_argument('--branch', required=True, help='Git branch')
    set_feature_parser.add_argument('--description', required=True, help='Feature description')
    set_feature_parser.add_argument('--criteria', help='Comma-separated acceptance criteria')
    set_feature_parser.add_argument('--issues', help='Comma-separated linked issues')
    
    # Clear feature command
    subparsers.add_parser('clear-feature', help='Clear current feature')
    
    args = parser.parse_args()
    
    # Initialize memory
    try:
        memory = CoordinatorMemory(args.state_file)
    except Exception as e:
        print(json.dumps({"error": f"Failed to initialize memory: {e}"}), file=sys.stderr)
        sys.exit(1)
    
    # Dispatch to handler
    handlers = {
        'status': handle_status,
        'transition': handle_transition,
        'handover': handle_handover,
        'update-agent': handle_update_agent,
        'add-blocker': handle_add_blocker,
        'resolve-blocker': handle_resolve_blocker,
        'list-blockers': handle_list_blockers,
        'add-action': handle_add_action,
        'complete-action': handle_complete_action,
        'record-decision': handle_record_decision,
        'list-decisions': handle_list_decisions,
        'list-handovers': handle_list_handovers,
        'metrics': handle_metrics,
        'set-feature': handle_set_feature,
        'clear-feature': handle_clear_feature
    }
    
    handler = handlers.get(args.command)
    if handler:
        try:
            handler(memory, args)
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
    else:
        print(json.dumps({"error": f"Unknown command: {args.command}"}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
