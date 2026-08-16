"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Mic, MicOff, Volume2, VolumeX, Loader2, PhoneOff, FileText, Languages,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button, Card, Badge } from "@/components/ui";
import { LANGUAGES } from "@/lib/utils";

// BCP-47 tags the Web Speech API understands for our supported languages
const BCP47: Record<string, string> = {
  en: "en-IN", hi: "hi-IN", kn: "kn-IN", ta: "ta-IN", te: "te-IN",
  ml: "ml-IN", mr: "mr-IN", bn: "bn-IN", gu: "gu-IN", pa: "pa-IN", ur: "ur-IN",
};

type SttMode = "browser" | "server" | "none";
type TtsMode = "browser" | "server" | "none";

interface Turn {
  role: "user" | "assistant";
  content: string;
  citations?: any[];
  language?: string;
}

export default function VoicePanel({ caseId }: { caseId: string }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [language, setLanguage] = useState("en");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [listening, setListening] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Capability detection: browser Web Speech, else server providers
  const [sttMode, setSttMode] = useState<SttMode>("none");
  const [ttsMode, setTtsMode] = useState<TtsMode>("none");
  const [sttSupported, setSttSupported] = useState(true);

  const recognitionRef = useRef<any>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const hasWebStt =
      typeof window !== "undefined" &&
      (("webkitSpeechRecognition" in window) || ("SpeechRecognition" in window));
    const hasWebTts = typeof window !== "undefined" && "speechSynthesis" in window;
    setSttSupported(hasWebStt);
    setSttMode(hasWebStt ? "browser" : "server"); // server attempted on first use
    setTtsMode(hasWebTts ? "browser" : "server");
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, thinking]);

  // Stop everything on unmount
  useEffect(() => {
    return () => {
      try { window.speechSynthesis?.cancel(); } catch {}
      try { recognitionRef.current?.stop(); } catch {}
      try { recorderRef.current?.stop(); } catch {}
      audioRef.current?.pause();
    };
  }, []);

  async function startSession() {
    setError(null);
    try {
      const session = await fetchVoiceSession(caseId, language);
      setSessionId(session.id);
      setTurns([]);
    } catch (e: any) {
      setError(e.message || "Failed to start voice session");
    }
  }

  async function endSession() {
    if (sessionId) {
      try { await api.endVoiceSession(sessionId); } catch {}
    }
    setSessionId(null);
    setTurns([]);
    try { window.speechSynthesis?.cancel(); } catch {}
    try { recognitionRef.current?.stop(); } catch {}
    try { recorderRef.current?.stop(); } catch {}
    audioRef.current?.pause();
    setListening(false);
    setSpeaking(false);
  }

  async function speak(text: string, lang: string) {
    if (muted) return;

    if (ttsMode === "browser" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = BCP47[lang] || "en-IN";
        utterance.rate = 1.0;
        utterance.onstart = () => setSpeaking(true);
        utterance.onend = () => setSpeaking(false);
        utterance.onerror = () => setSpeaking(false);
        window.speechSynthesis.speak(utterance);
        return;
      } catch {
        setSpeaking(false);
      }
    }

    // Server TTS fallback (browsers without speechSynthesis)
    try {
      setSpeaking(true);
      const blob = await api.speakAudio(caseId, text, lang);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => { setSpeaking(false); URL.revokeObjectURL(url); };
      audio.onerror = () => setSpeaking(false);
      await audio.play();
    } catch (e: any) {
      setSpeaking(false);
      setTtsMode("none");
      // Surface once: server TTS unavailable — text answers still readable
      setError(e.message || "Server text-to-speech unavailable; answers will be text-only.");
    }
  }

  async function sendTranscript(transcript: string, sttProvider?: string) {
    if (!sessionId || thinking) return;
    setThinking(true);
    setError(null);
    setTurns((t) => [...t, { role: "user", content: transcript, language }]);

    try {
      const result = await api.voiceMessage(caseId, sessionId, transcript, language, sttProvider);
      setTurns((t) => [...t, {
        role: "assistant",
        content: result.answer,
        citations: result.citations,
        language: result.language,
      }]);
      speak(result.answer, result.language || language);
    } catch (e: any) {
      setError(e.message || "Voice agent failed");
    } finally {
      setThinking(false);
    }
  }

  // ---- Browser STT (Chrome/Edge) ----
  const startListening = useCallback(() => {
    if (!sessionId || thinking) return;
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    setError(null);
    const recognition = new SpeechRecognition();
    recognition.lang = BCP47[language] || "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = (event: any) => {
      setListening(false);
      if (event.error === "not-allowed") {
        setError("Microphone permission denied. Allow mic access to speak.");
      } else if (event.error === "no-speech") {
        setError("No speech detected. Try again.");
      }
    };
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      if (transcript?.trim()) {
        sendTranscript(transcript.trim(), "browser-webspeech");
      }
    };

    recognitionRef.current = recognition;
    try { window.speechSynthesis?.cancel(); } catch {}
    recognition.start();
  }, [sessionId, language, thinking]);

  // ---- Server STT via MediaRecorder (Safari/Firefox fallback) ----
  const startServerRecording = useCallback(async () => {
    if (!sessionId || thinking) return;
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks: BlobPart[] = [];
      const mimeType = (window as any).MediaRecorder?.isTypeSupported?.("audio/webm")
        ? "audio/webm"
        : "audio/mp4"; // Safari
      const recorder = new MediaRecorder(stream, { mimeType });
      recorderRef.current = recorder;
      setListening(true);

      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setListening(false);
        const blob = new Blob(chunks, { type: mimeType });
        if (blob.size === 0) return;
        try {
          const result = await api.transcribeAudio(caseId, blob);
          if (result.transcript?.trim()) {
            await sendTranscript(result.transcript.trim(), "server-whisper");
          } else {
            setError("No speech detected in the recording.");
          }
        } catch (e: any) {
          setError(e.message || "Transcription failed.");
        }
      };
      recorder.start();
    } catch (e: any) {
      setListening(false);
      setError(
        e?.name === "NotAllowedError"
          ? "Microphone permission denied. Allow mic access to speak."
          : e.message || "Could not access the microphone."
      );
    }
  }, [sessionId, caseId, thinking]);

  function toggleListening() {
    if (listening) {
      if (recorderRef.current?.state === "recording") recorderRef.current.stop();
      else recognitionRef.current?.stop();
      return;
    }
    if (sttMode === "browser") startListening();
    else startServerRecording();
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Voice Assistant</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Speak about any document — answers cite their source page. Responds in your language.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-border bg-bg-surface px-2.5 py-1.5">
            <Languages size={14} className="text-text-muted" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={listening}
              className="bg-transparent text-xs text-white outline-none"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} className="bg-bg-surface">
                  {l.label}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => {
              setMuted(!muted);
              if (!muted) {
                try { window.speechSynthesis?.cancel(); } catch {}
                audioRef.current?.pause();
                setSpeaking(false);
              }
            }}
            title={muted ? "Unmute responses" : "Mute responses"}
            className="rounded-lg border border-border bg-bg-surface p-2 text-text-muted transition-colors hover:text-white"
          >
            {muted ? <VolumeX size={16} /> : <Volume2 size={16} className={speaking ? "text-primary" : ""} />}
          </button>
        </div>
      </div>

      {!sttSupported && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          This browser has no built-in speech recognition. Voice input will use the
          server transcription provider{""}
          {sttMode === "server" ? "" : " (unavailable)"} — answers are always shown as text.
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Conversation */}
      <Card className="mt-6 flex-1 overflow-y-auto p-6">
        {!sessionId ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-primary/30 bg-primary/10">
              <Mic size={28} className="text-primary" />
            </div>
            <h3 className="text-base font-semibold text-white">Jurisiva Legal Assistant</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-text-secondary">
              Start a session and ask things like &ldquo;What does this old paper say?&rdquo;
              or &ldquo;Who are the parties in the sale deed?&rdquo; — answers open the source page.
            </p>
            <p className="mt-4 text-xs text-text-muted">
              This is an AI assistant, not a human lawyer.
            </p>
            <Button onClick={startSession} className="mt-6">
              <Mic size={15} /> Start Voice Session
            </Button>
          </div>
        ) : (
          <div className="space-y-5">
            {turns.map((turn, i) => (
              <div key={i} className={turn.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div className={
                  turn.role === "user"
                    ? "max-w-[85%] rounded-2xl rounded-br-md bg-primary px-5 py-3.5"
                    : "max-w-[90%] rounded-2xl rounded-bl-md border border-border bg-bg px-5 py-3.5"
                }>
                  {turn.role === "user" ? (
                    <p className="text-sm leading-relaxed text-white">{turn.content}</p>
                  ) : (
                    <>
                      <div className="mb-1.5 flex items-center gap-2 text-[10px] uppercase tracking-wider text-text-muted">
                        {speaking && i === turns.length - 1 && (
                          <Volume2 size={11} className="animate-pulse text-primary" />
                        )}
                        {turn.language && turn.language !== "en" && `(${turn.language})`}
                      </div>
                      <pre className="whitespace-pre-wrap text-sm leading-relaxed text-text-secondary">{turn.content}</pre>
                      {turn.citations && turn.citations.length > 0 && (
                        <div className="mt-3 border-t border-border pt-3">
                          {turn.citations.map((c: any, j: number) => (
                            <a
                              key={j}
                              href={`/cases/${caseId}/documents?doc=${c.document_id}&page=${c.page_number}`}
                              className="mt-1.5 flex items-start gap-2 text-xs text-blue-400 hover:text-blue-300"
                            >
                              <FileText size={12} className="mt-0.5 shrink-0" />
                              {c.document_name} · p.{c.page_number}
                            </a>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl border border-border bg-bg px-5 py-3.5">
                  <Loader2 size={14} className="animate-spin text-primary" />
                  <span className="text-xs text-text-muted">Listening to your documents…</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </Card>

      {/* Controls */}
      {sessionId && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button
            onClick={toggleListening}
            disabled={thinking}
            className={`flex h-16 w-16 items-center justify-center rounded-full transition-all ${
              listening
                ? "animate-pulse bg-red-500 text-white shadow-[0_0_30px_rgba(239,68,68,0.4)]"
                : "bg-primary text-white hover:bg-primary-hover disabled:opacity-40"
            }`}
            title={listening ? "Stop speaking" : "Tap and speak"}
          >
            {listening ? <MicOff size={24} /> : <Mic size={24} />}
          </button>
          <Button variant="secondary" onClick={endSession}>
            <PhoneOff size={15} /> End Session
          </Button>
        </div>
      )}
    </div>
  );
}

// Local helper to avoid adding more surface to the shared api client
async function fetchVoiceSession(caseId: string, language: string) {
  const { createClient } = await import("@/lib/supabase");
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/cases/${caseId}/voice/session`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
      },
      body: JSON.stringify({ language }),
    }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to create voice session");
  }
  return res.json();
}
