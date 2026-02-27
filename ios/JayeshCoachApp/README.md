# Jayesh Coach iOS App

A production-grade SwiftUI foundation for a single unified AI coach tailored to Mr. Jayesh Joshi (CEO, VAAGDHARA).

## Product pillars

- Unified coaching: leadership, strategy, wellbeing, and relationship guidance in one conversation
- Behavioral system: daily brief, habits, accountability, burnout sentinel, weekly reflection

## Architecture

- `Models/`: domain models and seeded data
- `Services/`: coaching engines, decision quality, relationship support, burnout analytics, persistence
- `ViewModels/`: state orchestration and feature logic
- `Views/`: SwiftUI screens with modular sections

## Core screens

1. Daily Brief
2. Coach (single conversation + voice/text)
3. Habit Lab
4. Weekly Reflection

## AI and Calendar intelligence

- EventKit calendar integration for packed-day analysis (meeting load, free-block detection)
- Schedule protection guidance based on overload score
- Three recurring daily nudges that keep momentum even when the app is not opened
- AI backend support with secure token handling
- Local fallback coaching engine if remote AI is not configured
- Adaptive memory so coaching quality improves with ongoing interactions
- Speech-to-text + text-to-speech with Indian English support
- Goal horizon system (1 month, 3 months, 6 months, 1 year) with dialog-led discovery
- Unified Coach tab includes backend connection settings for private deployment
- Each backend coach turn includes calendar event summary + last 5 memory themes for stronger personalization
- Local fallback responses follow strict structured coaching format (Center, Reframe, Action path, Accountability, Evidence)

## Setup

1. Open Xcode and create a new iOS app target named `JayeshCoachApp`.
2. Replace target files with the source files from `ios/JayeshCoachApp/JayeshCoachApp`.
3. Set deployment target to iOS 17+
4. Add unit tests from `ios/JayeshCoachApp/JayeshCoachAppTests`.
5. Accept calendar permission on first sync in the Daily Brief tab.
6. Accept microphone + speech recognition permissions for voice coaching.

## Why this is not an MVP

- End-to-end coaching loops are implemented, including metrics and persistence.
- The app includes personalized nonprofit context, decision science flows, and relationship micro-interventions.
- The architecture is ready for LLM backends and HealthKit/Calendar integrations.

## Blueprint

- Full strategic design: `ios/JayeshCoachApp/COACHING_OS_BLUEPRINT.md`
- Premium service-level design: `ios/JayeshCoachApp/PREMIUM_CONCIERGE_PRODUCT.md`
