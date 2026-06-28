/**
 * Chat widget orchestrator.
 *
 * Brings together the FAB, panel, zero-state, input bar, and message list
 * modules into a single stateful component. All rendering is delegated to the
 * focused ES modules; this class only manages state, wiring, and the backend
 * API call.
 */

import { ask, clearSession, ApiClientError } from './api-client.ts';
import { createFab } from './fab.ts';
import { createPanel, type PanelSlots } from './panel.ts';
import { createZeroState } from './zero-state.ts';
import { createInputBar, type InputBarApi } from './input-bar.ts';
import { createMessageList, type MessageListApi } from './message-list.ts';

export class ChatWidget {
  private readonly root: HTMLElement;
  private sessionId: string;
  private readonly fab: HTMLButtonElement;
  private readonly panelSlots: PanelSlots;
  private readonly inputBar: InputBarApi;
  private readonly messageList: MessageListApi;
  private readonly zeroState: HTMLElement;
  private isOpen = false;
  private hasStarted = false;
  private isLoading = false;

  constructor(root: HTMLElement) {
    this.root = root;
    this.root.classList.add('chat-widget');
    this.sessionId = crypto.randomUUID();

    this.fab = createFab(() => this.openPanel());
    this.panelSlots = createPanel(
      () => this.closePanel(),
      () => this.resetConversation(),
    );
    this.zeroState = createZeroState((question) => this.selectSuggestion(question));
    this.inputBar = createInputBar((question) => this.sendMessage(question));
    this.messageList = createMessageList();

    this.panelSlots.contentSlot.appendChild(this.zeroState);
    this.panelSlots.footerSlot.appendChild(this.inputBar.element);

    this.root.appendChild(this.fab);
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
    this.fab.focus();
  }

  togglePanel(): void {
    if (this.isOpen) {
      this.closePanel();
    } else {
      this.openPanel();
    }
  }

  resetConversation(): void {
    if (!this.hasStarted) return;

    const confirmed = window.confirm(
      '¿Querés borrar la conversación y empezar de cero?',
    );
    if (!confirmed) return;

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

    this.inputBar.focus();
  }

  private updateVisibility(): void {
    if (this.isOpen) {
      this.panelSlots.element.classList.add('chat-panel--visible');
      this.fab.style.display = 'none';
    } else {
      this.panelSlots.element.classList.remove('chat-panel--visible');
      this.fab.style.display = 'flex';
    }
    this.fab.setAttribute('aria-expanded', String(this.isOpen));
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
      const response = await ask(this.sessionId, text);
      this.messageList.addAgentResponse(response);
    } catch (error) {
      const message =
        error instanceof ApiClientError
          ? error.message
          : 'No se pudo contactar al asistente.';
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
