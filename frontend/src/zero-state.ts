/**
 * Zero-state module for the chat widget.
 *
 * Renders a static greeting and a set of clickable suggestion cards that
 * populate the user's question. No animations or transitions are used.
 */

export interface Suggestion {
  id: string;
  label: string;
  icon: string;
}

const SUGGESTIONS: Suggestion[] = [
  {
    id: 'filmig',
    label: '¿Qué es FILMIG?',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/></svg>`,
  },
  {
    id: 'videos',
    label: '¿Qué videos puedo encontrar de Plataforma Cero?',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  },
  {
    id: 'mujeres',
    label: '¿Qué es mujeres del maíz?',
    icon: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  },
];

/**
 * Create the zero-state view with a greeting and suggestion cards.
 *
 * @param onSuggestionClick - Callback invoked when a suggestion is clicked.
 *                            Receives the suggestion label as the question text.
 * @returns The root zero-state element, ready to be appended to the panel.
 */
export function createZeroState(onSuggestionClick: (question: string) => void): HTMLElement {
  const root = document.createElement('div');
  root.className = 'chat-zero-state';

  const greeting = document.createElement('div');
  greeting.className = 'chat-zero-state-greeting';

  const heading = document.createElement('h3');
  heading.textContent = 'Hola, soy Cero';

  const purpose = document.createElement('p');
  purpose.textContent = 'Preguntame sobre los videos de Plataforma Cero';

  greeting.appendChild(heading);
  greeting.appendChild(purpose);
  root.appendChild(greeting);

  const suggestions = document.createElement('div');
  suggestions.className = 'chat-suggestions';
  suggestions.setAttribute('aria-label', 'Sugerencias de preguntas');

  for (const suggestion of SUGGESTIONS) {
    const card = document.createElement('button');
    card.className = 'chat-suggestion';
    card.type = 'button';

    const icon = document.createElement('span');
    icon.className = 'chat-suggestion-icon';
    icon.innerHTML = suggestion.icon;

    const label = document.createElement('span');
    label.className = 'chat-suggestion-label';
    label.textContent = suggestion.label;

    card.appendChild(icon);
    card.appendChild(label);

    card.addEventListener('click', () => {
      onSuggestionClick(suggestion.label);
    });

    suggestions.appendChild(card);
  }

  root.appendChild(suggestions);

  return root;
}
