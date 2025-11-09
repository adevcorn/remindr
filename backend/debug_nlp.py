"""Debug script to test NLP classification on each test case."""
import asyncio
from app.services.nlp import nlp_service
from app.models.capture import DraftType

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

async def test_classification():
    print("\n" + "="*80)
    print("TASK Classification Tests (Expected: TASK)")
    print("="*80)
    correct = 0
    for i, text in enumerate(SAMPLE_TASKS, 1):
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        is_correct = draft_type == DraftType.TASK
        correct += is_correct
        status = "✅" if is_correct else "❌"
        print(f"{status} {i}. '{text}'")
        print(f"   → {draft_type.value} (confidence: {confidence:.2f})")
    print(f"\nTASKS: {correct}/5 correct\n")
    
    print("="*80)
    print("EVENT Classification Tests (Expected: EVENT)")
    print("="*80)
    event_correct = 0
    for i, text in enumerate(SAMPLE_EVENTS, 1):
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        is_correct = draft_type == DraftType.EVENT
        event_correct += is_correct
        status = "✅" if is_correct else "❌"
        print(f"{status} {i}. '{text}'")
        print(f"   → {draft_type.value} (confidence: {confidence:.2f})")
    print(f"\nEVENTS: {event_correct}/5 correct\n")
    
    print("="*80)
    print("NOTE Classification Tests (Expected: NOTE)")
    print("="*80)
    note_correct = 0
    for i, text in enumerate(SAMPLE_NOTES, 1):
        draft_type, confidence, _ = await nlp_service.classify_and_extract(text)
        is_correct = draft_type == DraftType.NOTE
        note_correct += is_correct
        status = "✅" if is_correct else "❌"
        print(f"{status} {i}. '{text}'")
        print(f"   → {draft_type.value} (confidence: {confidence:.2f})")
    print(f"\nNOTES: {note_correct}/5 correct\n")
    
    total_correct = correct + event_correct + note_correct
    total = 15
    accuracy = total_correct / total
    print("="*80)
    print(f"OVERALL: {total_correct}/{total} correct ({accuracy:.1%})")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_classification())
