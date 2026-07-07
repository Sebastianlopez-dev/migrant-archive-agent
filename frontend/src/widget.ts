/**
 * Embeddable Cero chat widget custom element.
 *
 * This entrypoint is built as a self-contained IIFE so any plain HTML site
 * can install Cero with two lines of code:
 *
 *   <script src="https://chatbot.plataformacero.org/cero-widget.iife.js"></script>
 *   <cero-chat-widget api-base-url="https://chatbot.plataformacero.org"></cero-chat-widget>
 */

import inlineStyles from './styles.css?inline';
import { ChatWidget } from './chat-widget.ts';

function getScriptOrigin(): string {
  try {
    const script = document.currentScript as HTMLScriptElement | null;
    if (script?.src) {
      return new URL(script.src, document.baseURI).origin;
    }
  } catch {
    // Ignore malformed script URLs.
  }
  return '';
}

const WIDGET_SCRIPT_ORIGIN = getScriptOrigin();

export class CeroChatWidget extends HTMLElement {
  static readonly tagName = 'cero-chat-widget';
  private widget: ChatWidget | null = null;

  constructor() {
    super();
    // Attach the shadow root once during construction so it survives
    // disconnect/reconnect cycles. Calling attachShadow again after the
    // element has been connected would throw a NotSupportedError.
    this.attachShadow({ mode: 'open' });
  }

  connectedCallback(): void {
    if (this.widget) return;

    const shadow = this.shadowRoot;
    if (!shadow) return;

    const style = document.createElement('style');
    style.textContent = inlineStyles;
    shadow.appendChild(style);

    const container = document.createElement('div');
    container.className = 'chat-widget-root';
    shadow.appendChild(container);

    const apiBaseUrl = this.getAttribute('api-base-url') ?? undefined;
    const assetBaseUrl = this.getAttribute('asset-base-url') ?? WIDGET_SCRIPT_ORIGIN;

    this.widget = new ChatWidget(container, { apiBaseUrl, assetBaseUrl });
  }

  disconnectedCallback(): void {
    this.widget?.destroy();
    this.widget = null;
    if (this.shadowRoot) {
      this.shadowRoot.innerHTML = '';
    }
  }
}

if (!customElements.get(CeroChatWidget.tagName)) {
  customElements.define(CeroChatWidget.tagName, CeroChatWidget);
}
