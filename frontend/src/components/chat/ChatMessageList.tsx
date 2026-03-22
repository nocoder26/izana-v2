'use client';

import { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import DaySeparator from './DaySeparator';
import StreamingText from './StreamingText';
import SourcePills from './SourcePills';
import SuggestedQuestions from './SuggestedQuestions';
import ChatCard from './cards/ChatCard';
import type { ChatMessage, Source } from './types';

interface ChatMessageListProps {
  messages: ChatMessage[];
  onSuggestedQuestion?: (question: string) => void;
  onSourceTap?: (source: Source) => void;
  onCardAction?: (action: string, payload?: unknown) => void;
}

export default function ChatMessageList({
  messages,
  onSuggestedQuestion,
  onSourceTap,
  onCardAction,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showNewMessagePill, setShowNewMessagePill] = useState(false);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const prevMessageCount = useRef(messages.length);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    bottomRef.current?.scrollIntoView({ behavior });
    setShowNewMessagePill(false);
  }, []);

  // Check if user is near the bottom of the scroll container
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const threshold = 100;
    const nearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight <
      threshold;
    setIsNearBottom(nearBottom);
    if (nearBottom) setShowNewMessagePill(false);
  }, []);

  // Auto-scroll or show pill when new messages arrive
  useEffect(() => {
    if (messages.length > prevMessageCount.current) {
      if (isNearBottom) {
        scrollToBottom();
      } else {
        setShowNewMessagePill(true);
      }
    }
    prevMessageCount.current = messages.length;
  }, [messages.length, isNearBottom, scrollToBottom]);

  // Initial scroll to bottom
  useEffect(() => {
    scrollToBottom('instant');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Group messages by day for separators
  const renderMessages = () => {
    let lastDay: number | null = null;
    const elements: React.ReactNode[] = [];

    messages.forEach((msg) => {
      // Day separator
      if (msg.day !== undefined && msg.day !== lastDay) {
        const isToday = true; // Simplified; in production derive from timestamp
        elements.push(
          <DaySeparator
            key={`day-${msg.day}`}
            label={isToday ? 'today' : `day ${msg.day}`}
            day={msg.day}
          />,
        );
        lastDay = msg.day;
      }

      // Card messages
      if (msg.messageType !== 'text' && msg.cardData) {
        elements.push(
          <div key={msg.id} className="px-4 py-1">
            <ChatCard message={msg} onAction={onCardAction} />
          </div>,
        );
        return;
      }

      // Text messages
      const isUser = msg.role === 'user';
      elements.push(
        <motion.div
          key={msg.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className={cn(
            'flex px-4 py-1',
            isUser ? 'justify-end' : 'justify-start',
          )}
        >
          <div className="flex items-end gap-2 max-w-[85%]">
            {/* Izana avatar */}
            {!isUser && (
              <div className="izana-avatar shrink-0 mb-1" aria-hidden="true" />
            )}

            <div
              className={cn(
                isUser ? 'user-bubble' : 'izana-bubble',
              )}
            >
              {msg.isStreaming ? (
                <StreamingText text={msg.content} />
              ) : (
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {msg.content}
                </p>
              )}
            </div>
          </div>
        </motion.div>,
      );

      // Sources (after assistant messages)
      if (!isUser && msg.sources && msg.sources.length > 0) {
        elements.push(
          <div key={`sources-${msg.id}`} className="px-4 pl-14">
            <SourcePills sources={msg.sources} onSourceTap={onSourceTap} />
          </div>,
        );
      }

      // Suggested questions (after assistant messages)
      if (!isUser && msg.suggestedQuestions && msg.suggestedQuestions.length > 0) {
        elements.push(
          <div key={`suggestions-${msg.id}`} className="px-4 pl-14">
            <SuggestedQuestions
              questions={msg.suggestedQuestions}
              onSelect={(q) => onSuggestedQuestion?.(q)}
            />
          </div>,
        );
      }
    });

    return elements;
  };

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto chat-scroll py-4"
      >
        {renderMessages()}
        <div ref={bottomRef} />
      </div>

      {/* "New message" pill */}
      <AnimatePresence>
        {showNewMessagePill && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
            onClick={() => scrollToBottom()}
            className={cn(
              'absolute bottom-4 left-1/2 -translate-x-1/2 z-10',
              'px-4 py-2 rounded-full',
              'bg-brand-primary text-white text-sm font-medium',
              'shadow-[0_4px_12px_rgba(74,61,143,0.25)]',
              'hover:opacity-90 transition-opacity',
            )}
          >
            ↓ New message
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
