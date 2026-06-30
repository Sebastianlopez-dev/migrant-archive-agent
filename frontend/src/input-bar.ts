/**
 * Input bar module for the chat widget.
 *
 * Renders a bottom-anchored toolbar with a text input, send button, and
 * voice input. Voice transcription is handled via MediaRecorder capture
 * sent to the backend Groq Whisper endpoint — this is the sole voice path,
 * not a fallback.
 */

export interface InputBarApi {
  /** The root input bar element. */
  element: HTMLElement;
  /** Populate the input field with a question. */
  setQuestion: (question: string) => void;
  /** Clear the input field. */
  clear: () => void;
  /** Focus the input field. */
  focus: () => void;
  /** Enable or disable the input and send button. */
  setLoading: (isLoading: boolean) => void;
  /** Set the language hint passed to the voice transcription endpoint. */
  setVoiceLanguage: (lang: string) => void;
}

const SEND_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`;

const MIC_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;

// ---------------------------------------------------------------------------
// Voice transcription: MediaRecorder → POST /api/transcribe → Groq Whisper
// ---------------------------------------------------------------------------

async function transcribeAudio(blob: Blob, filename: string, language: string): Promise<string> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  const form = new FormData();
  form.append('audio', blob, filename);

  const url = language
    ? `/api/transcribe?language=${encodeURIComponent(language)}`
    : '/api/transcribe';

  console.log('[mic:backend] POST /api/transcribe — blob:', blob.size, 'bytes');

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: form,
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`[${response.status}] ${body || 'Transcription failed'}`);
    }

    const data: { text: string } = await response.json();
    return data.text;
  } finally {
    clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Input bar factory
// ---------------------------------------------------------------------------

export function createInputBar(onSend: (question: string) => void): InputBarApi {
  const root = document.createElement('div');
  root.className = 'chat-input-bar';

  const toolbar = document.createElement('div');
  toolbar.className = 'chat-input-toolbar';

  // ── Shared voice state ──────────────────────────────────────────

  let voiceLanguage = 'en';
  let isListening = false;
  let isProcessing = false;
  let hadFinalResult = false;

  let mediaRecorder: MediaRecorder | null = null;
  let audioChunks: Blob[] = [];
  let micStream: MediaStream | null = null;
  let startAborted = false;
  let maxRecordTimer: ReturnType<typeof setTimeout> | null = null;
  let countdownStartTimer: ReturnType<typeof setTimeout> | null = null;
  let countdownInterval: ReturnType<typeof setInterval> | null = null;
  const MAX_RECORD_SECONDS = 30;

  const voiceButton = document.createElement('button');
  voiceButton.className = 'chat-input-tool chat-input-tool--voice';
  voiceButton.type = 'button';
  voiceButton.setAttribute('aria-label', 'Hablar por voz');
  voiceButton.innerHTML = MIC_ICON;

  // ── Text input ──────────────────────────────────────────────────

  const input = document.createElement('textarea');
  input.className = 'chat-input';
  input.rows = 1;
  input.placeholder = 'Escribí tu pregunta…';
  input.setAttribute('aria-label', 'Mensaje');

  // ── Send button ─────────────────────────────────────────────────

  const sendButton = document.createElement('button');
  sendButton.className = 'chat-send';
  sendButton.type = 'button';
  sendButton.setAttribute('aria-label', 'Enviar mensaje');
  sendButton.innerHTML = SEND_ICON;

  toolbar.appendChild(voiceButton);
  toolbar.appendChild(input);
  toolbar.appendChild(sendButton);
  root.appendChild(toolbar);

  // ── Shared helpers ──────────────────────────────────────────────

  function showHint(message: string): void {
    input.placeholder = message;
    setTimeout(() => {
      if (!isListening && !isProcessing) {
        input.placeholder = 'Escribí tu pregunta…';
      }
    }, 2500);
  }

  function finishVoice(success: boolean): void {
    isProcessing = false;
    voiceButton.classList.remove('chat-input-tool--processing', 'chat-input-tool--recording');

    if (success && hadFinalResult && input.value.trim()) {
      voiceButton.classList.add('chat-input-tool--success');
      voiceButton.setAttribute('aria-label', 'Mensaje de voz transcrito');
      setTimeout(() => {
        voiceButton.classList.remove('chat-input-tool--success');
        voiceButton.setAttribute('aria-label', 'Hablar por voz');
      }, 2000);
    } else {
      voiceButton.setAttribute('aria-label', 'Hablar por voz');
    }
  }

  // ── Voice recording ─────────────────────────────────────────────

  voiceButton.addEventListener('click', () => {
    if (isProcessing) {
      showHint('Transcribiendo…');
      return;
    }
    if (isListening) {
      stopBackendRecording();
    } else {
      startBackendRecording();
    }
  });

  async function startBackendRecording(): Promise<void> {
    if (isListening || isProcessing) return;

    isListening = true;
    startAborted = false;

    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.log('[mic:backend] getUserMedia failed:', err);
      isListening = false;
      if (err instanceof DOMException) {
        if (err.name === 'NotAllowedError') {
          showHint('Permiso de micrófono denegado — revisá configuración del navegador');
          voiceButton.classList.add('chat-input-tool--denied');
        } else if (err.name === 'NotFoundError') {
          showHint('No se detectó ningún micrófono');
        } else {
          showHint('Micrófono no disponible');
        }
      } else {
        showHint('Micrófono no disponible');
      }
      return;
    }

    if (startAborted) {
      micStream.getTracks().forEach((t) => t.stop());
      micStream = null;
      isListening = false;
      return;
    }

    hadFinalResult = false;
    audioChunks = [];
    const capturedLanguage = voiceLanguage;
    input.placeholder = 'Escuchando…';
    input.value = '';

    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

    try {
      mediaRecorder = new MediaRecorder(micStream, { mimeType: mime });

      mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (!mediaRecorder) return;

        if (micStream) {
          micStream.getTracks().forEach((t) => t.stop());
          micStream = null;
        }

        if (audioChunks.length === 0) {
          showHint('No se detectó audio');
          finishVoice(false);
          return;
        }

        const blob = new Blob(audioChunks, { type: mime });
        const filename = mime === 'audio/mp4' ? 'recording.mp4' : 'recording.webm';

        try {
          const text = await transcribeAudio(blob, filename, capturedLanguage);
          input.value = text;
          input.rows = Math.min(5, text.split('\n').length);
          hadFinalResult = true;
          finishVoice(true);
          input.focus();
          input.placeholder = 'Presioná Enter para enviar';
          setTimeout(() => {
            input.placeholder = 'Escribí tu pregunta…';
          }, 3000);
        } catch (err) {
          console.log('[mic:backend] transcription failed:', err);
          hadFinalResult = false;
          const msg = err instanceof Error ? err.message : String(err);
          if (err instanceof TypeError || msg.includes('ECONNREFUSED') || msg.includes('Failed to fetch')) {
            showHint('Error de conexión — intentá de nuevo');
          } else if (msg.includes('[422]')) {
            showHint('No se detectó voz');
          } else if (msg.includes('[503]')) {
            showHint('Servicio de transcripción no disponible');
          } else if (msg.includes('[413]')) {
            showHint('Audio demasiado largo — máximo 25 MB');
          } else {
            showHint('Error de conexión — intentá de nuevo');
          }
          finishVoice(false);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.log('[mic:backend] MediaRecorder error:', event);
        isListening = false;
        if (maxRecordTimer) {
          clearTimeout(maxRecordTimer);
          maxRecordTimer = null;
        }
        if (countdownStartTimer) {
          clearTimeout(countdownStartTimer);
          countdownStartTimer = null;
        }
        if (countdownInterval) {
          clearInterval(countdownInterval);
          countdownInterval = null;
        }
        if (micStream) {
          micStream.getTracks().forEach((t) => t.stop());
          micStream = null;
        }
        mediaRecorder = null;
        voiceButton.classList.remove('chat-input-tool--recording');
        input.placeholder = 'Escribí tu pregunta…';
        finishVoice(false);
      };

      mediaRecorder.start(1000);
      voiceButton.classList.add('chat-input-tool--recording');
      voiceButton.setAttribute('aria-label', 'Grabando… pulsá para detener');

      maxRecordTimer = setTimeout(() => {
        if (isListening && mediaRecorder && mediaRecorder.state === 'recording') {
          stopBackendRecording();
        }
      }, MAX_RECORD_SECONDS * 1000);

      countdownStartTimer = setTimeout(() => {
        if (!isListening) return;
        let remaining = 3;
        input.placeholder = `Escuchando… ${remaining}s`;
        countdownInterval = setInterval(() => {
          remaining--;
          if (remaining <= 0 || !isListening) {
            if (countdownInterval) {
              clearInterval(countdownInterval);
              countdownInterval = null;
            }
            return;
          }
          input.placeholder = `Escuchando… ${remaining}s`;
        }, 1000);
      }, (MAX_RECORD_SECONDS - 3) * 1000);
    } catch (err) {
      console.log('[mic:backend] MediaRecorder construction/start failed:', err);
      isListening = false;
      if (micStream) {
        micStream.getTracks().forEach((t) => t.stop());
        micStream = null;
      }
      showHint('Error al iniciar grabación');
      return;
    }
  }

  function stopBackendRecording(): void {
    if (!mediaRecorder) {
      if (isListening) {
        startAborted = true;
        isListening = false;
        voiceButton.classList.remove('chat-input-tool--recording');
        voiceButton.setAttribute('aria-label', 'Hablar por voz');
      }
      return;
    }
    if (mediaRecorder.state === 'inactive') return;

    if (maxRecordTimer) {
      clearTimeout(maxRecordTimer);
      maxRecordTimer = null;
    }
    if (countdownStartTimer) {
      clearTimeout(countdownStartTimer);
      countdownStartTimer = null;
    }
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }

    isListening = false;
    isProcessing = true;
    voiceButton.classList.remove('chat-input-tool--recording');
    voiceButton.classList.add('chat-input-tool--processing');
    voiceButton.setAttribute('aria-label', 'Transcribiendo…');
    input.placeholder = 'Transcribiendo…';

    mediaRecorder.stop();
  }

  // ── Helpers ────────────────────────────────────────────────────

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

  function focus(): void {
    input.focus();
  }

  function setLoading(isLoading: boolean): void {
    input.disabled = isLoading;
    sendButton.disabled = isLoading;
    voiceButton.disabled = isLoading;
  }

  function setVoiceLanguage(lang: string): void {
    voiceLanguage = lang;
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

  return { element: root, setQuestion, clear, focus, setLoading, setVoiceLanguage };
}
