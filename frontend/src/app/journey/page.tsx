'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import { apiGet, apiPost } from '@/lib/api-client';
import { supabase } from '@/lib/supabase/client';
import ShareModal from '@/components/sharing/ShareModal';
import type { JourneyPhase } from '@/components/chat/types';

/* ── Types ─────────────────────────────────────────────────── */

type CheckinEntry = {
  date: string;
  mood: number;
  energy?: number;
};

type ChapterMessage = {
  id: string;
  role: string;
  content: string;
  created_at: string;
};

// Placeholder data; in production, fetch from API
const MOCK_PHASES: JourneyPhase[] = [
  { id: 'baseline', name: 'Baseline', status: 'completed', totalDays: 5 },
  { id: 'stims', name: 'Stimulation', status: 'active', day: 8, totalDays: 14 },
  { id: 'trigger', name: 'Trigger', status: 'upcoming', totalDays: 2 },
  { id: 'retrieval', name: 'Retrieval', status: 'upcoming', totalDays: 1 },
  { id: 'recovery', name: 'Recovery', status: 'upcoming', totalDays: 7 },
  { id: 'transfer', name: 'Transfer', status: 'upcoming', totalDays: 1 },
  { id: 'tww', name: 'Two-Week Wait', status: 'upcoming', totalDays: 14 },
];

/* ── Inline Mood Chart (using Recharts) ─────────────────────── */

function MoodTrendsPanel({ onClose }: { onClose: () => void }) {
  const [history, setHistory] = useState<CheckinEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [ChartComponents, setChartComponents] = useState<{
    ResponsiveContainer: any;
    LineChart: any;
    Line: any;
    XAxis: any;
    YAxis: any;
    Tooltip: any;
    CartesianGrid: any;
  } | null>(null);

  useEffect(() => {
    // Dynamically import Recharts to avoid SSR issues
    import('recharts').then((mod) => {
      setChartComponents({
        ResponsiveContainer: mod.ResponsiveContainer,
        LineChart: mod.LineChart,
        Line: mod.Line,
        XAxis: mod.XAxis,
        YAxis: mod.YAxis,
        Tooltip: mod.Tooltip,
        CartesianGrid: mod.CartesianGrid,
      });
    });

    apiGet<{ history: CheckinEntry[] }>('/companion/checkin/history')
      .then((res) => setHistory(res.history ?? []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, []);

  const chartData = history.map((entry) => ({
    date: new Date(entry.date).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
    mood: entry.mood,
    energy: entry.energy ?? 0,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="mx-5 mb-4 bg-canvas-elevated rounded-2xl border border-border-default p-4"
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Mood & Energy Trends</h3>
        <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">
          Close
        </button>
      </div>

      {loading ? (
        <div className="h-40 flex items-center justify-center">
          <p className="text-sm text-text-tertiary">Loading trends...</p>
        </div>
      ) : chartData.length === 0 ? (
        <div className="h-32 flex items-center justify-center">
          <p className="text-sm text-text-tertiary text-center">
            No check-in data yet. Complete daily check-ins to see your mood trends here.
          </p>
        </div>
      ) : ChartComponents ? (
        <div className="h-48">
          <ChartComponents.ResponsiveContainer width="100%" height="100%">
            <ChartComponents.LineChart data={chartData}>
              <ChartComponents.CartesianGrid strokeDasharray="3 3" stroke="var(--border-default, #e5e5e5)" />
              <ChartComponents.XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: 'var(--text-tertiary, #999)' }}
                tickLine={false}
              />
              <ChartComponents.YAxis
                domain={[0, 5]}
                tick={{ fontSize: 10, fill: 'var(--text-tertiary, #999)' }}
                tickLine={false}
                width={24}
              />
              <ChartComponents.Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: '1px solid var(--border-default, #e5e5e5)',
                  fontSize: 12,
                }}
              />
              <ChartComponents.Line
                type="monotone"
                dataKey="mood"
                stroke="#4A3D8F"
                strokeWidth={2}
                dot={{ r: 3, fill: '#4A3D8F' }}
                name="Mood"
              />
              <ChartComponents.Line
                type="monotone"
                dataKey="energy"
                stroke="#C4956A"
                strokeWidth={2}
                dot={{ r: 3, fill: '#C4956A' }}
                name="Energy"
              />
            </ChartComponents.LineChart>
          </ChartComponents.ResponsiveContainer>
        </div>
      ) : (
        <div className="h-40 flex items-center justify-center">
          <p className="text-sm text-text-tertiary">Loading chart...</p>
        </div>
      )}
    </motion.div>
  );
}

/* ── Bloodwork Upload Panel ─────────────────────────────────── */

function BloodworkPanel({ onClose }: { onClose: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${apiUrl}/bloodwork/analyze-file`, {
        method: 'POST',
        headers: session?.access_token
          ? { Authorization: `Bearer ${session.access_token}` }
          : {},
        body: formData,
      });

      if (!response.ok) throw new Error('Upload failed');
      const data = await response.json();
      setResult(data.summary ?? 'Bloodwork uploaded successfully. Results will appear in your chat.');
      // Auto-close and redirect to chat after 2 seconds
      setTimeout(() => {
        onClose();
        window.location.href = '/chat';
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload bloodwork');
    } finally {
      setUploading(false);
    }
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="mx-5 mb-4 bg-canvas-elevated rounded-2xl border border-border-default p-4"
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">Upload Bloodwork</h3>
        <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">
          Close
        </button>
      </div>

      <p className="text-xs text-text-secondary mb-3">
        Upload a photo or PDF of your bloodwork results for AI analysis.
      </p>

      <label
        className={cn(
          'flex flex-col items-center gap-2 py-6 rounded-xl border-2 border-dashed cursor-pointer',
          'border-border-default hover:border-brand-primary/40 transition-colors',
          uploading && 'opacity-50 pointer-events-none',
        )}
      >
        <span className="text-2xl">{uploading ? '...' : '📄'}</span>
        <span className="text-xs text-text-secondary">
          {uploading ? 'Uploading...' : 'Tap to select file'}
        </span>
        <input
          type="file"
          accept="image/*,.pdf"
          className="hidden"
          onChange={handleFileUpload}
          disabled={uploading}
        />
      </label>

      {result && (
        <p className="text-xs text-success mt-3">{result}</p>
      )}
      {error && (
        <p className="text-xs text-error mt-3">{error}</p>
      )}
    </motion.div>
  );
}

/* ── Phase Messages Panel ───────────────────────────────────── */

function PhaseMessagesPanel({ phaseId, phaseName, onClose }: { phaseId: string; phaseName: string; onClose: () => void }) {
  const [messages, setMessages] = useState<ChapterMessage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<{ messages: ChapterMessage[] }>(`/chapters/${phaseId}/messages`)
      .then((res) => setMessages(res.messages ?? []))
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  }, [phaseId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="mx-5 mb-4 bg-canvas-elevated rounded-2xl border border-border-default p-4 max-h-64 overflow-y-auto"
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">{phaseName} Messages</h3>
        <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">
          Close
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-text-tertiary">Loading...</p>
      ) : messages.length === 0 ? (
        <p className="text-sm text-text-tertiary">No messages recorded for this phase.</p>
      ) : (
        <div className="space-y-2">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'text-xs p-2 rounded-lg',
                msg.role === 'assistant' ? 'bg-canvas-sunken text-text-primary' : 'bg-brand-primary-bg text-text-primary',
              )}
            >
              <p>{msg.content}</p>
              <p className="text-[10px] text-text-tertiary mt-1">
                {new Date(msg.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

/* ── Main Page ──────────────────────────────────────────────── */

export default function JourneyPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabId>('journey');
  const [showBloodwork, setShowBloodwork] = useState(false);
  const [showTrends, setShowTrends] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [selectedPhase, setSelectedPhase] = useState<JourneyPhase | null>(null);

  const QUICK_ACTIONS = [
    { emoji: '🩸', label: 'Bloodwork', action: () => setShowBloodwork((v) => !v) },
    { emoji: '📊', label: 'Trends', action: () => setShowTrends((v) => !v) },
    { emoji: '🩺', label: 'Doctor', action: () => setShowShareModal(true) },
  ];

  const handleTabChange = (tab: TabId) => {
    // Close all panels before navigating
    setShowBloodwork(false);
    setShowTrends(false);
    setShowShareModal(false);
    setSelectedPhase(null);
    setActiveTab(tab);
    if (tab === 'today') {
      router.push('/chat');
    } else if (tab === 'you') {
      router.push('/profile');
    }
  };

  const handlePhaseClick = (phase: JourneyPhase) => {
    if (phase.status === 'completed') {
      setSelectedPhase(selectedPhase?.id === phase.id ? null : phase);
    }
  };

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        className="bg-canvas-elevated border-b border-border-default px-5 py-4"
        style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
      >
        <h1 className="text-lg font-semibold text-text-primary">Your Journey</h1>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto pb-[68px]">
        {/* Quick Actions */}
        <div className="px-5 py-4 flex gap-3">
          {QUICK_ACTIONS.map((action) => (
            <motion.button
              key={action.label}
              whileTap={{ scale: 0.95 }}
              onClick={action.action}
              className={cn(
                'flex-1 flex flex-col items-center gap-1.5 py-3 rounded-xl',
                'bg-canvas-elevated border border-border-default',
                'hover:bg-canvas-sunken transition-colors cursor-pointer',
              )}
              style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
            >
              <span className="text-xl">{action.emoji}</span>
              <span className="text-xs font-medium text-text-secondary">
                {action.label}
              </span>
            </motion.button>
          ))}
        </div>

        {/* Inline Panels */}
        <AnimatePresence>
          {showBloodwork && (
            <BloodworkPanel onClose={() => setShowBloodwork(false)} />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showTrends && (
            <MoodTrendsPanel onClose={() => setShowTrends(false)} />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {selectedPhase && (
            <PhaseMessagesPanel
              phaseId={selectedPhase.id}
              phaseName={selectedPhase.name}
              onClose={() => setSelectedPhase(null)}
            />
          )}
        </AnimatePresence>

        {/* Timeline */}
        <div className="px-5 py-2">
          <div className="relative">
            {/* Vertical line */}
            <div
              className="absolute left-[11px] top-4 bottom-4 w-0.5 bg-border-default"
              aria-hidden="true"
            />

            <div className="flex flex-col gap-1">
              {MOCK_PHASES.map((phase, i) => (
                <motion.div
                  key={phase.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.08 }}
                  className={cn(
                    'relative flex items-start gap-4 py-3',
                    phase.status === 'completed' && 'cursor-pointer',
                  )}
                  onClick={() => handlePhaseClick(phase)}
                >
                  {/* Dot */}
                  <div
                    className={cn(
                      'relative z-10 w-6 h-6 rounded-full shrink-0',
                      'flex items-center justify-center',
                      'border-2',
                      phase.status === 'completed' &&
                        'bg-success border-success text-white',
                      phase.status === 'active' &&
                        'bg-brand-primary border-brand-primary text-white',
                      phase.status === 'upcoming' &&
                        'bg-canvas-elevated border-border-default',
                    )}
                  >
                    {phase.status === 'completed' && (
                      <span className="text-xs">✓</span>
                    )}
                    {phase.status === 'active' && (
                      <span className="w-2 h-2 rounded-full bg-white" />
                    )}
                  </div>

                  {/* Content */}
                  <div
                    className={cn(
                      'flex-1 rounded-xl px-4 py-3',
                      phase.status === 'active' &&
                        'bg-canvas-elevated border border-brand-primary',
                      phase.status === 'completed' &&
                        'bg-canvas-sunken hover:bg-canvas-elevated transition-colors',
                      phase.status === 'upcoming' &&
                        'bg-canvas-sunken opacity-60',
                    )}
                    style={
                      phase.status === 'active'
                        ? { boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }
                        : undefined
                    }
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={cn(
                          'text-sm font-medium',
                          phase.status === 'active'
                            ? 'text-brand-primary'
                            : 'text-text-primary',
                        )}
                      >
                        {phase.name}
                      </span>
                      {phase.status === 'active' && phase.day && (
                        <span className="text-xs text-brand-primary font-medium">
                          day {phase.day} →
                        </span>
                      )}
                      {phase.status === 'completed' && (
                        <span className="text-xs text-success font-medium">
                          ✓ tap to view
                        </span>
                      )}
                    </div>
                    {phase.totalDays && (
                      <p className="text-xs text-text-tertiary mt-0.5">
                        {phase.totalDays} days
                      </p>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Share Modal (Doctor) */}
      <ShareModal open={showShareModal} onOpenChange={setShowShareModal} />

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
