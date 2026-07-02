# Delta for Chat Widget

## ADDED Requirements

### Requirement: Light-Mode Input Readability

The system MUST render typed chat input text with sufficient contrast against the light-mode input background. On light theme activation, the input text color MUST be dark enough to meet WCAG AA contrast minimum for normal text.

#### Scenario: Typed text visible in light theme

- GIVEN the chat panel is open and the active theme is light (`[data-theme="light"]`)
- WHEN the user types text into the chat input field
- THEN the typed characters are clearly visible against the input background
- AND contrast meets WCAG AA ratio of at least 4.5:1

#### Scenario: Dark theme input unaffected

- GIVEN the chat panel is open and the active theme is dark (`[data-theme="dark"]`)
- WHEN the user types text into the chat input field
- THEN the input text appearance is unchanged from current behavior

### Requirement: Rotating Localized Loading Messages

The system SHALL display a rotating set of Cero/archive-themed loading messages while an API request is pending, replacing the previous static single message. Each of the six supported languages MUST define at least three distinct messages. Messages SHALL rotate on a timed interval. The rotation timer MUST be cleared when loading ends.

#### Scenario: Loading indicator shows rotating messages

- GIVEN the user has sent a question and the API request is pending
- WHEN the loading state is active
- THEN a localized archive-themed loading message is displayed
- AND the message changes to the next message in the set on each interval tick

#### Scenario: At least three messages per supported language

- GIVEN the system supports English, Spanish, Catalan, French, Portuguese, and German
- THEN each language has at least three distinct loading messages
- AND every message references Cero or archive-related themes

#### Scenario: Rotation stops when loading ends

- GIVEN the loading indicator is cycling through messages
- WHEN the API response arrives and loading ends
- THEN the rotation timer is cleared
- THEN no stale interval continues in the background

#### Scenario: Fast response before first rotation tick

- GIVEN loading becomes active and the rotation interval has not yet fired
- WHEN the API request completes before the first tick
- THEN the timer is cleared without cycling
- THEN the first message in the set was displayed while loading was active
