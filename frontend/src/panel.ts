/**
 * Panel shell module for the chat widget.
 *
 * Renders the fixed right-side panel that hosts the conversation. It exposes
 * a content slot for messages/zero-state and a footer slot for the input bar.
 * The panel is intentionally stateless: the orchestrator toggles visibility.
 */

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
 * @returns The panel element and its content/footer slots.
 */
export function createPanel(onClose: () => void): PanelSlots {
  const panel = document.createElement('section');
  panel.id = 'chat-panel';
  panel.className = 'chat-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Chat con Cerito');

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
  titleText.textContent = 'Cerito';

  title.appendChild(titleAvatar);
  title.appendChild(titleText);

  const closeButton = document.createElement('button');
  closeButton.className = 'chat-panel-close';
  closeButton.type = 'button';
  closeButton.setAttribute('aria-label', 'Cerrar chat');
  closeButton.textContent = '×';
  closeButton.addEventListener('click', onClose);

  header.appendChild(title);
  header.appendChild(closeButton);

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
