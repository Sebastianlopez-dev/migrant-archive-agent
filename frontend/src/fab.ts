/**
 * Floating Action Button module for the chat widget.
 *
 * Renders a fixed circular button in the bottom-right corner that toggles
 * the chat panel. The button is intentionally stateless: the orchestrator
 * decides when to show or hide it by attaching/removing it from the DOM or
 * toggling a CSS class.
 */

export interface FabApi {
  /** The FAB button element. */
  element: HTMLButtonElement;
  /** Update the aria-label based on the selected language. */
  setLanguage: (lang: string) => void;
}

const FAB_I18N: Record<string, string> = {
  en: 'Open chat with Cero',
  es: 'Abrir chat con Cero',
  ca: 'Obrir xat amb Cero',
  fr: 'Ouvrir le chat avec Cero',
  pt: 'Abrir chat com Cero',
  de: 'Chat mit Cero öffnen',
};

/**
 * Create a Floating Action Button that opens the chat panel.
 *
 * @param language - ISO code for the display language (default: `en`).
 * @param onClick - Callback invoked when the user clicks the FAB.
 * @returns The button element and a language setter.
 */
export function createFab(language = 'en', onClick: () => void): FabApi {
  let currentLanguage = language;

  const button = document.createElement('button');
  button.className = 'chat-fab';
  button.type = 'button';
  button.setAttribute('aria-controls', 'chat-panel');
  button.setAttribute('aria-expanded', 'false');

  function refreshLabel(): void {
    button.setAttribute('aria-label', FAB_I18N[currentLanguage] || FAB_I18N.en);
  }

  refreshLabel();

  const avatar = document.createElement('img');
  avatar.src = '/cerito-avatar.svg';
  avatar.alt = 'Cero';
  avatar.width = 42;
  avatar.height = 42;

  button.appendChild(avatar);
  button.addEventListener('click', onClick);

  function setLanguage(lang: string): void {
    currentLanguage = lang;
    refreshLabel();
  }

  return { element: button, setLanguage };
}
