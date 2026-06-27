/**
 * Chat widget orchestrator.
 *
 * Brings together the FAB, panel, zero-state, input bar, and message list
 * modules into a single stateful component. All rendering is delegated to the
 * focused ES modules; this class only manages state, wiring, and the backend
 * API call.
 */

import { ask, ApiClientError } from './api-client.ts';
import { createFab } from './fab.ts';
import { createPanel, type PanelSlots } from './panel.ts';
import { createZeroState } from './zero-state.ts';
import { createInputBar, type InputBarApi } from './input-bar.ts';
import { createMessageList, type MessageListApi } from './message-list.ts';

export class ChatWidget {
  private readonly root: HTMLElement;
  private readonly sessionId: string;
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
    this.panelSlots = createPanel(() => this.closePanel());
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

  private updateVisibility(): void {
    this.panelSlots.element.style.display = this.isOpen ? 'flex' : 'none';
    this.fab.style.display = this.isOpen ? 'none' : 'flex';
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
