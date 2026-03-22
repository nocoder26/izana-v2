'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiPost, apiGet } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

/* ── Types ────────────────────────────────────────────────────── */

interface PartnerDashboardData {
  primaryName: string;
  day: number;
  phaseName: string;
  mood: string | null;
  izanaMessage: string;
}

interface PartnerChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}

/* ── Component ────────────────────────────────────────────────── */

export default function PartnerView() {
  const [dashboard, setDashboard] = useState<PartnerDashboardData | null>(null);
  const [messages, setMessages] = useState<PartnerChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchDashboard() {
      try {
        const data = await apiGet<PartnerDashboardData>(
          '/api/v1/partner/dashboard',
        );
        if (!cancelled) setDashboard(data);
      } catch (err) {
        if (!cancelled)
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load partner dashboard',
          );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isSending) return;

      const userMsg: PartnerChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: content.trim(),
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput('');
      setIsSending(true);

      try {
        const reply = await apiPost<{ message: string }>(
          '/api/v1/partner/chat',
          { content: content.trim() },
        );
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: reply.message,
            createdAt: new Date().toISOString(),
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: 'Something went wrong. Please try again.',
            createdAt: new Date().toISOString(),
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [isSending],
  );

  const handleQuickAction = useCallback(
    (action: string) => {
      const prompts: Record<string, string> = {
        encourage: 'Help me write an encouraging message for my partner',
        meditation: 'I would like to do a couples meditation session',
        support: 'How can I best support my partner right now?',
      };
      sendMessage(prompts[action] ?? action);
    },
    [sendMessage],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  /* ── Loading State ─────────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
        <div className="flex-1 flex items-center justify-center">
          <div className="space-y-3 text-center">
            <div className="w-12 h-12 rounded-full skeleton mx-auto" />
            <div className="w-40 h-4 skeleton mx-auto rounded" />
            <div className="w-56 h-3 skeleton mx-auto rounded" />
          </div>
        </div>
      </div>
    );
  }

  /* ── Error State ───────────────────────────────────────────── */

  if (error || !dashboard) {
    return (
      <div className="flex flex-col h-dvh bg-canvas-base items-center justify-center p-6" style={{ minHeight: '100vh' }}>
        <p className="text-sm text-error text-center mb-4">
          {error ?? 'Could not load partner dashboard'}
        </p>
        <Button variant="secondary" onClick={() => window.location.reload()}>
          Try again
        </Button>
      </div>
    );
  }

  /* ── Main Render ───────────────────────────────────────────── */

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        className="bg-canvas-elevated border-b border-border-default px-5 py-4 shrink-0"
        style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
      >
        <h1 className="text-lg font-semibold text-text-primary">
          Supporting {dashboard.primaryName}
        </h1>
        <p className="text-sm text-text-secondary mt-0.5">
          {dashboard.phaseName} &middot; day {dashboard.day}
        </p>
      </header>

      {/* Scrollable Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto chat-scroll">
        <div className="px-5 py-5 space-y-4">
          {/* Izana's Partner Message */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
          >
            <Card>
              <CardContent>
                <div className="flex items-start gap-3">
                  <div className="izana-avatar shrink-0 mt-0.5" />
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-text-tertiary">
                      Izana
                    </p>
                    <p className="text-sm text-text-primary leading-relaxed">
                      {dashboard.izanaMessage}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Mood Indicator (if shared) */}
          {dashboard.mood && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: 0.1 }}
              className={cn(
                'rounded-xl border border-border-default bg-canvas-elevated',
                'px-4 py-3 flex items-center gap-3',
              )}
              style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
            >
              <span className="text-2xl">{dashboard.mood}</span>
              <div>
                <p className="text-xs text-text-tertiary">Current mood</p>
                <p className="text-sm font-medium text-text-primary">
                  {dashboard.primaryName} checked in today
                </p>
              </div>
            </motion.div>
          )}

          {/* Quick Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="grid grid-cols-1 gap-2"
          >
            {[
              {
                key: 'encourage',
                icon: '💬',
                label: 'Send encouragement',
              },
              {
                key: 'meditation',
                icon: '🧘',
                label: 'Couples meditation',
              },
              {
                key: 'support',
                icon: '❓',
                label: 'Ask about supporting',
              },
            ].map((action) => (
              <button
                key={action.key}
                onClick={() => handleQuickAction(action.key)}
                disabled={isSending}
                className={cn(
                  'flex items-center gap-3 px-4 py-3 rounded-xl',
                  'border border-border-default bg-canvas-elevated',
                  'hover:bg-canvas-sunken transition-colors text-left',
                  'disabled:opacity-50',
                )}
                style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
              >
                <span className="text-lg">{action.icon}</span>
                <span className="text-sm font-medium text-text-primary">
                  {action.label}
                </span>
              </button>
            ))}
          </motion.div>

          {/* Chat Messages */}
          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'flex',
                  msg.role === 'user' ? 'justify-end' : 'justify-start',
                )}
              >
                <div
                  className={
                    msg.role === 'user' ? 'user-bubble' : 'izana-bubble'
                  }
                >
                  <p className="text-sm">{msg.content}</p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          {isSending && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="izana-bubble">
                <div className="flex gap-1 py-1">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="w-2 h-2 rounded-full bg-text-tertiary"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{
                        duration: 1.2,
                        repeat: Infinity,
                        delay: i * 0.2,
                      }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Chat Input */}
      <div
        className={cn(
          'shrink-0 border-t border-border-default bg-canvas-elevated',
          'px-4 py-3 safe-area-bottom',
        )}
      >
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Izana anything about supporting your partner..."
            disabled={isSending}
            className={cn(
              'flex-1 rounded-xl border border-border-default bg-canvas-base',
              'px-4 py-2.5 text-[16px] text-text-primary',
              'placeholder:text-text-tertiary',
              'focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20',
              'disabled:opacity-50',
            )}
          />
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!input.trim() || isSending}
          >
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}
