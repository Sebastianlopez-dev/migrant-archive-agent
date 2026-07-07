/**
 * Chat widget orchestrator.
 *
 * Brings together the FAB, panel, zero-state, input bar, and message list
 * modules into a single stateful component. All rendering is delegated to the
 * focused ES modules; this class only manages state, wiring, and the backend
 * API call.
 */

import { ask, clearSession } from './api-client.ts';
import { createFab, type FabApi } from './fab.ts';
import { createPanel, type PanelSlots } from './panel.ts';
import { createZeroState, SUPPORTED_LANGUAGES, type ZeroStateElement } from './zero-state.ts';
import { createInputBar, type InputBarApi } from './input-bar.ts';
import { createMessageList, type MessageListApi } from './message-list.ts';

function generateSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  const fallback = (): string => {
    const s4 = (): string => {
      const value = typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function'
        ? crypto.getRandomValues(new Uint8Array(1))[0] % 16
        : Math.floor(Math.random() * 16);
      return value.toString(16);
    };
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = s4();
      const v = c === 'x' ? r : ((parseInt(r, 16) & 0x3) | 0x8).toString(16);
      return v;
    });
  };

  return fallback();
}

const LANG_STORAGE_KEY = 'cero-widget-lang';
const LEGACY_LANG_STORAGE_KEY = 'migrant-archive-lang';

function getSavedLanguage(): string | null {
  const current = localStorage.getItem(LANG_STORAGE_KEY);
  if (current) return current;
  return localStorage.getItem(LEGACY_LANG_STORAGE_KEY);
}

const CONFIRM_RESET: Record<string, string> = {
  en: 'Delete this conversation and start over?',
  es: '¿Querés borrar la conversación y empezar de cero?',
  ca: 'Vols esborrar la conversa i començar de zero?',
  fr: 'Supprimer cette conversation et recommencer ?',
  pt: 'Apagar esta conversa e começar de novo?',
  de: 'Diese Unterhaltung löschen und neu beginnen?',
};

const ERROR_MESSAGES: Record<string, string> = {
  en: 'Could not reach the assistant.',
  es: 'No se pudo contactar al asistente.',
  ca: "No s'ha pogut contactar amb l'assistent.",
  fr: "Impossible de contacter l'assistant.",
  pt: 'Não foi possível contactar o assistente.',
  de: 'Der Assistent konnte nicht erreicht werden.',
};

export interface ChatWidgetOptions {
  apiBaseUrl?: string;
  assetBaseUrl?: string;
}

export class ChatWidget {
  private readonly root: HTMLElement;
  private readonly apiBaseUrl: string;
  private readonly assetBaseUrl: string;
  private sessionId: string;
  private readonly fab: FabApi;
  private readonly panelSlots: PanelSlots;
  private readonly inputBar: InputBarApi;
  private readonly messageList: MessageListApi;
  private readonly zeroState: ZeroStateElement;
  private readonly keydownHandler: (event: KeyboardEvent) => void;
  private isOpen = false;
  private hasStarted = false;
  private isLoading = false;
  private language = 'en';
  private destroyed = false;
  private activeAskController: AbortController | null = null;

  constructor(root: HTMLElement);
  constructor(root: HTMLElement, options?: ChatWidgetOptions);
  constructor(root: HTMLElement, options?: ChatWidgetOptions) {
    this.root = root;
    this.apiBaseUrl = options?.apiBaseUrl ?? '';
    this.assetBaseUrl = options?.assetBaseUrl ?? '';
    this.root.classList.add('chat-widget');
    this.root.setAttribute('data-theme', 'light');
    this.sessionId = generateSessionId();

    const savedLang = getSavedLanguage();
    if (savedLang && (SUPPORTED_LANGUAGES as readonly string[]).includes(savedLang)) {
      this.language = savedLang;
    }

    this.fab = createFab(this.language, () => this.openPanel(), this.assetBaseUrl);
    this.panelSlots = createPanel(
      () => this.closePanel(),
      () => this.resetConversation(),
      (lang) => this.setLanguage(lang),
      this.language,
      this.assetBaseUrl,
    );
    this.zeroState = createZeroState(this.language, (question) => this.selectSuggestion(question));
    this.inputBar = createInputBar(
      this.language,
      (question) => this.sendMessage(question),
      this.apiBaseUrl,
    );
    this.messageList = createMessageList(this.language);

    this.panelSlots.contentSlot.appendChild(this.zeroState);
    this.panelSlots.footerSlot.appendChild(this.inputBar.element);

    this.root.appendChild(this.fab.element);
    this.root.appendChild(this.panelSlots.element);

    this.updateVisibility();

    this.keydownHandler = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && this.isOpen) {
        this.closePanel();
      }
    };
    document.addEventListener('keydown', this.keydownHandler);
  }

  openPanel(): void {
    if (this.isOpen) return;
    this.isOpen = true;
    this.updateVisibility();
    this.inputBar.focus();
  }

  closePanel(): void {
    if (!this.isOpen) return;
    this.isOpen = false;
    this.updateVisibility();
    this.fab.element.focus();
  }

  togglePanel(): void {
    if (this.isOpen) {
      this.closePanel();
    } else {
      this.openPanel();
    }
  }

  setLanguage(lang: string): void {
    if (!(SUPPORTED_LANGUAGES as readonly string[]).includes(lang)) return;
    if (this.language === lang) return;
    this.language = lang;
    localStorage.setItem(LANG_STORAGE_KEY, lang);
    this.fab.setLanguage(lang);
    this.inputBar.setLanguage(lang);
    this.messageList.setLanguage(lang);
    this.panelSlots.setLanguage(lang);
    this.zeroState.updateLanguage(lang);

    if (this.hasStarted) {
      this._doReset();
    }
  }

  resetConversation(): void {
    if (!this.hasStarted) return;

    const confirmed = window.confirm(
      CONFIRM_RESET[this.language] || CONFIRM_RESET.en,
    );
    if (!confirmed) return;

    this._doReset();
    this.inputBar.focus();
  }

  private _doReset(): void {
    void clearSession(this.sessionId, this.apiBaseUrl);

    this.isLoading = false;
    this.inputBar.setLoading(false);
    this.messageList.clear();
    this.hasStarted = false;
    this.sessionId = generateSessionId();

    if (this.panelSlots.contentSlot.contains(this.messageList.element)) {
      this.panelSlots.contentSlot.removeChild(this.messageList.element);
    }
    this.panelSlots.contentSlot.appendChild(this.zeroState);
  }

  private updateVisibility(): void {
    if (this.isOpen) {
      this.panelSlots.element.classList.add('chat-panel--visible');
      this.fab.element.style.display = 'none';
    } else {
      this.panelSlots.element.classList.remove('chat-panel--visible');
      this.fab.element.style.display = 'flex';
    }
    this.fab.element.setAttribute('aria-expanded', String(this.isOpen));
  }

  selectSuggestion(question: string): void {
    this.inputBar.setQuestion(question);
    this.sendMessage(question);
  }

  async sendMessage(question: string): Promise<void> {
    if (this.isLoading || this.destroyed) return;

    const text = question.trim();
    if (!text) return;

    if (!this.hasStarted) {
      this.hasStarted = true;
      this.panelSlots.contentSlot.removeChild(this.zeroState);
      this.panelSlots.contentSlot.appendChild(this.messageList.element);
    }

    this.messageList.addUserMessage(text);
    this.inputBar.clear();
    this.setLoading(true);

    const controller = new AbortController();
    this.activeAskController = controller;

    try {
      const response = await ask(this.sessionId, text, this.language, this.apiBaseUrl, controller.signal);
      if (this.destroyed || controller.signal.aborted) return;
      this.messageList.addAgentResponse(response);
    } catch (error) {
      if (this.destroyed || controller.signal.aborted) return;
      void error; // ApiClientError details are logged but not shown to the user.
      const message = ERROR_MESSAGES[this.language] || ERROR_MESSAGES.en;
      this.messageList.addErrorMessage(message);
    } finally {
      this.activeAskController = null;
      if (!this.destroyed) {
        this.setLoading(false);
        this.inputBar.focus();
      }
    }
  }

  private setLoading(isLoading: boolean): void {
    this.isLoading = isLoading;
    this.inputBar.setLoading(isLoading);
    this.messageList.setLoading(isLoading);
  }

  destroy(): void {
    this.destroyed = true;
    this.activeAskController?.abort();
    this.activeAskController = null;
    document.removeEventListener('keydown', this.keydownHandler);
    this.inputBar.destroy();
    this.messageList.destroy();
    this.panelSlots.destroy();
    this.root.innerHTML = '';
  }
}
