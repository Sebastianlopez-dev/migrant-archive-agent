/**
 * Message list module for the chat widget.
 *
 * Renders the conversation history (user messages and agent responses) in a
 * scrollable container. Agent responses can include source citation cards that
 * link back to the referenced YouTube videos at the matching start time.
 *
 * No animations, transitions, or JavaScript-driven motion are used.
 */

import type { AskResponse } from './api-client';

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
  /** Update display language for the loading indicator. */
  setLanguage: (lang: string) => void;
}

const LOADING_I18N: Record<string, string> = {
  en: 'Cero is thinking...',
  es: 'Cero está pensando...',
  ca: 'Cero està pensant...',
  fr: 'Cero réfléchit...',
  pt: 'Cero está a pensar...',
  de: 'Cero denkt nach...',
};

/**
 * Create the scrollable message list.
 *
 * @param language - ISO code for the display language (default: `en`).
 * @returns The message list element and the methods used to populate it.
 */
export function createMessageList(language = 'en'): MessageListApi {
  let currentLanguage = language;

  const element = document.createElement('div');
  element.className = 'chat-messages';
  element.setAttribute('role', 'log');
  element.setAttribute('aria-live', 'polite');
  element.style.overflowY = 'auto';

  let loadingIndicator: HTMLElement | null = null;

  function getLoadingText(): string {
    return LOADING_I18N[currentLanguage] || LOADING_I18N.en;
  }

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
    bubble.innerHTML = response.answer;
    scrollToBottom();
  }

  function setLoading(isLoading: boolean): void {
    if (isLoading) {
      if (!loadingIndicator) {
        loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'msg-loading';
        loadingIndicator.textContent = getLoadingText();
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

  function setLanguage(lang: string): void {
    currentLanguage = lang;
    if (loadingIndicator && loadingIndicator.parentNode === element) {
      loadingIndicator.textContent = getLoadingText();
    }
  }

  return { element, addUserMessage, addAgentResponse, setLoading, addErrorMessage, clear, setLanguage };
}
