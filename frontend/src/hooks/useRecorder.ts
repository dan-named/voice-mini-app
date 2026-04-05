import { useState, useRef, useCallback } from "react";

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        requestWriteAccess?: (callback: (granted: boolean) => void) => void;
        ready?: () => void;
        expand?: () => void;
      };
    };
  }
}

export function useRecorder() {
  const [recording, setRecording] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);
  const mediaRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const requestMicAccess = useCallback(async (): Promise<MediaStream> => {
    // Try to get microphone access
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setPermissionError(null);
      return stream;
    } catch (err) {
      // On iOS Telegram WebView, getUserMedia may not be available
      // Try fallback: check if we're in Telegram WebApp context
      const tg = window.Telegram?.WebApp;
      if (tg) {
        setPermissionError(
          "Microphone not available in this browser. Try opening the link in a regular browser, or use Android."
        );
      } else {
        setPermissionError("Microphone access denied. Please allow microphone in browser settings.");
      }
      throw err;
    }
  }, []);

  const start = useCallback(async () => {
    const stream = await requestMicAccess();

    // Try opus first, fall back to default
    let recorder: MediaRecorder;
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
    } else {
      recorder = new MediaRecorder(stream);
    }

    chunksRef.current = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.start();
    mediaRef.current = recorder;
    setRecording(true);
  }, [requestMicAccess]);

  const stop = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = mediaRef.current;
      if (!recorder) return resolve(new Blob());

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mimeType });
        recorder.stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        resolve(blob);
      };

      recorder.stop();
    });
  }, []);

  return { recording, start, stop, permissionError };
}
