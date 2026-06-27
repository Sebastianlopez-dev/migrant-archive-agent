/**
 * Floating Action Button module for the chat widget.
 *
 * Renders a fixed circular button in the bottom-right corner that toggles
 * the chat panel. The button is intentionally stateless: the orchestrator
 * decides when to show or hide it by attaching/removing it from the DOM or
 * toggling a CSS class.
 */

/**
 * Create a Floating Action Button that opens the chat panel.
 *
 * @param onClick - Callback invoked when the user clicks the FAB.
 * @returns The configured button element, ready to be appended to the DOM.
 */
export function createFab(onClick: () => void): HTMLButtonElement {
  const button = document.createElement('button');
  button.className = 'chat-fab';
  button.type = 'button';
  button.setAttribute('aria-label', 'Abrir chat con Cero');
  button.setAttribute('aria-controls', 'chat-panel');
  button.setAttribute('aria-expanded', 'false');

  const avatar = document.createElement('img');
  avatar.src = '/cerito-avatar.svg';
  avatar.alt = 'Cero';
  avatar.width = 42;
  avatar.height = 42;

  button.appendChild(avatar);
  button.addEventListener('click', onClick);

  return button;
}
