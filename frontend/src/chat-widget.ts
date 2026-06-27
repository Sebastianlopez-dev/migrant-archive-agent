export interface Source {
  video_id: string;
  title: string;
  start_time: string;
  end_time: string;
  text: string;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

export class ChatWidget {
  private readonly root: HTMLElement;
  private readonly sessionId: string;
  private panel: HTMLElement | null = null;
  private messages: HTMLElement | null = null;
  private input: HTMLInputElement | null = null;
  private sendButton: HTMLButtonElement | null = null;
  private isOpen = false;

  constructor(root: HTMLElement) {
    this.root = root;
    this.sessionId = crypto.randomUUID();
    this.root.classList.add('chat-widget');
    this.createBubble();
    this.createPanel();
  }

  createBubble(): void {
    const bubble = document.createElement('button');
    bubble.className = 'chat-bubble';
    bubble.setAttribute('aria-label', 'Abrir chat con Cerito');
    bubble.setAttribute('aria-expanded', 'false');
    bubble.setAttribute('aria-controls', 'chat-panel');

    const avatar = document.createElement('img');
    avatar.src = '/cerito-avatar.svg';
    avatar.alt = 'Cerito';
    bubble.appendChild(avatar);

    bubble.addEventListener('click', () => this.togglePanel());
    this.root.appendChild(bubble);
  }

  createPanel(): void {
    const panel = document.createElement('section');
    panel.id = 'chat-panel';
    panel.className = 'chat-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Chat con Cerito');

    const header = document.createElement('header');
    header.className = 'chat-panel-header';

    const title = document.createElement('h2');
    title.className = 'chat-panel-title';

    const titleAvatar = document.createElement('img');
    titleAvatar.src = '/cerito-avatar.svg';
    titleAvatar.alt = '';
    title.appendChild(titleAvatar);
    title.appendChild(document.createTextNode('Cerito'));

    const closeButton = document.createElement('button');
    closeButton.className = 'chat-panel-close';
    closeButton.setAttribute('aria-label', 'Cerrar chat');
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', () => this.closePanel());

    header.appendChild(title);
    header.appendChild(closeButton);

    this.messages = document.createElement('div');
    this.messages.className = 'chat-messages';
    this.messages.setAttribute('role', 'log');
    this.messages.setAttribute('aria-live', 'polite');

    const inputArea = document.createElement('div');
    inputArea.className = 'chat-input-area';

    this.input = document.createElement('input');
    this.input.className = 'chat-input';
    this.input.type = 'text';
    this.input.placeholder = 'Escribí tu pregunta…';
    this.input.setAttribute('aria-label', 'Mensaje');
    this.input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        this.sendMessage();
      }
    });

    this.sendButton = document.createElement('button');
    this.sendButton.className = 'chat-send';
    this.sendButton.type = 'button';
    this.sendButton.textContent = 'Enviar';
    this.sendButton.addEventListener('click', () => this.sendMessage());

    inputArea.appendChild(this.input);
    inputArea.appendChild(this.sendButton);

    panel.appendChild(header);
    panel.appendChild(this.messages);
    panel.appendChild(inputArea);

    this.panel = panel;
    this.root.appendChild(panel);
  }

  togglePanel(): void {
    this.isOpen = !this.isOpen;
    this.updatePanelState();
  }

  openPanel(): void {
    this.isOpen = true;
    this.updatePanelState();
  }

  closePanel(): void {
    this.isOpen = false;
    this.updatePanelState();
  }

  private updatePanelState(): void {
    if (!this.panel) return;
    this.panel.classList.toggle('is-open', this.isOpen);

    const bubble = this.root.querySelector('.chat-bubble');
    if (bubble) {
      bubble.setAttribute('aria-expanded', String(this.isOpen));
      bubble.setAttribute(
        'aria-label',
        this.isOpen ? 'Cerrar chat con Cerito' : 'Abrir chat con Cerito'
      );
    }

    if (this.isOpen && this.input) {
      this.input.focus();
    }
  }

  async sendMessage(): Promise<void> {
    if (!this.input || !this.messages) return;

    const question = this.input.value.trim();
    if (!question) return;

    this.renderMessage(question, 'user');
    this.input.value = '';
    this.setLoading(true);

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 60_000);
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: this.sessionId }),
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Error ${response.status}: ${errorBody || response.statusText}`);
      }

      const data: AskResponse = await response.json();
      this.renderMessage(data.answer, 'agent', data.sources);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'No se pudo contactar al asistente.';
      this.renderMessage(message, 'error');
    } finally {
      this.setLoading(false);
    }
  }

  private setLoading(isLoading: boolean): void {
    if (this.input) this.input.disabled = isLoading;
    if (this.sendButton) {
      this.sendButton.disabled = isLoading;
      this.sendButton.textContent = isLoading ? 'Enviando…' : 'Enviar';
    }
  }

  renderMessage(text: string, sender: 'user' | 'agent' | 'error', sources?: Source[]): void {
    if (!this.messages) return;

    const message = document.createElement('div');
    message.className = `chat-message chat-message--${sender}`;

    const bubble = document.createElement('div');
    bubble.className = 'chat-message-bubble';

    if (sender === 'agent' && sources && sources.length > 0) {
      bubble.innerHTML = this.linkifySources(text, sources);
    } else {
      bubble.textContent = text;
    }
    message.appendChild(bubble);

    if (sender === 'agent' && sources && sources.length > 0) {
      const sourcesBlock = this.createSourcesBlock(sources);
      message.appendChild(sourcesBlock);
    }

    this.messages.appendChild(message);
    this.messages.scrollTop = this.messages.scrollHeight;
  }

  private createSourcesBlock(sources: Source[]): HTMLElement {
    const block = document.createElement('div');
    block.className = 'chat-sources';

    const title = document.createElement('p');
    title.className = 'chat-sources-title';
    title.textContent = 'Fuentes';
    block.appendChild(title);

    for (const source of sources) {
      const item = document.createElement('div');
      item.className = 'chat-source';

      const link = document.createElement('a');
      link.href = this.buildSourceUrl(source.video_id, source.start_time);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = source.title || source.video_id;
      link.title = 'Abrir en YouTube';

      const external = document.createElement('span');
      external.setAttribute('aria-hidden', 'true');
      external.style.cssText = 'font-size:0.75rem;margin-left:2px;';
      external.textContent = ' ↗';

      const meta = document.createElement('span');
      meta.className = 'chat-source-time';
      meta.textContent = ` (${source.start_time} – ${source.end_time})`;

      const excerpt = document.createElement('p');
      excerpt.textContent = source.text;

      item.appendChild(link);
      item.appendChild(external);
      item.appendChild(meta);
      item.appendChild(excerpt);
      block.appendChild(item);
    }

    return block;
  }

  private buildSourceUrl(videoId: string, startTime: string): string {
    const seconds = this.parseTimeToSeconds(startTime);
    const base = `https://www.youtube.com/watch?v=${videoId}`;
    return seconds > 0 ? `${base}&t=${seconds}` : base;
  }

  private linkifySources(text: string, sources: Source[]): string {
    let html = this.escapeHtml(text);
    for (const source of sources) {
      const url = this.buildSourceUrl(source.video_id, source.start_time);
      const link = `<a href="${url}" target="_blank" rel="noopener noreferrer" title="Abrir en YouTube">${this.escapeHtml(source.video_id)}</a>`;
      // Replace bare video_id with clickable link
      html = html.replace(
        new RegExp(`\\b${this.escapeRegex(source.video_id)}\\b`, 'g'),
        link
      );
    }
    return html;
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  private escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  private parseTimeToSeconds(time: string): number {
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
}
