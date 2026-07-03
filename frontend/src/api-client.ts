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
 * Build a full API URL from an optional base URL and a path.
 *
 * An empty base preserves the existing relative-path behavior, while a
 * remote base is normalized so the path never starts with a double slash.
 */
export function buildApiUrl(path: string, apiBaseUrl: string): string {
  const base = apiBaseUrl.replace(/\/+$/, '');
  return base ? `${base}${path}` : path;
}

/**
 * Send a question to `/api/ask` and return the typed response.
 *
 * The request is aborted automatically after 60 seconds. An optional external
 * `signal` can also abort the request. Non-200 responses, network failures,
 * and aborts are normalized into `ApiClientError`.
 */
export async function ask(
  sessionId: string,
  question: string,
  language = 'en',
  apiBaseUrl = '',
  signal?: AbortSignal,
): Promise<AskResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ASK_TIMEOUT_MS);

  function onExternalAbort(): void {
    controller.abort();
  }

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener('abort', onExternalAbort, { once: true });
    }
  }

  try {
    const response = await fetch(buildApiUrl('/api/ask', apiBaseUrl), {
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
    if (signal && !signal.aborted) {
      signal.removeEventListener('abort', onExternalAbort);
    }
  }
}

/**
 * Clear the chat history for a session on the backend.
 *
 * Best-effort: failures are silently ignored since a new session id
 * will be generated regardless. The backend cleans up orphaned sessions
 * when the server restarts.
 */
export async function clearSession(sessionId: string, apiBaseUrl = ''): Promise<void> {
  try {
    await fetch(
      buildApiUrl(`/api/session/${encodeURIComponent(sessionId)}`, apiBaseUrl),
      {
        method: 'DELETE',
      },
    );
  } catch {
    // Best-effort cleanup — ignore network errors.
  }
}


