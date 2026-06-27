/**
 * Input bar module for the chat widget.
 *
 * Renders a bottom-anchored toolbar with a text input, send button, and
 * non-functional microphone/model placeholders. No animations are used.
 */

export interface InputBarApi {
  /** The root input bar element. */
  element: HTMLElement;
  /** Populate the input field with a question. */
  setQuestion: (question: string) => void;
  /** Clear the input field. */
  clear: () => void;
}

const SEND_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`;

const MIC_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;

/**
 * Create the bottom input bar.
 *
 * @param onSend - Callback invoked when the user submits a question.
 * @returns The input bar element and helpers to manipulate the input value.
 */
export function createInputBar(onSend: (question: string) => void): InputBarApi {
  const root = document.createElement('div');
  root.className = 'chat-input-bar';

  const toolbar = document.createElement('div');
  toolbar.className = 'chat-input-toolbar';

  const voiceButton = document.createElement('button');
  voiceButton.className = 'chat-input-tool chat-input-tool--voice';
  voiceButton.type = 'button';
  voiceButton.setAttribute('aria-label', 'Enviar mensaje de voz');
  voiceButton.disabled = true;
  voiceButton.innerHTML = MIC_ICON;
  voiceButton.setAttribute('aria-hidden', 'true');

  const input = document.createElement('textarea');
  input.className = 'chat-input';
  input.rows = 1;
  input.placeholder = 'Escribí tu pregunta…';
  input.setAttribute('aria-label', 'Mensaje');

  const sendButton = document.createElement('button');
  sendButton.className = 'chat-send';
  sendButton.type = 'button';
  sendButton.setAttribute('aria-label', 'Enviar mensaje');
  sendButton.innerHTML = SEND_ICON;

  toolbar.appendChild(voiceButton);
  toolbar.appendChild(input);
  toolbar.appendChild(sendButton);

  const meta = document.createElement('div');
  meta.className = 'chat-input-meta';

  const modelLabel = document.createElement('span');
  modelLabel.className = 'chat-model-label';
  modelLabel.textContent = 'Gemini';
  meta.appendChild(modelLabel);

  root.appendChild(toolbar);
  root.appendChild(meta);

  function submit(): void {
    const question = input.value.trim();
    if (!question) return;
    onSend(question);
    input.value = '';
    input.rows = 1;
  }

  function setQuestion(question: string): void {
    input.value = question;
    input.rows = Math.min(5, question.split('\n').length);
    input.focus();
  }

  function clear(): void {
    input.value = '';
    input.rows = 1;
  }

  sendButton.addEventListener('click', submit);

  input.addEventListener('keydown', (event: KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  });

  input.addEventListener('input', () => {
    const lines = input.value.split('\n').length;
    input.rows = Math.min(5, Math.max(1, lines));
  });

  return { element: root, setQuestion, clear };
}
