/**
 * Zero-state module for the chat widget.
 *
 * Renders a language-aware greeting and a set of clickable suggestion cards
 * that populate the user's question. No animations or transitions are used.
 */

export interface Suggestion {
  id: string;
  label: string;
  icon: string;
}

const ICONS: Record<string, string> = {
  videos: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  filmig: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>`,
  mujeres: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
};

interface ZeroStateTranslations {
  greeting: string;
  purpose: string;
  suggestionsAria: string;
  suggestions: Array<{ id: string; label: string }>;
}

const I18N: Record<string, ZeroStateTranslations> = {
  en: {
    greeting: "Hi, I'm Cero",
    purpose: "Ask me about the Plataforma Cero videos",
    suggestionsAria: "Suggested questions",
    suggestions: [
      { id: 'videos', label: 'List Plataforma Cero videos' },
      { id: 'filmig', label: 'What is FILMIG?' },
      { id: 'mujeres', label: 'What is Mujeres del Maíz?' },
    ]
  },
  es: {
    greeting: "Hola, soy Cero",
    purpose: "Preguntame sobre los videos de Plataforma Cero",
    suggestionsAria: "Sugerencias de preguntas",
    suggestions: [
      { id: 'videos', label: 'Lista de videos de Plataforma Cero' },
      { id: 'filmig', label: '¿Qué es FILMIG?' },
      { id: 'mujeres', label: '¿Qué es Mujeres del Maíz?' },
    ]
  },
  ca: {
    greeting: "Hola, soc Cero",
    purpose: "Pregunta'm sobre els vídeos de Plataforma Cero",
    suggestionsAria: "Preguntes suggerides",
    suggestions: [
      { id: 'videos', label: 'Llista de vídeos de Plataforma Cero' },
      { id: 'filmig', label: 'Què és FILMIG?' },
      { id: 'mujeres', label: 'Què és Mujeres del Maíz?' },
    ]
  },
  fr: {
    greeting: "Bonjour, je suis Cero",
    purpose: "Posez-moi des questions sur les vidéos de Plataforma Cero",
    suggestionsAria: "Questions suggérées",
    suggestions: [
      { id: 'videos', label: 'Liste des vidéos de Plataforma Cero' },
      { id: 'filmig', label: 'Qu\'est-ce que FILMIG ?' },
      { id: 'mujeres', label: 'Qu\'est-ce que Mujeres del Maíz ?' },
    ]
  },
  pt: {
    greeting: "Olá, sou Cero",
    purpose: "Pergunte-me sobre os vídeos da Plataforma Cero",
    suggestionsAria: "Perguntas sugeridas",
    suggestions: [
      { id: 'videos', label: 'Lista de vídeos da Plataforma Cero' },
      { id: 'filmig', label: 'O que é FILMIG?' },
      { id: 'mujeres', label: 'O que é Mujeres del Maíz?' },
    ]
  },
  de: {
    greeting: "Hallo, ich bin Cero",
    purpose: "Frag mich zu den Videos von Plataforma Cero",
    suggestionsAria: "Vorgeschlagene Fragen",
    suggestions: [
      { id: 'videos', label: 'Liste der Plataforma Cero Videos' },
      { id: 'filmig', label: 'Was ist FILMIG?' },
      { id: 'mujeres', label: 'Was ist Mujeres del Maíz?' },
    ]
  },
};

export const SUPPORTED_LANGUAGES: readonly string[] = Object.keys(I18N);

export interface ZeroStateElement extends HTMLElement {
  updateLanguage(lang: string): void;
}

/**
 * Create the zero-state view with a greeting and suggestion cards.
 *
 * @param language - ISO code of the language to render (fallback: `en`).
 * @param onSuggestionClick - Callback invoked when a suggestion is clicked.
 *                            Receives the suggestion label as the question text.
 * @returns The root zero-state element, ready to be appended to the panel.
 */
export function createZeroState(
  language: string,
  onSuggestionClick: (question: string) => void,
): ZeroStateElement {
  const t = I18N[language] || I18N.en;

  const root = document.createElement('div');
  root.className = 'chat-zero-state';
  root.setAttribute('lang', language);

  const greeting = document.createElement('div');
  greeting.className = 'chat-zero-state-greeting';

  const heading = document.createElement('h3');
  heading.textContent = t.greeting;

  const purpose = document.createElement('p');
  purpose.textContent = t.purpose;

  greeting.appendChild(heading);
  greeting.appendChild(purpose);
  root.appendChild(greeting);

  const suggestions = document.createElement('div');
  suggestions.className = 'chat-suggestions';
  suggestions.setAttribute('aria-label', t.suggestionsAria);

  for (const suggestion of t.suggestions) {
    const card = document.createElement('button');
    card.className = 'chat-suggestion';
    card.type = 'button';

    const icon = document.createElement('span');
    icon.className = 'chat-suggestion-icon';
    icon.innerHTML = ICONS[suggestion.id] || '';

    const label = document.createElement('span');
    label.className = 'chat-suggestion-label';
    label.textContent = suggestion.label;

    card.appendChild(icon);
    card.appendChild(label);

    card.addEventListener('click', () => {
      const labelEl = card.querySelector<HTMLElement>('.chat-suggestion-label');
      const currentLabel = labelEl?.textContent || '';
      onSuggestionClick(currentLabel);
    });

    suggestions.appendChild(card);
  }

  root.appendChild(suggestions);

  return Object.assign(root, {
    updateLanguage(lang: string) {
      root.setAttribute('lang', lang);
      const next = I18N[lang] || I18N.en;
      heading.textContent = next.greeting;
      purpose.textContent = next.purpose;
      suggestions.setAttribute('aria-label', next.suggestionsAria);

      const cards = suggestions.querySelectorAll('.chat-suggestion-label');
      next.suggestions.forEach((s, i) => {
        const label = cards[i];
        if (label) {
          label.textContent = s.label;
        }
      });
    }
  });
}
