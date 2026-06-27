# Delta Spec: Chat Widget UI Redesign

## Constraint

This iteration MUST NOT introduce CSS animations, `@keyframes`, CSS `transition` properties, or JavaScript-driven animations. State changes between open/closed MUST be instantaneous and static.

## ADDED Requirements

### Requirement: Floating Action Button (FAB) Toggle

The system MUST render a fixed FAB in the bottom-right corner when the chat panel is closed. Clicking the FAB MUST open the side panel. The FAB MUST be hidden while the panel is open and restored when the panel closes.

#### Scenario: FAB opens panel

- GIVEN the panel is closed and the FAB is visible
- WHEN the user clicks the FAB
- THEN the panel opens and the FAB is no longer visible

#### Scenario: Close button restores FAB

- GIVEN the panel is open
- WHEN the user clicks the panel close button
- THEN the panel closes and the FAB is visible again

### Requirement: Side-Panel Layout

The system MUST render the chat as a fixed side panel anchored to the right edge of the viewport. On desktop, the panel width MUST be approximately 30% of the viewport, bounded by a minimum of 320px and a maximum of 480px. Below a 640px breakpoint, the panel MUST occupy the full viewport width.

#### Scenario: Desktop panel width

- GIVEN a viewport width of 1280px
- WHEN the user opens the chat panel
- THEN the panel width is between 320px and 480px

#### Scenario: Small viewport adapts to full width

- GIVEN a viewport width of 480px
- WHEN the user opens the chat panel
- THEN the panel spans the full viewport width

### Requirement: Zero-State Greeting

The system MUST display a static zero-state view when the panel is open and no user message has been sent. The zero-state MUST show a greeting with the agent name, a brief purpose description, and three clickable suggestion cards.

#### Scenario: Suggestion cards visible before first message

- GIVEN the panel is open and the conversation has not started
- THEN the zero-state greeting and three suggestion cards are rendered

#### Scenario: Suggestion card sends question

- GIVEN the zero-state is visible
- WHEN the user clicks the suggestion "¿Qué es FILMIG?"
- THEN the question text is sent to `/api/ask` and the zero-state is hidden

### Requirement: Suggestion Card Set

The system MUST provide exactly three suggestion cards with these labels: "¿Qué es FILMIG?", "¿Qué videos puedo encontrar de Plataforma Cero?", and "¿Qué es mujeres del maíz?". Each card MUST be clickable and MUST trigger the same question as its label.

#### Scenario: All three suggestions present

- GIVEN the zero-state is rendered
- THEN cards for FILMIG, Plataforma Cero videos, and mujeres del maíz are visible

### Requirement: Bottom-Anchored Input Bar

The system MUST anchor the input toolbar at the bottom of the panel. The toolbar MUST contain a text input field, a send button, and a visually distinct but non-functional microphone button placeholder. It SHOULD reserve space for a model selector placeholder in the same toolbar area.

#### Scenario: Input bar stays visible while scrolling

- GIVEN the panel is open with many messages
- WHEN the user scrolls the message list
- THEN the input toolbar remains fixed at the bottom of the panel

#### Scenario: Microphone button is disabled

- GIVEN the input toolbar is rendered
- WHEN the user clicks the microphone button
- THEN no action is taken and focus remains unchanged

## MODIFIED Requirements

### Requirement: Panel Open/Close Behavior

The system MUST display the chat panel as a fixed right-side panel. The previous slide-out transform behavior is replaced by an instantaneous state change.
(Previously: the panel translated in from the right with a CSS transform transition.)

#### Scenario: Panel opens without animation

- GIVEN the panel is closed
- WHEN the user clicks the FAB
- THEN the panel appears immediately without transition effects

### Requirement: Initial Greeting Presentation

The system MUST show the initial greeting inside the zero-state view instead of as the first chat message. The greeting text and purpose description remain static.
(Previously: opening the panel rendered the agent greeting as a chat bubble message.)

#### Scenario: First open shows zero-state greeting

- GIVEN the panel is opened for the first time in a session
- THEN the zero-state greeting is rendered, not a chat bubble

## REMOVED Requirements

### Requirement: Bubble Hover/Active Scale Effects

(Reason: CSS transitions and transforms are prohibited in this iteration.)
(Migration: None — hover/focus states MAY use static color or outline changes instead.)

### Requirement: Message Entrance Animation

(Reason: `@keyframes` animations are prohibited in this iteration.)
(Migration: Messages appear instantly with static styling.)
