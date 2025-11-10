"""Simple test to check which cases are failing."""

# Test data from test_performance.py
SAMPLE_TASKS = [
    "Buy groceries tomorrow",
    "Call the dentist at 2pm on Friday",
    "Submit quarterly report by end of week",
    "Schedule team meeting for next Monday at 10am",
    "Review pull request #42 urgent",
]

SAMPLE_EVENTS = [
    "Doctor appointment tomorrow at 3pm",
    "Conference call with client on Wednesday at 9am",
    "Lunch with Sarah at Cafe Roma at noon",
    "Team standup meeting at 9:30am daily",
    "Birthday party on Saturday at 7pm",
]

SAMPLE_NOTES = [
    "Remember to bring laptop charger",
    "Note to self: check email before meeting",
    "Don't forget parking pass tomorrow",
    "Keep in mind the deadline is flexible",
    "Important: verify credentials before deployment",
]

# Simulate the classification logic
def classify_text(text: str) -> str:
    """Simulate the precedence-based classification."""
    text_lower = text.lower()
    
    # Note keywords - highest priority
    note_keywords = ["remember", "note to", "don't forget", "keep in mind", "important:"]
    has_note_keyword = any(kw in text_lower for kw in note_keywords)
    
    # Event keywords - check for specific phrases BEFORE generic action verbs
    strong_event_keywords = [
        "meeting", "appointment", "conference call", 
        "lunch with", "dinner with", "party"
    ]
    has_strong_event = any(kw in text_lower for kw in strong_event_keywords)
    
    # Task action verbs that take precedence even over event keywords
    # "Schedule meeting", "Book appointment", "Call dentist" are all TASKs
    task_action_verbs = [
        "buy", "call", "send", "write", "create", "update", "delete", "fix", "submit",
        "complete", "finish", "start", "begin", "check", "verify", "test", "deploy",
        "build", "review", "approve", "schedule", "book", "email", "text", "message", "remind",
    ]
    
    has_task_action = any(
        text_lower.startswith(kw) or f" {kw} " in text_lower
        for kw in task_action_verbs
    )
    
    # Specific task verbs that override event detection
    # "schedule meeting" = TASK, "book appointment" = TASK
    organizing_verbs = ["schedule", "book", "arrange", "organize", "plan"]
    has_organizing_verb = any(
        text_lower.startswith(kw) or f" {kw} " in text_lower
        for kw in organizing_verbs
    )
    
    # Time pattern (updated to match "noon" and "midnight")
    import re
    time_pattern = r"(?:at|@)\s*(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight)"
    has_time = bool(re.search(time_pattern, text_lower))
    
    # Classification with NEW precedence
    # Priority 1: Note keywords first
    if has_note_keyword:
        return "NOTE"
    # Priority 2: Organizing verbs ALWAYS indicate TASK (even with event keywords)
    # "Schedule meeting", "Book appointment" are tasks to DO
    elif has_organizing_verb:
        return "TASK"
    # Priority 3: Event keywords + time (if no organizing verb)
    elif has_strong_event and has_time:
        return "EVENT"
    # Priority 4: Other task action verbs
    elif has_task_action:
        return "TASK"
    else:
        return "UNKNOWN (fallback to embedding)"

# Test all samples
print("=" * 80)
print("TESTING TASKS (should all be TASK)")
print("=" * 80)
for i, text in enumerate(SAMPLE_TASKS, 1):
    result = classify_text(text)
    status = "✅" if result == "TASK" else "❌"
    print(f"{status} {i}. \"{text}\" → {result}")

print("\n" + "=" * 80)
print("TESTING EVENTS (should all be EVENT)")
print("=" * 80)
for i, text in enumerate(SAMPLE_EVENTS, 1):
    result = classify_text(text)
    status = "✅" if result == "EVENT" else "❌"
    print(f"{status} {i}. \"{text}\" → {result}")

print("\n" + "=" * 80)
print("TESTING NOTES (should all be NOTE)")
print("=" * 80)
for i, text in enumerate(SAMPLE_NOTES, 1):
    result = classify_text(text)
    status = "✅" if result == "NOTE" else "❌"
    print(f"{status} {i}. \"{text}\" → {result}")

# Summary
all_samples = [
    ("TASK", text, classify_text(text)) for text in SAMPLE_TASKS
] + [
    ("EVENT", text, classify_text(text)) for text in SAMPLE_EVENTS
] + [
    ("NOTE", text, classify_text(text)) for text in SAMPLE_NOTES
]

correct = sum(1 for expected, _, actual in all_samples if expected == actual)
total = len(all_samples)
accuracy = correct / total

print("\n" + "=" * 80)
print(f"ACCURACY: {correct}/{total} = {accuracy:.1%}")
print("=" * 80)
