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
  /** Show or hide the rotating loading indicator. */
  setLoading: (isLoading: boolean) => void;
  /** Append an error-styled message bubble. */
  addErrorMessage: (text: string) => void;
  /** Remove every rendered message. */
  clear: () => void;
  /** Update display language for the loading indicator. */
  setLanguage: (lang: string) => void;
}

const LOADING_I18N: Record<string, string[]> = {
  en: [
    'Consulting the archive...',
    'Cero is reviewing testimonies...',
    'Cross-referencing oral histories...',
    'Tracing stories through the archive...',
  ],
  es: [
    'Consultando el archivo...',
    'Cero está revisando testimonios...',
    'Cotejando historias orales...',
    'Rastreando relatos en el archivo...',
  ],
  ca: [
    'Consultant l\'arxiu...',
    'Cero està revisant testimonis...',
    'Constrastant històries orals...',
    'Resseguint relats a l\'arxiu...',
  ],
  fr: [
    'Consultation des archives...',
    'Cero examine les témoignages...',
    'Recoupement des histoires orales...',
    'Parcours des récits dans les archives...',
  ],
  pt: [
    'Consultando o arquivo...',
    'Cero está a rever os testemunhos...',
    'Cruzando histórias orais...',
    'Percorrendo relatos no arquivo...',
  ],
  de: [
    'Archiv wird konsultiert...',
    'Cero sichtet die Zeugnisse...',
    'Mündliche Überlieferungen werden abgeglichen...',
    'Geschichten im Archiv werden nachverfolgt...',
  ],
};

/**
 * Create the scrollable message list.
 *
 * @param language - ISO code for the display language (default: `en`).
 * @returns The message list element and the methods used to populate it.
 */
const ROTATION_INTERVAL_MS = 2500;

export function createMessageList(language = 'en'): MessageListApi {
  let currentLanguage = language;

  const element = document.createElement('div');
  element.className = 'chat-messages';
  element.setAttribute('role', 'log');
  element.setAttribute('aria-live', 'polite');
  element.style.overflowY = 'auto';

  let loadingIndicator: HTMLElement | null = null;
  let rotationTimer: ReturnType<typeof setInterval> | null = null;
  let rotationIndex = 0;

  function getLoadingText(): string {
    const messages = LOADING_I18N[currentLanguage] || LOADING_I18N.en;
    return messages[rotationIndex % messages.length];
  }

  function stopRotation(): void {
    if (rotationTimer) {
      clearInterval(rotationTimer);
      rotationTimer = null;
    }
  }

  function startRotation(): void {
    if (rotationTimer) return;
    rotationTimer = setInterval(() => {
      rotationIndex += 1;
      if (loadingIndicator) {
        loadingIndicator.textContent = getLoadingText();
      }
    }, ROTATION_INTERVAL_MS);
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
      }
      rotationIndex = 0;
      loadingIndicator.textContent = getLoadingText();
      element.appendChild(loadingIndicator);
      scrollToBottom();
      startRotation();
      return;
    }

    stopRotation();
    if (loadingIndicator && loadingIndicator.parentNode === element) {
      element.removeChild(loadingIndicator);
    }
  }

  function clear(): void {
    stopRotation();
    element.innerHTML = '';
    loadingIndicator = null;
    rotationIndex = 0;
  }

  function setLanguage(lang: string): void {
    currentLanguage = lang;
    if (loadingIndicator && loadingIndicator.parentNode === element) {
      if (rotationTimer) {
        stopRotation();
        rotationIndex = 0;
        loadingIndicator.textContent = getLoadingText();
        startRotation();
      } else {
        loadingIndicator.textContent = getLoadingText();
      }
    }
  }

  return { element, addUserMessage, addAgentResponse, setLoading, addErrorMessage, clear, setLanguage };
}
