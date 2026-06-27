/**
 * Message list module for the chat widget.
 *
 * Renders the conversation history (user messages and agent responses) in a
 * scrollable container. Agent responses can include source citation cards that
 * link back to the referenced YouTube videos at the matching start time.
 *
 * No animations, transitions, or JavaScript-driven motion are used.
 */

import type { AskResponse, Source } from './api-client';

/** Public API exposed by `createMessageList`. */
export interface MessageListApi {
  /** The root message list element. */
  element: HTMLElement;
  /** Append a user-styled message bubble. */
  addUserMessage: (text: string) => void;
  /** Append an agent answer plus optional source citations. */
  addAgentResponse: (response: AskResponse) => void;
  /** Show or hide the static loading indicator. */
  setLoading: (isLoading: boolean) => void;
  /** Append an error-styled message bubble. */
  addErrorMessage: (text: string) => void;
  /** Remove every rendered message. */
  clear: () => void;
}

const LOADING_TEXT = 'Cero está pensando...';

/**
 * Create the scrollable message list.
 *
 * @returns The message list element and the methods used to populate it.
 */
export function createMessageList(): MessageListApi {
  const element = document.createElement('div');
  element.className = 'chat-messages';
  element.setAttribute('role', 'log');
  element.setAttribute('aria-live', 'polite');
  element.style.overflowY = 'auto';

  let loadingIndicator: HTMLElement | null = null;

  function scrollToBottom(): void {
    element.scrollTop = element.scrollHeight;
  }

  function appendBubble(className: string): HTMLElement {
    const bubble = document.createElement('div');
    bubble.className = className;
    element.appendChild(bubble);
    return bubble;
  }

  function addUserMessage(text: string): void {
    const bubble = appendBubble('msg-user');
    bubble.textContent = text;
    scrollToBottom();
  }

  function addErrorMessage(text: string): void {
    const bubble = appendBubble('msg-error');
    bubble.textContent = text;
    scrollToBottom();
  }

  function addAgentResponse(response: AskResponse): void {
    const bubble = appendBubble('msg-agent');
    bubble.innerHTML = linkifySources(response.answer, response.sources);

    if (response.sources && response.sources.length > 0) {
      const sourcesBlock = document.createElement('div');
      sourcesBlock.className = 'msg-sources';

      for (const source of response.sources) {
        sourcesBlock.appendChild(createSourceCard(source));
      }

      element.appendChild(sourcesBlock);
    }

    scrollToBottom();
  }

  function createSourceCard(source: Source): HTMLElement {
    const card = document.createElement('div');
    card.className = 'msg-source';

    const header = document.createElement('div');
    header.className = 'msg-source-header';

    const videoLabel = document.createElement('span');
    videoLabel.className = 'msg-source-label';
    videoLabel.textContent = 'Video:';

    const videoId = document.createElement('span');
    videoId.className = 'msg-source-video-id';
    videoId.textContent = source.video_id;

    const title = document.createElement('a');
    title.className = 'msg-source-title';
    title.href = buildSourceUrl(source.video_id, source.start_time);
    title.target = '_blank';
    title.rel = 'noopener noreferrer';
    title.textContent = source.title;
    title.setAttribute('aria-label', `Abrir ${source.title} en YouTube`);

    header.appendChild(videoLabel);
    header.appendChild(videoId);
    header.appendChild(document.createTextNode(' — '));
    header.appendChild(title);

    const time = document.createElement('div');
    time.className = 'msg-source-time';

    const timeLabel = document.createElement('span');
    timeLabel.className = 'msg-source-label';
    timeLabel.textContent = 'Time:';

    const timeRange = document.createElement('span');
    timeRange.textContent = `${source.start_time} – ${source.end_time}`;

    time.appendChild(timeLabel);
    time.appendChild(timeRange);

    const excerpt = document.createElement('blockquote');
    excerpt.className = 'msg-source-excerpt';
    excerpt.textContent = source.text;

    card.appendChild(header);
    card.appendChild(time);
    card.appendChild(excerpt);

    return card;
  }

  function setLoading(isLoading: boolean): void {
    if (isLoading) {
      if (!loadingIndicator) {
        loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'msg-loading';
        loadingIndicator.textContent = LOADING_TEXT;
      }
      element.appendChild(loadingIndicator);
      scrollToBottom();
      return;
    }

    if (loadingIndicator && loadingIndicator.parentNode === element) {
      element.removeChild(loadingIndicator);
    }
  }

  function clear(): void {
    element.innerHTML = '';
    loadingIndicator = null;
  }

  return { element, addUserMessage, addAgentResponse, setLoading, addErrorMessage, clear };
}

function buildSourceUrl(videoId: string, startTime: string): string {
  const seconds = parseTimeToSeconds(startTime);
  const base = `https://www.youtube.com/watch?v=${videoId}`;
  return seconds > 0 ? `${base}&t=${seconds}` : base;
}

function parseTimeToSeconds(time: string): number {
  const parts = time.split(':').map(Number);
  if (parts.some(isNaN)) return 0;

  if (parts.length === 3) {
    return parts[0] * 3600 + parts[1] * 60 + parts[2];
  }
  if (parts.length === 2) {
    return parts[0] * 60 + parts[1];
  }
  return parts[0] || 0;
}

function linkifySources(text: string, sources: Source[]): string {
  let html = escapeHtml(text);

  for (const source of sources) {
    const url = buildSourceUrl(source.video_id, source.start_time);
    const link = `<a href="${url}" target="_blank" rel="noopener noreferrer" title="Abrir en YouTube">${escapeHtml(source.video_id)}</a>`;
    html = html.replace(
      new RegExp(`\\b${escapeRegex(source.video_id)}\\b`, 'g'),
      link
    );
  }

  return html;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
