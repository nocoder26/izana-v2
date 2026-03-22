'use client';

import { useState, useCallback, useRef } from 'react';
import { supabase } from '@/lib/supabase/client';

/* ── Types ────────────────────────────────────────────────────── */

export interface StreamSource {
  title: string;
  url?: string;
  snippet?: string;
}

export interface StreamingState {
  /** The accumulated response text (token by token) */
  streamingText: string;
  /** Current search animation stage (0-3), or -1 if not searching */
  currentStage: number;
  /** Sources discovered during search */
  sources: StreamSource[];
  /** Follow-up question suggestions */
  followUps: string[];
  /** Whether streaming is in progress */
  isStreaming: boolean;
  /** Error message, if any */
  error: string | null;
}

type SSEEventType =
  | 'stage'
  | 'source'
  | 'token'
  | 'followups'
  | 'done'
  | 'error';

interface SSEEvent {
  event: SSEEventType;
  data: string;
}

/* ── Hook ─────────────────────────────────────────────────────── */

export function useStreamingChat() {
  const [streamingText, setStreamingText] = useState('');
  const [currentStage, setCurrentStage] = useState(-1);
  const [sources, setSources] = useState<StreamSource[]>([]);
  const [followUps, setFollowUps] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setStreamingText('');
    setCurrentStage(-1);
    setSources([]);
    setFollowUps([]);
    setError(null);
  }, []);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  /**
   * Sends a message to the streaming chat endpoint and processes SSE events.
   *
   * SSE protocol:
   *   event: stage    data: { "stage": 0 }
   *   event: source   data: { "title": "...", "url": "..." }
   *   event: token    data: { "text": "word" }
   *   event: followups data: { "questions": ["...", "..."] }
   *   event: done     data: {}
   *   event: error    data: { "message": "..." }
   */
  const sendMessage = useCallback(
    async (content: string, conversationId?: string) => {
      // Abort any existing stream
      abortRef.current?.abort();

      const controller = new AbortController();
      abortRef.current = controller;

      reset();
      setIsStreaming(true);

      try {
        // Get current auth token
        const {
          data: { session },
        } = await supabase.auth.getSession();

        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (session?.access_token) {
          headers['Authorization'] = `Bearer ${session.access_token}`;
        }

        const response = await fetch(`${apiUrl}/api/v1/chat/stream`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            content,
            conversation_id: conversationId,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const body = await response.text().catch(() => '');
          throw new Error(`API ${response.status}: ${body || response.statusText}`);
        }

        if (!response.body) {
          throw new Error('Response body is empty');
        }

        // Parse the SSE stream using ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Parse SSE events from buffer
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? ''; // Keep incomplete last line in buffer

          let currentEvent: Partial<SSEEvent> = {};

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent.event = line.slice(7).trim() as SSEEventType;
            } else if (line.startsWith('data: ')) {
              currentEvent.data = line.slice(6);
            } else if (line === '' && currentEvent.event) {
              // Empty line = end of event
              processEvent(currentEvent as SSEEvent);
              currentEvent = {};
            }
          }
        }

        // Process any remaining event in buffer
        if (buffer.trim()) {
          const remainingLines = buffer.split('\n');
          let currentEvent: Partial<SSEEvent> = {};
          for (const line of remainingLines) {
            if (line.startsWith('event: ')) {
              currentEvent.event = line.slice(7).trim() as SSEEventType;
            } else if (line.startsWith('data: ')) {
              currentEvent.data = line.slice(6);
            }
          }
          if (currentEvent.event) {
            processEvent(currentEvent as SSEEvent);
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // User cancelled — not an error
          return;
        }
        setError(
          err instanceof Error ? err.message : 'Stream connection failed',
        );
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [reset],
  );

  function processEvent(event: SSEEvent) {
    try {
      const payload = JSON.parse(event.data || '{}');

      switch (event.event) {
        case 'stage':
          setCurrentStage(payload.stage ?? 0);
          break;

        case 'source':
          setSources((prev) => [
            ...prev,
            {
              title: payload.title ?? '',
              url: payload.url,
              snippet: payload.snippet,
            },
          ]);
          break;

        case 'token':
          setStreamingText((prev) => prev + (payload.text ?? ''));
          // Once tokens start flowing, we're past the search stages
          setCurrentStage(4);
          break;

        case 'followups':
          setFollowUps(payload.questions ?? []);
          break;

        case 'done':
          setIsStreaming(false);
          break;

        case 'error':
          setError(payload.message ?? 'Unknown error');
          setIsStreaming(false);
          break;
      }
    } catch {
      // Ignore unparseable events
    }
  }

  return {
    sendMessage,
    stopStreaming,
    reset,
    streamingText,
    currentStage,
    sources,
    followUps,
    isStreaming,
    error,
  };
}

export default useStreamingChat;
