'use client';

import { useState, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useChatStore } from '@/stores/chat-store';
import { apiPost } from '@/lib/api-client';
import ChapterHeader from './ChapterHeader';
import ChatMessageList from './ChatMessageList';
import SearchAnimation from './SearchAnimation';
import MediaPlayer from './MediaPlayer';
import type {
  ChatMessage,
  ChapterInfo,
  Source,
  ExerciseItem,
  MeditationItem,
} from './types';

interface ChatInterfaceProps {
  chapter: ChapterInfo;
}

export default function ChatInterface({ chapter }: ChatInterfaceProps) {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const addMessage = useChatStore((s) => s.addMessage);
  const updateMessage = useChatStore((s) => s.updateMessage);
  const setStreaming = useChatStore((s) => s.setStreaming);

  const [inputValue, setInputValue] = useState('');
  const [headerCompact, setHeaderCompact] = useState(false);
  const [searchStage, setSearchStage] = useState<number | undefined>(undefined);
  const [searchSources, setSearchSources] = useState<Source[]>([]);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Media player state
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaType, setMediaType] = useState<'video' | 'audio'>('video');
  const [mediaSrc, setMediaSrc] = useState('');
  const [mediaTitle, setMediaTitle] = useState('');
  const [mediaContentId, setMediaContentId] = useState<string | undefined>();

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: text.trim(),
        messageType: 'text',
        timestamp: new Date().toISOString(),
        createdAt: new Date().toISOString(),
        day: chapter.day,
      };

      addMessage(userMsg as any);
      setInputValue('');
      setStreaming(true);
      setSearchStage(0);

      try {
        // Stage progression simulation via SSE
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL ?? ''}/companion/chat`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text.trim() }),
          },
        );

        if (!response.ok) throw new Error('Chat failed');

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No stream');

        const decoder = new TextDecoder();
        const assistantId = `assistant-${Date.now()}`;
        let fullContent = '';
        let assistantAdded = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(Boolean);

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const payload = line.slice(6);
            if (payload === '[DONE]') break;

            try {
              const event = JSON.parse(payload);

              // Search stage updates
              if (event.type === 'stage') {
                setSearchStage(event.stage);
                if (event.sources) setSearchSources(event.sources);
                continue;
              }

              // Text content
              if (event.type === 'content' || event.type === 'delta') {
                fullContent += event.content ?? event.delta ?? '';

                if (!assistantAdded) {
                  addMessage({
                    id: assistantId,
                    role: 'assistant',
                    content: fullContent,
                    messageType: 'text',
                    createdAt: new Date().toISOString(),
                  });
                  assistantAdded = true;
                } else {
                  updateMessage(assistantId, { content: fullContent });
                }
              }

              // Card messages
              if (event.type === 'card') {
                addMessage({
                  id: `card-${Date.now()}`,
                  role: 'assistant',
                  content: event.text ?? '',
                  messageType: event.cardType,
                  cardData: event.cardData,
                  createdAt: new Date().toISOString(),
                });
              }

              // Sources
              if (event.type === 'sources' && assistantAdded) {
                updateMessage(assistantId, { sources: event.sources });
              }

              // Follow-up suggestions
              if (event.type === 'followups' && assistantAdded) {
                updateMessage(assistantId, { followUps: event.questions });
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      } catch (error) {
        // Add error message
        addMessage({
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'I had trouble responding. Please try again.',
          messageType: 'text',
          createdAt: new Date().toISOString(),
        });
      } finally {
        setStreaming(false);
        setSearchStage(undefined);
        setSearchSources([]);
      }
    },
    [isStreaming, chapter.day, addMessage, updateMessage, setStreaming],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(inputValue);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  const handleSuggestedQuestion = (question: string) => {
    sendMessage(question);
  };

  const handleCardAction = (action: string, payload?: unknown) => {
    // Handle media playback actions
    if (action === 'play_video') {
      const p = payload as { exercise: ExerciseItem };
      setMediaType('video');
      setMediaSrc(p.exercise.videoUrl);
      setMediaTitle(p.exercise.title);
      setMediaContentId(p.exercise.id);
      setMediaOpen(true);
      return;
    }
    if (action === 'play_audio') {
      const p = payload as { meditation: MeditationItem };
      setMediaType('audio');
      setMediaSrc(p.meditation.audioUrl);
      setMediaTitle(p.meditation.title);
      setMediaContentId(p.meditation.id);
      setMediaOpen(true);
      return;
    }

    // Handle check-in
    if (action === 'checkin_submit') {
      apiPost('/companion/checkin', payload).catch(() => {});
      return;
    }

    // Handle meal/exercise/meditation done
    if (action.endsWith('_done')) {
      apiPost('/companion/activity', { action, ...payload as Record<string, unknown> }).catch(() => {});
      return;
    }

    // Handle transition selection
    if (action === 'transition_select') {
      const p = payload as { optionId: string };
      sendMessage(
        messages.length > 0
          ? `Selected option: ${p.optionId}`
          : p.optionId,
      );
    }
  };

  // Map store messages to local ChatMessage type for the list
  const mappedMessages: ChatMessage[] = messages.map((m) => ({
    id: m.id,
    role: m.role === 'assistant' ? 'assistant' : m.role === 'user' ? 'user' : 'system',
    content: m.content,
    messageType: (m.messageType as ChatMessage['messageType']) || 'text',
    cardData: m.cardData as ChatMessage['cardData'],
    sources: m.sources?.map((s, i) => ({ id: String(i), ...s })),
    suggestedQuestions: m.followUps,
    timestamp: m.createdAt,
    createdAt: m.createdAt,
    day: chapter.day,
    isStreaming: false,
  }));

  return (
    <div className="flex flex-col h-full bg-canvas-base">
      {/* Chapter Header */}
      <ChapterHeader chapter={chapter} compact={headerCompact} />

      {/* Message List */}
      <ChatMessageList
        messages={mappedMessages}
        onSuggestedQuestion={handleSuggestedQuestion}
        onCardAction={handleCardAction}
      />

      {/* Search Animation (when streaming) */}
      {isStreaming && searchStage !== undefined && (
        <div className="px-4 pb-2">
          <div className="flex items-start gap-2">
            <div className="izana-avatar shrink-0 mt-1" />
            <div className="izana-bubble flex-1">
              <SearchAnimation
                currentStage={searchStage}
                sources={searchSources.map((s) => ({
                  title: s.title,
                  url: s.url,
                }))}
              />
            </div>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div
        className={cn(
          'border-t border-border-default bg-canvas-elevated',
          'px-4 py-3 safe-area-bottom',
        )}
      >
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              // Auto-resize
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setHeaderCompact(true)}
            onBlur={() => setHeaderCompact(false)}
            placeholder="Message Izana..."
            disabled={isStreaming}
            rows={1}
            className={cn(
              'flex-1 resize-none rounded-xl border border-border-default',
              'bg-canvas-base px-4 py-2.5',
              'text-sm text-text-primary placeholder:text-text-tertiary',
              'focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20',
              'transition-colors duration-150',
              'disabled:opacity-50',
              'max-h-[120px]',
            )}
            style={{ fontSize: '16px' }} // Prevent iOS zoom
          />
          <motion.button
            type="submit"
            disabled={!inputValue.trim() || isStreaming}
            whileTap={{ scale: 0.95 }}
            className={cn(
              'shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
              'transition-colors duration-200',
              inputValue.trim() && !isStreaming
                ? 'bg-brand-primary text-white'
                : 'bg-canvas-sunken text-text-tertiary',
              'disabled:cursor-not-allowed',
            )}
            aria-label="Send message"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </motion.button>
        </form>
      </div>

      {/* Media Player */}
      <MediaPlayer
        open={mediaOpen}
        onClose={() => setMediaOpen(false)}
        type={mediaType}
        src={mediaSrc}
        title={mediaTitle}
        contentId={mediaContentId}
      />
    </div>
  );
}
