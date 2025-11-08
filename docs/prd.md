# remindr — Product Requirements Document (PRD)
**Version:** 1.0  
**Date:** November 2025  
**Author:** Anton Cornett  

---

## 1. Overview
The **remindr** app is an intelligent productivity tool that enables users to quickly capture, organize, and prioritize tasks using natural inputs such as **voice**, **text**, and **images**.  
It integrates seamlessly with **Google Tasks** and **Google Calendar**, using AI to interpret intent (task vs event) and suggest due dates, priorities, and categories.

---

## 2. Problem Statement
People often think of tasks or appointments on the go but find it cumbersome to open a task manager, type details, and organize them manually.  
Current tools lack the fluidity to capture ideas instantly and contextually—especially via **voice or image-based input**.

### Key Pain Points
- Manual entry slows down task capture  
- Tasks and events end up scattered across tools  
- Context (urgency, time, intent) is often lost  

---

## 3. Goals and Objectives

### Primary Goals
- Capture tasks or reminders instantly via **voice**, **text**, or **camera input**  
- Use AI to decide if an input is a **task** or a **calendar event**  
- Automatically **classify, prioritize, and schedule** tasks  
- Seamlessly **sync with Google Tasks and Calendar**

### Secondary Goals
- Integrate with **Google Gemini** or voice assistants  
- Support offline capture with later sync  
- Offer a minimal, fast, distraction-free interface  

---

## 4. Target Users

| User Type | Description | Needs |
|------------|--------------|--------|
| Busy professionals | Juggling meetings and deadlines | Quick capture, automatic scheduling |
| Students | Tracking classes, assignments | Easy reminders, flexible input |
| Makers / Developers | Managing ideas and side projects | Tagging, categorization |
| General users | Everyday personal tasks | Fast and simple capture |

---

## 5. Key Features

### Core Features
1. **Voice Capture**
   - Speech-to-text input  
   - AI interprets phrases like “Remind me to call mom tomorrow at 8”  

2. **Text Capture**
   - Quick-add bar (“Buy milk at ICA tomorrow”)  
   - Smart date/time/priority parsing  

3. **Image Capture**
   - OCR on handwritten or printed notes  
   - Extracts text into actionable tasks  

4. **AI Task Classification**
   - Detects task vs event  
   - Suggests due dates and urgency  
   - Learns from user behavior  

5. **Google Sync**
   - Two-way integration with **Google Tasks** and **Calendar**  
   - Secure OAuth 2.0 authentication  

6. **Offline Mode**
   - Capture tasks offline  
   - Automatic sync when reconnected  

7. **Voice Assistant Integration (Future)**
   - “Hey Gemini, add ‘Pay rent on the 1st’ to remindr”  

---

## 6. Success Metrics

| Metric | Target |
|---------|---------|
| Task capture time | < 3 seconds |
| AI classification accuracy | ≥ 90% |
| Google sync latency | < 10 seconds |
| 30-day active retention | ≥ 60% |
| Misclassification rate | < 5% |

---

## 7. User Flow

### Voice Capture
1. Tap mic → speak “Buy groceries tomorrow”  
2. AI transcribes and classifies input  
3. User confirms or edits draft  
4. Task syncs to Google Tasks  
5. Confirmation message shown  

### Image Capture
1. Take a photo of handwritten notes  
2. AI extracts text and identifies potential tasks  
3. User selects tasks to save  
4. Tasks appear in Google Tasks list  

### Text Capture
1. Type “Dentist at 14:00 Thursday”  
2. AI detects date/time and classifies as event  
3. Event added to Calendar  

---

## 8. Technical Requirements

| Area | Details |
|------|----------|
| **Frontend** | Flutter (Android/iOS/Web) |
| **Backend** | FastAPI or Node.js |
| **AI Services** | Google Vertex AI / Gemini API |
| **Database** | Firestore or SQLite |
| **Integrations** | Google Tasks, Google Calendar |
| **Auth** | OAuth 2.0 |
| **Storage** | Cloud Storage (for images) |
| **Latency** | Voice transcription < 1s, full classification < 3s |

---

## 9. Risks and Mitigations

| Risk | Mitigation |
|------|-------------|
| AI misclassifies inputs | Provide quick manual correction |
| Google API rate limits | Background sync + exponential backoff |
| Privacy concerns | Local processing where possible; anonymized logs |
| API deprecations | Abstract sync layer for portability |

---

## 10. Future Enhancements
- Multi-language input and translation  
- Home screen widget for quick capture  
- Daily summaries (“You have 3 tasks due today”)  
- Integration with **Notion**, **Todoist**, or **Taskwarrior**  
- Location-based reminders  

---

## 11. Example AI Prompts

- “Summarize this note into 3 actionable tasks”  
- “Classify: is this a meeting or a reminder?”  
- “Predict due date from text context”  

---

## 12. Mock UI (Future)
- Quick input bar at top  
- “Smart Drafts” section with AI tags  
- Task list synced with Google  
- Status indicator: offline / syncing / done  

---

## 13. Appendix: MVP Scope

**Minimum Viable Product includes:**
- Voice, text, and image capture  
- AI classification with confidence threshold  
- Google Tasks/Calendar sync  
- Offline capture + retry mechanism  
- Simple confirmation UI  

**Excluded from MVP:**
- Assistant integration  
- Team sharing  
- Advanced analytics  
- Multi-language support  

---
