/**
 * Panel shell module for the chat widget.
 *
 * Renders the fixed right-side panel that hosts the conversation. It exposes
 * a content slot for messages/zero-state and a footer slot for the input bar.
 * The panel is intentionally stateless: the orchestrator toggles visibility.
 */

const REFRESH_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`;

const CLOSE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

/** References to the panel and its two placeholder regions. */
export interface PanelSlots {
  /** The root panel element (section#chat-panel). */
  element: HTMLElement;
  /** Container where messages or the zero-state are rendered. */
  contentSlot: HTMLElement;
  /** Container where the input bar is rendered. */
  footerSlot: HTMLElement;
}

/**
 * Create the chat panel shell.
 *
 * @param onClose - Callback invoked when the user clicks the close button
 *                  or presses Escape inside the panel.
 * @param onRefresh - Callback invoked when the user clicks the refresh button.
 * @returns The panel element and its content/footer slots.
 */
export function createPanel(onClose: () => void, onRefresh: () => void): PanelSlots {
  const panel = document.createElement('section');
  panel.id = 'chat-panel';
  panel.className = 'chat-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Chat con Cero');

  const header = document.createElement('header');
  header.className = 'chat-panel-header';

  const title = document.createElement('div');
  title.className = 'chat-panel-title';

  const titleAvatar = document.createElement('img');
  titleAvatar.src = '/cerito-avatar.svg';
  titleAvatar.alt = '';
  titleAvatar.width = 28;
  titleAvatar.height = 28;

  const titleText = document.createElement('h2');
  titleText.textContent = 'Cero';

  title.appendChild(titleAvatar);
  title.appendChild(titleText);

  const headerActions = document.createElement('div');
  headerActions.className = 'chat-panel-actions';

  const refreshButton = document.createElement('button');
  refreshButton.className = 'chat-panel-refresh';
  refreshButton.type = 'button';
  refreshButton.setAttribute('aria-label', 'Reiniciar conversación');
  refreshButton.innerHTML = REFRESH_ICON;
  refreshButton.addEventListener('click', onRefresh);

  const closeButton = document.createElement('button');
  closeButton.className = 'chat-panel-close';
  closeButton.type = 'button';
  closeButton.setAttribute('aria-label', 'Cerrar chat');
  closeButton.innerHTML = CLOSE_ICON;
  closeButton.addEventListener('click', onClose);

  headerActions.appendChild(refreshButton);
  headerActions.appendChild(closeButton);

  header.appendChild(title);
  header.appendChild(headerActions);

  const contentSlot = document.createElement('div');
  contentSlot.className = 'chat-panel-content';

  const footerSlot = document.createElement('div');
  footerSlot.className = 'chat-panel-footer';

  panel.appendChild(header);
  panel.appendChild(contentSlot);
  panel.appendChild(footerSlot);

  panel.addEventListener('keydown', (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      onClose();
    }
  });

  return { element: panel, contentSlot, footerSlot };
}
