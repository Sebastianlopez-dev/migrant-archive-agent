/**
 * Typed API client for the chat backend.
 *
 * This module is the single source of truth for the frontend-to-backend
 * contract exposed by `POST /api/ask`. It deliberately has no runtime
 * dependencies so it can be imported by any widget module without bloating
 * the bundle.
 */

/** A single transcript source returned with an agent answer. */
export interface Source {
  video_id: string;
  title: string;
  start_time: string;
  end_time: string;
  text: string;
}

/** Response body for `POST /api/ask`. */
export interface AskResponse {
  answer: string;
  sources: Source[];
}

/** Internal message representation used by the chat widget. */
export interface Message {
  id: string;
  sender: 'user' | 'agent' | 'error';
  text: string;
  sources?: Source[];
}

/** Error raised by the API client when a request cannot be completed. */
export class ApiClientError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
  }
}

const ASK_TIMEOUT_MS = 60_000;

/**
 * Send a question to `/api/ask` and return the typed response.
 *
 * The request is aborted automatically after 60 seconds. Non-200 responses,
 * network failures, and aborts are normalized into `ApiClientError`.
 */
export async function ask(sessionId: string, question: string, language = 'en'): Promise<AskResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);

  try {
    const response = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId, language }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.text();
      throw new ApiClientError(
        `Request failed: ${response.status} ${body || response.statusText}`,
        response.status
      );
    }

    return (await response.json()) as AskResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiClientError(
        'The response is taking too long. Try a more specific question.'
      );
    }

    if (error instanceof ApiClientError) {
      throw error;
    }

    throw new ApiClientError(
      error instanceof Error ? error.message : 'Could not reach the assistant.'
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Clear the chat history for a session on the backend.
 *
 * Best-effort: failures are silently ignored since a new session id
 * will be generated regardless. The backend cleans up orphaned sessions
 * when the server restarts.
 */
export async function clearSession(sessionId: string): Promise<void> {
  try {
    await fetch(`/api/session/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    });
  } catch {
    // Best-effort cleanup — ignore network errors.
  }
}


