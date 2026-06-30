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

export class ChatWidget {
  private readonly root: HTMLElement;
  private sessionId: string;
  private readonly fab: FabApi;
  private readonly panelSlots: PanelSlots;
  private readonly inputBar: InputBarApi;
  private readonly messageList: MessageListApi;
  private readonly zeroState: ZeroStateElement;
  private isOpen = false;
  private hasStarted = false;
  private isLoading = false;
  private language = 'en';

  constructor(root: HTMLElement) {
    this.root = root;
    this.root.classList.add('chat-widget');
    this.sessionId = crypto.randomUUID();

    const savedLang = localStorage.getItem('migrant-archive-lang');
    if (savedLang && (SUPPORTED_LANGUAGES as readonly string[]).includes(savedLang)) {
      this.language = savedLang;
    }

    this.fab = createFab(this.language, () => this.openPanel());
    this.panelSlots = createPanel(
      () => this.closePanel(),
      () => this.resetConversation(),
      (lang) => this.setLanguage(lang),
      this.language,
    );
    this.zeroState = createZeroState(this.language, (question) => this.selectSuggestion(question));
    this.inputBar = createInputBar(this.language, (question) => this.sendMessage(question));
    this.messageList = createMessageList(this.language);

    this.panelSlots.contentSlot.appendChild(this.zeroState);
    this.panelSlots.footerSlot.appendChild(this.inputBar.element);

    this.root.appendChild(this.fab.element);
    this.root.appendChild(this.panelSlots.element);

    this.updateVisibility();

    document.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.key === 'Escape' && this.isOpen) {
        this.closePanel();
      }
    });
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
    localStorage.setItem('migrant-archive-lang', lang);
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
    void clearSession(this.sessionId);

    this.isLoading = false;
    this.inputBar.setLoading(false);
    this.messageList.clear();
    this.hasStarted = false;
    this.sessionId = crypto.randomUUID();

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
    if (this.isLoading) return;

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

    try {
      const response = await ask(this.sessionId, text, this.language);
      this.messageList.addAgentResponse(response);
    } catch (error) {
      void error; // ApiClientError details are logged but not shown to the user.
      const message = ERROR_MESSAGES[this.language] || ERROR_MESSAGES.en;
      this.messageList.addErrorMessage(message);
    } finally {
      this.setLoading(false);
      this.inputBar.focus();
    }
  }

  private setLoading(isLoading: boolean): void {
    this.isLoading = isLoading;
    this.inputBar.setLoading(isLoading);
    this.messageList.setLoading(isLoading);
  }
}
