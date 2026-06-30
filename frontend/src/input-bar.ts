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
  /** Set display language and refresh visible labels. */
  setLanguage: (lang: string) => void;
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
// i18n strings
// ---------------------------------------------------------------------------

const INPUT_BAR_I18N: Record<string, Record<string, string>> = {
  en: {
    voiceLabel: 'Speak',
    placeholder: 'Type your question…',
    messageLabel: 'Message',
    sendLabel: 'Send message',
    transcribedLabel: 'Voice message transcribed',
    processing: 'Transcribing…',
    permissionDenied: 'Microphone blocked — check browser settings',
    noMic: 'No microphone detected',
    micUnavailable: 'Microphone unavailable',
    listening: 'Listening…',
    noAudio: 'No audio detected',
    pressEnter: 'Press Enter to send',
    connectionError: 'Connection error — try again',
    noSpeech: 'No speech detected',
    serviceUnavailable: 'Transcription service unavailable',
    audioTooLarge: 'Audio too long — max 25 MB',
    recording: 'Recording… tap to stop',
    countdown: 'Listening… {n}s',
    recorderError: 'Recording failed to start',
    transcribingStatus: 'Transcribing…',
  },
  es: {
    voiceLabel: 'Hablar por voz',
    placeholder: 'Escribí tu pregunta…',
    messageLabel: 'Mensaje',
    sendLabel: 'Enviar mensaje',
    transcribedLabel: 'Mensaje de voz transcrito',
    processing: 'Transcribiendo…',
    permissionDenied: 'Permiso de micrófono denegado — revisá configuración del navegador',
    noMic: 'No se detectó ningún micrófono',
    micUnavailable: 'Micrófono no disponible',
    listening: 'Escuchando…',
    noAudio: 'No se detectó audio',
    pressEnter: 'Presioná Enter para enviar',
    connectionError: 'Error de conexión — intentá de nuevo',
    noSpeech: 'No se detectó voz',
    serviceUnavailable: 'Servicio de transcripción no disponible',
    audioTooLarge: 'Audio demasiado largo — máximo 25 MB',
    recording: 'Grabando… pulsá para detener',
    countdown: 'Escuchando… {n}s',
    recorderError: 'Error al iniciar grabación',
    transcribingStatus: 'Transcribiendo…',
  },
  ca: {
    voiceLabel: 'Parlar',
    placeholder: 'Escriu la teva pregunta…',
    messageLabel: 'Missatge',
    sendLabel: 'Enviar missatge',
    transcribedLabel: 'Missatge de veu transcrit',
    processing: 'Transcrivint…',
    permissionDenied: 'Micròfon bloquejat — revisa la configuració del navegador',
    noMic: 'No s\'ha detectat cap micròfon',
    micUnavailable: 'Micròfon no disponible',
    listening: 'Escoltant…',
    noAudio: 'No s\'ha detectat àudio',
    pressEnter: 'Prem Enter per enviar',
    connectionError: 'Error de connexió — torna a intentar',
    noSpeech: 'No s\'ha detectat veu',
    serviceUnavailable: 'Servei de transcripció no disponible',
    audioTooLarge: 'Àudio massa llarg — màxim 25 MB',
    recording: 'Gravant… prem per aturar',
    countdown: 'Escoltant… {n}s',
    recorderError: 'Error en iniciar la gravació',
    transcribingStatus: 'Transcrivint…',
  },
  fr: {
    voiceLabel: 'Parler',
    placeholder: 'Écrivez votre question…',
    messageLabel: 'Message',
    sendLabel: 'Envoyer',
    transcribedLabel: 'Message vocal transcrit',
    processing: 'Transcription…',
    permissionDenied: 'Micro bloqué — vérifiez les paramètres du navigateur',
    noMic: 'Aucun microphone détecté',
    micUnavailable: 'Microphone indisponible',
    listening: 'Écoute…',
    noAudio: 'Aucun audio détecté',
    pressEnter: 'Appuyez sur Entrée pour envoyer',
    connectionError: 'Erreur de connexion — réessayez',
    noSpeech: 'Aucune parole détectée',
    serviceUnavailable: 'Service de transcription indisponible',
    audioTooLarge: 'Audio trop long — max 25 Mo',
    recording: 'Enregistrement… appuyez pour arrêter',
    countdown: 'Écoute… {n}s',
    recorderError: 'Échec du démarrage de l\'enregistrement',
    transcribingStatus: 'Transcription…',
  },
  pt: {
    voiceLabel: 'Falar',
    placeholder: 'Digite sua pergunta…',
    messageLabel: 'Mensagem',
    sendLabel: 'Enviar mensagem',
    transcribedLabel: 'Mensagem de voz transcrita',
    processing: 'Transcrevendo…',
    permissionDenied: 'Microfone bloqueado — verifique as configurações do navegador',
    noMic: 'Nenhum microfone detectado',
    micUnavailable: 'Microfone indisponível',
    listening: 'Ouvindo…',
    noAudio: 'Nenhum áudio detectado',
    pressEnter: 'Pressione Enter para enviar',
    connectionError: 'Erro de conexão — tente novamente',
    noSpeech: 'Nenhuma fala detectada',
    serviceUnavailable: 'Serviço de transcrição indisponível',
    audioTooLarge: 'Áudio muito longo — máx 25 MB',
    recording: 'Gravando… toque para parar',
    countdown: 'Ouvindo… {n}s',
    recorderError: 'Falha ao iniciar gravação',
    transcribingStatus: 'Transcrevendo…',
  },
  de: {
    voiceLabel: 'Sprechen',
    placeholder: 'Frage eingeben…',
    messageLabel: 'Nachricht',
    sendLabel: 'Nachricht senden',
    transcribedLabel: 'Sprachnachricht transkribiert',
    processing: 'Transkribiere…',
    permissionDenied: 'Mikrofon blockiert — Browsereinstellungen prüfen',
    noMic: 'Kein Mikrofon erkannt',
    micUnavailable: 'Mikrofon nicht verfügbar',
    listening: 'Höre zu…',
    noAudio: 'Kein Audio erkannt',
    pressEnter: 'Enter drücken zum Senden',
    connectionError: 'Verbindungsfehler — erneut versuchen',
    noSpeech: 'Keine Sprache erkannt',
    serviceUnavailable: 'Transkriptionsdienst nicht verfügbar',
    audioTooLarge: 'Audio zu lang — max 25 MB',
    recording: 'Aufnahme… zum Stoppen tippen',
    countdown: 'Höre zu… {n}s',
    recorderError: 'Aufnahme konnte nicht gestartet werden',
    transcribingStatus: 'Transkribiere…',
  },
};

// ---------------------------------------------------------------------------
// Input bar factory
// ---------------------------------------------------------------------------

export function createInputBar(language = 'en', onSend: (question: string) => void): InputBarApi {
  let currentLanguage = language;
  const t = (key: string): string => (INPUT_BAR_I18N[currentLanguage] || INPUT_BAR_I18N.en)[key] || key;

  const root = document.createElement('div');
  root.className = 'chat-input-bar';

  const toolbar = document.createElement('div');
  toolbar.className = 'chat-input-toolbar';

  // ── Shared voice state ──────────────────────────────────────────

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
  voiceButton.setAttribute('aria-label', t('voiceLabel'));
  voiceButton.innerHTML = MIC_ICON;

  // ── Text input ──────────────────────────────────────────────────

  const input = document.createElement('textarea');
  input.className = 'chat-input';
  input.rows = 1;
  input.placeholder = t('placeholder');
  input.setAttribute('aria-label', t('messageLabel'));

  // ── Send button ─────────────────────────────────────────────────

  const sendButton = document.createElement('button');
  sendButton.className = 'chat-send';
  sendButton.type = 'button';
  sendButton.setAttribute('aria-label', t('sendLabel'));
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
        input.placeholder = t('placeholder');
      }
    }, 2500);
  }

  function finishVoice(success: boolean): void {
    isProcessing = false;
    voiceButton.classList.remove('chat-input-tool--processing', 'chat-input-tool--recording');

    if (success && hadFinalResult && input.value.trim()) {
      voiceButton.classList.add('chat-input-tool--success');
      voiceButton.setAttribute('aria-label', t('transcribedLabel'));
      setTimeout(() => {
        voiceButton.classList.remove('chat-input-tool--success');
        voiceButton.setAttribute('aria-label', t('voiceLabel'));
      }, 2000);
    } else {
      voiceButton.setAttribute('aria-label', t('voiceLabel'));
    }
  }

  // ── Voice recording ─────────────────────────────────────────────

  voiceButton.addEventListener('click', () => {
    if (isProcessing) {
      showHint(t('processing'));
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
          showHint(t('permissionDenied'));
          voiceButton.classList.add('chat-input-tool--denied');
        } else if (err.name === 'NotFoundError') {
          showHint(t('noMic'));
        } else {
          showHint(t('micUnavailable'));
        }
      } else {
        showHint(t('micUnavailable'));
      }
      return;
    }

    if (startAborted) {
      micStream.getTracks().forEach((tr) => tr.stop());
      micStream = null;
      isListening = false;
      return;
    }

    hadFinalResult = false;
    audioChunks = [];
    const capturedLanguage = currentLanguage;
    input.placeholder = t('listening');
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
          micStream.getTracks().forEach((tr) => tr.stop());
          micStream = null;
        }

        if (audioChunks.length === 0) {
          showHint(t('noAudio'));
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
          input.placeholder = t('pressEnter');
          setTimeout(() => {
            input.placeholder = t('placeholder');
          }, 3000);
        } catch (err) {
          console.log('[mic:backend] transcription failed:', err);
          hadFinalResult = false;
          const msg = err instanceof Error ? err.message : String(err);
          if (err instanceof TypeError || msg.includes('ECONNREFUSED') || msg.includes('Failed to fetch')) {
            showHint(t('connectionError'));
          } else if (msg.includes('[422]')) {
            showHint(t('noSpeech'));
          } else if (msg.includes('[503]')) {
            showHint(t('serviceUnavailable'));
          } else if (msg.includes('[413]')) {
            showHint(t('audioTooLarge'));
          } else {
            showHint(t('connectionError'));
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
          micStream.getTracks().forEach((tr) => tr.stop());
          micStream = null;
        }
        mediaRecorder = null;
        voiceButton.classList.remove('chat-input-tool--recording');
        input.placeholder = t('placeholder');
        finishVoice(false);
      };

      mediaRecorder.start(1000);
      voiceButton.classList.add('chat-input-tool--recording');
      voiceButton.setAttribute('aria-label', t('recording'));

      maxRecordTimer = setTimeout(() => {
        if (isListening && mediaRecorder && mediaRecorder.state === 'recording') {
          stopBackendRecording();
        }
      }, MAX_RECORD_SECONDS * 1000);

      countdownStartTimer = setTimeout(() => {
        if (!isListening) return;
        let remaining = 3;
        input.placeholder = t('countdown').replace('{n}', String(remaining));
        countdownInterval = setInterval(() => {
          remaining--;
          if (remaining <= 0 || !isListening) {
            if (countdownInterval) {
              clearInterval(countdownInterval);
              countdownInterval = null;
            }
            return;
          }
          input.placeholder = t('countdown').replace('{n}', String(remaining));
        }, 1000);
      }, (MAX_RECORD_SECONDS - 3) * 1000);
    } catch (err) {
      console.log('[mic:backend] MediaRecorder construction/start failed:', err);
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
        micStream.getTracks().forEach((tr) => tr.stop());
        micStream = null;
      }
      showHint(t('recorderError'));
      return;
    }
  }

  function stopBackendRecording(): void {
    if (!mediaRecorder) {
      if (isListening) {
        startAborted = true;
        isListening = false;
        voiceButton.classList.remove('chat-input-tool--recording');
        voiceButton.setAttribute('aria-label', t('voiceLabel'));
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
    voiceButton.setAttribute('aria-label', t('transcribingStatus'));
    input.placeholder = t('processing');

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

  function setLanguage(lang: string): void {
    currentLanguage = lang;
    voiceButton.setAttribute('aria-label', t('voiceLabel'));
    input.placeholder = t('placeholder');
    input.setAttribute('aria-label', t('messageLabel'));
    sendButton.setAttribute('aria-label', t('sendLabel'));
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

  return { element: root, setQuestion, clear, focus, setLoading, setLanguage };
}
