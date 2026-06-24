# api-chat-frontend Specification

## chat-api

### Requirement: POST /api/ask endpoint

The system MUST expose `POST /api/ask` accepting a JSON body `{"question": "string"}` and returning HTTP 200 with JSON `{"answer": "string", "sources": [...]}`.

Each source object MUST contain `video_id`, `title`, `start_time`, `end_time`, and `text`.

#### Scenario: Valid Spanish question returns an answer with sources

- GIVEN a running API with a configured agent
- WHEN the client sends `POST /api/ask` with `{"question": "¿cuál es el testimonio de María?"}`
- THEN the response status is 200
- AND `answer` is a non-empty string
- AND `sources` is a list of source objects with all required fields

#### Scenario: Empty question returns a validation error

- GIVEN a running API
- WHEN the client sends `POST /api/ask` with `{"question": ""}`
- THEN the response status is 422
- AND the response body describes the validation error

#### Scenario: Missing GEMINI_API_KEY returns service unavailable

- GIVEN a running API without `GEMINI_API_KEY` configured
- WHEN the client sends a valid `POST /api/ask` request
- THEN the response status is 503
- AND the response body indicates the service is unavailable

### Requirement: Thread-safe per-request agent

The system MUST create a fresh `AgentExecutor` for every request using `create_agent()`.
The system MUST ensure concurrent requests do not share `VectorStore` or Gemini client instances.

#### Scenario: Concurrent requests succeed without lock errors

- GIVEN a running API
- WHEN two clients send `POST /api/ask` simultaneously
- THEN both requests return HTTP 200
- AND neither request raises a lock or shared-state error

### Requirement: CORS configuration

The system MUST configure CORS allowed origins from the `ALLOWED_ORIGINS` environment variable, defaulting to `http://localhost:5173`.

#### Scenario: Preflight request returns correct CORS headers

- GIVEN a running API
- WHEN the browser sends `OPTIONS /api/ask` with `Origin: http://localhost:5173`
- THEN the response status is 200
- AND `Access-Control-Allow-Origin` matches the request origin

## chat-widget

### Requirement: Chat bubble

The system MUST render a floating button fixed in the bottom-right corner of the viewport.
The button MUST display the "Cerito" avatar SVG.
Clicking the button MUST toggle the slide-out chat panel.

#### Scenario: Bubble opens the chat panel

- GIVEN a page with the chat widget
- WHEN the page loads
- THEN the bubble is visible in the bottom-right corner
- AND clicking the bubble opens the chat panel

### Requirement: Chat panel

The system MUST render a slide-out panel 380px wide from the right side of the viewport.
The panel MUST contain a scrollable message list, an input field, and a send button.
Clicking send MUST call `POST /api/ask` and display the returned answer and sources.
The widget MUST use the brand blue `#019ee3` and the system font stack.

#### Scenario: User asks a question in the panel

- GIVEN the chat panel is open
- WHEN the user types a question and clicks send
- THEN the question appears in the message list
- AND the answer appears after the backend responds
- AND the sources are displayed in the panel

## tests

### Requirement: Automated tests

The system MUST provide unit tests for `POST /api/ask` using a mocked agent.
The system MUST provide an integration test that uses the real agent when `GEMINI_API_KEY` is set, otherwise the test MUST be skipped.
The system MUST provide a CORS header test.

#### Scenario: Mocked agent unit test

- GIVEN a mocked agent that returns a fixed answer and sources
- WHEN `POST /api/ask` is invoked
- THEN the response matches the mocked answer and sources

#### Scenario: Integration test with real agent

- GIVEN `GEMINI_API_KEY` is present in the environment
- WHEN `POST /api/ask` is invoked with a real question
- THEN the response status is 200
- AND the response contains a non-empty answer

#### Scenario: CORS header test

- GIVEN a running API
- WHEN `OPTIONS /api/ask` is requested from an allowed origin
- THEN the response contains the expected CORS headers
