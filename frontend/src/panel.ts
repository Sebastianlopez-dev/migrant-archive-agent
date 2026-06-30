/**
 * Panel shell module for the chat widget.
 *
 * Renders the fixed right-side panel that hosts the conversation. It exposes
 * a content slot for messages/zero-state and a footer slot for the input bar.
 * The panel is intentionally stateless: the orchestrator toggles visibility.
 */

const REFRESH_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`;

const CLOSE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

const CHEVRON_DOWN_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="4 6 8 10 12 6"/></svg>`;

const LANGUAGES: Array<{ code: string; code3: string; name: string }> = [
  { code: 'en', code3: 'ENG', name: 'English' },
  { code: 'es', code3: 'SPA', name: 'Español' },
  { code: 'ca', code3: 'CAT', name: 'Català' },
  { code: 'fr', code3: 'FRA', name: 'Français' },
  { code: 'pt', code3: 'POR', name: 'Português' },
  { code: 'de', code3: 'DEU', name: 'Deutsch' },
];

const PANEL_I18N: Record<string, Record<string, string>> = {
  en: {
    ariaLabel: 'Chat with Cero',
    langLabel: 'Select language',
    langToggleLabel: 'Toggle language menu',
    refreshLabel: 'Restart conversation',
    closeLabel: 'Close chat',
    ceroName: 'Cero',
  },
  es: {
    ariaLabel: 'Chatear con Cero',
    langLabel: 'Seleccionar idioma',
    langToggleLabel: 'Mostrar u ocultar menú de idioma',
    refreshLabel: 'Reiniciar conversación',
    closeLabel: 'Cerrar chat',
    ceroName: 'Cero',
  },
  ca: {
    ariaLabel: 'Xatejar amb Cero',
    langLabel: 'Seleccionar idioma',
    langToggleLabel: "Mostrar o amagar el menú d'idioma",
    refreshLabel: 'Reinicia la conversa',
    closeLabel: 'Tancar xat',
    ceroName: 'Cero',
  },
  fr: {
    ariaLabel: 'Chatter avec Cero',
    langLabel: 'Sélectionner la langue',
    langToggleLabel: 'Afficher ou masquer le menu des langues',
    refreshLabel: 'Redémarrer la conversation',
    closeLabel: 'Fermer le chat',
    ceroName: 'Cero',
  },
  pt: {
    ariaLabel: 'Conversar com Cero',
    langLabel: 'Selecionar idioma',
    langToggleLabel: 'Mostrar ou ocultar menu de idioma',
    refreshLabel: 'Reiniciar conversa',
    closeLabel: 'Fechar chat',
    ceroName: 'Cero',
  },
  de: {
    ariaLabel: 'Chat mit Cero',
    langLabel: 'Sprache auswählen',
    langToggleLabel: 'Sprachmenü ein- oder ausblenden',
    refreshLabel: 'Konversation neu starten',
    closeLabel: 'Chat schließen',
    ceroName: 'Cero',
  },
};

/** References to the panel and its two placeholder regions. */
export interface PanelSlots {
  /** The root panel element (section#chat-panel). */
  element: HTMLElement;
  /** Container where messages or the zero-state are rendered. */
  contentSlot: HTMLElement;
  /** Container where the input bar is rendered. */
  footerSlot: HTMLElement;
  /** Set the language select value programmatically. */
  setLanguage: (lang: string) => void;
}

/**
 * Create the chat panel shell.
 *
 * @param onClose - Callback invoked when the user clicks the close button
 *                  or presses Escape inside the panel.
 * @param onRefresh - Callback invoked when the user clicks the refresh button.
 * @param onLanguageChange - Callback invoked when the user changes the language.
 * @param initialLanguage - Initial language for the select (default 'en').
 * @returns The panel element and its content/footer slots.
 */
export function createPanel(
  onClose: () => void,
  onRefresh: () => void,
  onLanguageChange: (lang: string) => void,
  initialLanguage = 'en',
): PanelSlots {
  const initialI18n = PANEL_I18N[initialLanguage] || PANEL_I18N.en;

  const panel = document.createElement('section');
  panel.id = 'chat-panel';
  panel.className = 'chat-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', initialI18n.ariaLabel);

  const header = document.createElement('header');
  header.className = 'chat-panel-header';

  const title = document.createElement('div');
  title.className = 'chat-panel-title';

  const titleAvatar = document.createElement('img');
  titleAvatar.src = '/cero-idea03.png';
  titleAvatar.alt = '';
titleAvatar.width = 42;
titleAvatar.height = 42;

  const titleText = document.createElement('h2');
  titleText.textContent = initialI18n.ceroName;

  title.appendChild(titleAvatar);
  title.appendChild(titleText);

  const headerActions = document.createElement('div');
  headerActions.className = 'chat-panel-actions';

  const langWrapper = document.createElement('div');
  langWrapper.className = 'chat-panel-lang-wrapper';

  const langBtn = document.createElement('button');
  langBtn.type = 'button';
  langBtn.className = 'chat-panel-lang-btn';
  langBtn.setAttribute('aria-haspopup', 'listbox');
  langBtn.setAttribute('aria-expanded', 'false');
  langBtn.setAttribute('aria-controls', 'chat-panel-lang-dropdown');
  langBtn.setAttribute('aria-label', initialI18n.langLabel);

  const langCodeSpan = document.createElement('span');
  langCodeSpan.className = 'chat-panel-lang-code';
  langCodeSpan.textContent = 'ENG';
  langBtn.appendChild(langCodeSpan);

  const langArrow = document.createElement('button');
  langArrow.type = 'button';
  langArrow.className = 'chat-panel-lang-arrow';
  langArrow.setAttribute('aria-haspopup', 'listbox');
  langArrow.setAttribute('aria-expanded', 'false');
  langArrow.setAttribute('aria-controls', 'chat-panel-lang-dropdown');
  langArrow.setAttribute('aria-label', initialI18n.langToggleLabel);
  langArrow.innerHTML = CHEVRON_DOWN_ICON;

  const langDropdown = document.createElement('div');
  langDropdown.id = 'chat-panel-lang-dropdown';
  langDropdown.className = 'chat-panel-lang-dropdown';
  langDropdown.setAttribute('role', 'listbox');
  langDropdown.setAttribute('aria-label', initialI18n.langLabel);
  langDropdown.hidden = true;

  const optionElements: HTMLButtonElement[] = [];
  LANGUAGES.forEach((lang) => {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = 'chat-panel-lang-option';
    option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', 'false');
    option.dataset.value = lang.code;

    const optionCode = document.createElement('span');
    optionCode.className = 'chat-panel-lang-option-code';
    optionCode.textContent = lang.code3;

    const optionName = document.createElement('span');
    optionName.className = 'chat-panel-lang-option-name';
    optionName.textContent = lang.name;

    option.appendChild(optionCode);
    option.appendChild(optionName);
    option.addEventListener('click', () => selectLanguage(lang.code));

    optionElements.push(option);
    langDropdown.appendChild(option);
  });

  langWrapper.appendChild(langBtn);
  langWrapper.appendChild(langArrow);
  langWrapper.appendChild(langDropdown);

  const refreshButton = document.createElement('button');
  refreshButton.className = 'chat-panel-refresh';
  refreshButton.type = 'button';
  refreshButton.setAttribute('aria-label', initialI18n.refreshLabel);
  refreshButton.innerHTML = REFRESH_ICON;
  refreshButton.addEventListener('click', onRefresh);

  const closeButton = document.createElement('button');
  closeButton.className = 'chat-panel-close';
  closeButton.type = 'button';
  closeButton.setAttribute('aria-label', initialI18n.closeLabel);
  closeButton.innerHTML = CLOSE_ICON;
  closeButton.addEventListener('click', onClose);

  headerActions.appendChild(langWrapper);
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
      if (isDropdownOpen) {
        event.stopPropagation();
        closeDropdown();
        return;
      }
      onClose();
    }
  });

  let currentLanguage = initialLanguage;
  let isDropdownOpen = false;
  let filterBuffer = '';
  let filterTimer: number | null = null;
  let activeOptionIndex = 0;

  function getVisibleOptions(): HTMLButtonElement[] {
    return optionElements.filter((option) => !option.hidden);
  }

  function openDropdown(): void {
    isDropdownOpen = true;
    filterBuffer = '';
    updateVisibleOptions();
    langDropdown.hidden = false;
    langBtn.setAttribute('aria-expanded', 'true');
    langArrow.setAttribute('aria-expanded', 'true');
    langArrow.classList.add('chat-panel-lang-arrow--open');
    activeOptionIndex = Math.max(
      0,
      getVisibleOptions().findIndex((option) => option.dataset.value === currentLanguage),
    );
    focusOption(activeOptionIndex);
    document.addEventListener('mousedown', handleClickOutside);
  }

  function closeDropdown(): void {
    if (!isDropdownOpen) return;
    isDropdownOpen = false;
    langDropdown.hidden = true;
    langBtn.setAttribute('aria-expanded', 'false');
    langArrow.setAttribute('aria-expanded', 'false');
    langArrow.classList.remove('chat-panel-lang-arrow--open');
    document.removeEventListener('mousedown', handleClickOutside);
    resetFilter();
    langBtn.focus();
  }

  function toggleDropdown(): void {
    if (isDropdownOpen) {
      closeDropdown();
    } else {
      openDropdown();
    }
  }

  function handleClickOutside(event: MouseEvent): void {
    const target = event.target as Node;
    if (!langWrapper.contains(target)) {
      closeDropdown();
    }
  }

  function selectLanguage(lang: string): void {
    onLanguageChange(lang);
    closeDropdown();
  }

  function focusOption(index: number): void {
    const visible = getVisibleOptions();
    if (visible.length === 0) return;
    activeOptionIndex = Math.max(0, Math.min(index, visible.length - 1));
    visible[activeOptionIndex].focus();
  }

  function focusNextOption(delta: number): void {
    const visible = getVisibleOptions();
    if (visible.length === 0) return;
    activeOptionIndex = (activeOptionIndex + delta + visible.length) % visible.length;
    visible[activeOptionIndex].focus();
  }

  function resetFilter(): void {
    filterBuffer = '';
    if (filterTimer !== null) {
      window.clearTimeout(filterTimer);
      filterTimer = null;
    }
    updateVisibleOptions();
  }

  function updateVisibleOptions(): void {
    const buffer = filterBuffer.toLowerCase();
    optionElements.forEach((option) => {
      const lang = LANGUAGES.find((l) => l.code === option.dataset.value);
      if (!lang) return;
      const match =
        buffer === '' ||
        lang.code3.toLowerCase().startsWith(buffer) ||
        lang.code.toLowerCase().startsWith(buffer) ||
        lang.name.toLowerCase().includes(buffer);
      option.hidden = !match;
    });
    const visible = getVisibleOptions();
    if (activeOptionIndex >= visible.length) {
      activeOptionIndex = visible.length > 0 ? 0 : 0;
    }
  }

  function handleFilterKey(key: string): void {
    if (key.length !== 1) return;
    filterBuffer += key.toLowerCase();
    updateVisibleOptions();
    const visible = getVisibleOptions();
    if (visible.length > 0) {
      activeOptionIndex = 0;
      visible[0].focus();
    }
    if (filterTimer !== null) {
      window.clearTimeout(filterTimer);
    }
    filterTimer = window.setTimeout(() => {
      resetFilter();
    }, 500);
  }

  langBtn.addEventListener('click', toggleDropdown);
  langArrow.addEventListener('click', toggleDropdown);

  langWrapper.addEventListener('keydown', (event: KeyboardEvent) => {
    if (!isDropdownOpen) return;

    if (event.key === 'Escape') {
      event.stopPropagation();
      closeDropdown();
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusNextOption(1);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusNextOption(-1);
      return;
    }

    if (event.key === 'Home') {
      event.preventDefault();
      focusOption(0);
      return;
    }

    if (event.key === 'End') {
      event.preventDefault();
      focusOption(getVisibleOptions().length - 1);
      return;
    }

    if (event.key === ' ') {
      const active = document.activeElement as HTMLElement | null;
      if (active && active.classList.contains('chat-panel-lang-option')) {
        event.preventDefault();
        const value = active.dataset.value;
        if (value) selectLanguage(value);
        return;
      }
    }

    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      handleFilterKey(event.key);
    }
  });

  function setLanguage(lang: string): void {
    currentLanguage = lang;
    const langData = LANGUAGES.find((l) => l.code === lang);
    langCodeSpan.textContent = langData?.code3 ?? 'ENG';
    optionElements.forEach((option) => {
      option.setAttribute('aria-selected', String(option.dataset.value === lang));
    });
    const i18n = PANEL_I18N[lang] || PANEL_I18N.en;
    panel.setAttribute('aria-label', i18n.ariaLabel);
    langBtn.setAttribute('aria-label', i18n.langLabel);
    langArrow.setAttribute('aria-label', i18n.langToggleLabel);
    langDropdown.setAttribute('aria-label', i18n.langLabel);
    refreshButton.setAttribute('aria-label', i18n.refreshLabel);
    closeButton.setAttribute('aria-label', i18n.closeLabel);
    titleText.textContent = i18n.ceroName;
  }

  setLanguage(initialLanguage);

  return { element: panel, contentSlot, footerSlot, setLanguage };
}
