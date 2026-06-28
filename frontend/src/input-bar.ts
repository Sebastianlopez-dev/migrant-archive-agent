/**
 * Input bar module for the chat widget.
 *
 * Renders a bottom-anchored toolbar with a text input, send button, and
 * voice input. Two strategies, tried in order:
 *
 *   1. Web Speech API (SpeechRecognition) — instant, zero-backend, works
 *      in Chrome, Edge, and Safari. Brave deliberately disables it.
 *   2. MediaRecorder + backend /api/transcribe — fallback for Firefox
 *      and any browser without SpeechRecognition.
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
}

const SEND_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`;

const MIC_ICON = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>`;

// ---------------------------------------------------------------------------
// Backend fallback: MediaRecorder → POST /api/transcribe → faster-whisper
// ---------------------------------------------------------------------------

async function transcribeAudio(blob: Blob): Promise<string> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120_000);

  const form = new FormData();
  form.append('audio', blob, 'recording.webm');

  console.log('[mic:backend] POST /api/transcribe — blob:', blob.size, 'bytes');

  try {
    const response = await fetch('/api/transcribe', {
      method: 'POST',
      body: form,
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(body || `Transcription failed (${response.status})`);
    }

    const data: { text: string } = await response.json();
    return data.text;
  } finally {
    clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Voice strategy detection
// ---------------------------------------------------------------------------

/** Resolve the SpeechRecognition constructor across browser prefixes. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getSpeechRecognitionAPI(): any {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null;
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

  let isListening = false;
  let isProcessing = false;
  let hadFinalResult = false;

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
      if (!isListening) {
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

  // ===================================================================
  // Strategy 1: Web Speech API (primary — Chrome, Edge, Safari)
  // ===================================================================

  const SpeechRecognitionAPI = getSpeechRecognitionAPI();

  if (SpeechRecognitionAPI) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let recognition: any = null;

    voiceButton.addEventListener('click', () => {
      if (isProcessing) return;
      if (isListening) {
        stopSpeechRecognition();
      } else {
        startSpeechRecognition();
      }
    });

    function startSpeechRecognition(): void {
      if (isListening || isProcessing) return;

      hadFinalResult = false;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition = new (SpeechRecognitionAPI as any)();
      recognition.lang = 'es-ES';
      recognition.interimResults = true;
      recognition.continuous = true;
      // Stop after a short silence — the API fires a final result.
      recognition.maxAlternatives = 1;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        // Walk results backwards so we pick up the final isFinal.
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          transcript += result[0].transcript;
          if (result.isFinal) {
            hadFinalResult = true;
          }
        }
        input.value = transcript;
        input.rows = Math.min(5, transcript.split('\n').length);
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = (event: any) => {
        console.log('[mic:speech] error:', event.error, event.message);
        if (event.error === 'not-allowed') {
          showHint('Micrófono bloqueado por el navegador');
        } else if (event.error !== 'aborted') {
          showHint('No se detectó voz');
        }
        cleanupSpeechRecognition();
        isListening = false;
        finishVoice(false);
      };

      recognition.onend = () => {
        const wasListening = isListening;
        cleanupSpeechRecognition();
        if (wasListening) {
          isListening = false;
          voiceButton.classList.remove('chat-input-tool--recording');
          finishVoice(hadFinalResult);
          if (hadFinalResult) input.focus();
        }
      };

      recognition.onaudiostart = () => {
        isProcessing = false;
      };

      recognition.start();
      isListening = true;
      voiceButton.classList.add('chat-input-tool--recording');
      voiceButton.setAttribute('aria-label', 'Grabando… pulsá para detener');
      input.value = '';
      input.placeholder = 'Escuchando…';
    }

    function stopSpeechRecognition(): void {
      isListening = false;
      isProcessing = true;
      voiceButton.classList.remove('chat-input-tool--recording');
      voiceButton.classList.add('chat-input-tool--processing');
      voiceButton.setAttribute('aria-label', 'Transcribiendo…');
      input.placeholder = 'Transcribiendo…';

      if (recognition) {
        recognition.stop();
      }
    }

    function cleanupSpeechRecognition(): void {
      if (recognition) {
        // Remove handlers to avoid double-fires.
        recognition.onresult = null;
        recognition.onerror = null;
        recognition.onend = null;
        recognition.onaudiostart = null;
        recognition = null;
      }
    }

    console.log('[mic] Web Speech API active — transcription runs entirely in-browser');
  } else {

    // ===================================================================
    // Strategy 2: MediaRecorder + backend (fallback)
    // ===================================================================

    let mediaRecorder: MediaRecorder | null = null;
    let audioChunks: Blob[] = [];
    let micStream: MediaStream | null = null;
    let startAborted = false;
    let maxRecordTimer: ReturnType<typeof setTimeout> | null = null;
    const MAX_RECORD_SECONDS = 10;

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
        showHint('Micrófono no disponible');
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
      input.placeholder = 'Escuchando…';
      input.value = '';

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : 'audio/mp4';

      mediaRecorder = new MediaRecorder(micStream, { mimeType: mime });

      mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (micStream) {
          micStream.getTracks().forEach((t) => t.stop());
          micStream = null;
        }

        if (audioChunks.length === 0) {
          finishVoice(false);
          return;
        }

        const blob = new Blob(audioChunks, { type: mime });

        try {
          const text = await transcribeAudio(blob);
          input.value = text;
          input.rows = Math.min(5, text.split('\n').length);
          hadFinalResult = true;
          finishVoice(true);
          input.focus();
        } catch (err) {
          console.log('[mic:backend] transcription failed:', err);
          hadFinalResult = false;
          showHint('No se detectó voz');
          finishVoice(false);
        }
      };

      mediaRecorder.onerror = (event) => {
        console.log('[mic:backend] MediaRecorder error:', event);
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

      isListening = false;
      isProcessing = true;
      voiceButton.classList.remove('chat-input-tool--recording');
      voiceButton.classList.add('chat-input-tool--processing');
      voiceButton.setAttribute('aria-label', 'Transcribiendo…');
      input.placeholder = 'Transcribiendo…';

      mediaRecorder.stop();
    }

    console.log('[mic] Backend transcription active — audio sent to /api/transcribe');
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

  return { element: root, setQuestion, clear, focus, setLoading };
}
