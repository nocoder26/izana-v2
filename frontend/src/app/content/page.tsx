'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiGet } from '@/lib/api-client';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import MediaPlayer from '@/components/chat/MediaPlayer';

/* ── Types ─────────────────────────────────────────────────── */

type ContentItem = {
  id: string;
  title: string;
  type: 'exercise' | 'meditation';
  mediaType: 'video' | 'audio';
  src: string;
  thumbnailUrl?: string;
  duration: number; // seconds
  intensity?: 'low' | 'medium' | 'high';
  phases: string[];
  completed: boolean;
};

type ContentLibraryResponse = {
  items: ContentItem[];
};

/* ── Phase filters ─────────────────────────────────────────── */

const PHASES = ['All', 'Baseline', 'Stims', 'Trigger', 'Retrieval', 'Transfer', 'TWW', 'Recovery'];

/* ── Helpers ───────────────────────────────────────────────── */

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function intensityColor(intensity?: string): string {
  switch (intensity) {
    case 'low':
      return 'bg-success/15 text-success';
    case 'medium':
      return 'bg-warning/15 text-warning';
    case 'high':
      return 'bg-error/15 text-error';
    default:
      return 'bg-canvas-sunken text-text-tertiary';
  }
}

/* ── Component ─────────────────────────────────────────────── */

export default function ContentLibraryPage() {
  const [activeTab, setActiveTab] = useState<'exercise' | 'meditation'>('exercise');
  const [selectedPhase, setSelectedPhase] = useState('All');
  const [items, setItems] = useState<ContentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [navTab, setNavTab] = useState<TabId>('journey');

  // Media player state
  const [playerOpen, setPlayerOpen] = useState(false);
  const [activeItem, setActiveItem] = useState<ContentItem | null>(null);

  useEffect(() => {
    setLoading(true);
    apiGet<ContentLibraryResponse>('/content/library')
      .then((res) => setItems(res.items))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  const filteredItems = items.filter((item) => {
    if (item.type !== activeTab) return false;
    if (selectedPhase !== 'All' && !item.phases.includes(selectedPhase.toLowerCase())) return false;
    return true;
  });

  const handleItemClick = useCallback((item: ContentItem) => {
    setActiveItem(item);
    setPlayerOpen(true);
  }, []);

  const handleNavChange = (tab: TabId) => {
    setNavTab(tab);
    if (tab === 'today') window.location.href = '/chat';
    else if (tab === 'you') window.location.href = '/profile';
  };

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      <div className="flex-1 min-h-0 pb-[52px] overflow-y-auto">
        {/* Header */}
        <div className="px-5 pt-6 pb-2">
          <h1 className="text-xl font-semibold text-text-primary font-serif">Content Library</h1>
          <p className="text-sm text-text-secondary mt-1">Guided exercises and meditations for your journey</p>
        </div>

        {/* Tab toggle */}
        <div className="px-5 pt-3">
          <div className="flex bg-canvas-sunken rounded-xl p-1">
            {(['exercise', 'meditation'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  'flex-1 py-2 text-sm font-medium rounded-lg transition-all duration-200 capitalize',
                  activeTab === tab
                    ? 'bg-canvas-elevated text-text-primary shadow-sm'
                    : 'text-text-tertiary hover:text-text-secondary',
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Phase filter pills */}
        <div className="px-5 pt-4 pb-2 overflow-x-auto">
          <div className="flex gap-2 min-w-max">
            {PHASES.map((phase) => (
              <button
                key={phase}
                onClick={() => setSelectedPhase(phase)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-full transition-colors duration-150 whitespace-nowrap',
                  selectedPhase === phase
                    ? 'bg-brand-primary text-white'
                    : 'bg-canvas-sunken text-text-secondary hover:bg-border-default',
                )}
              >
                {phase}
              </button>
            ))}
          </div>
        </div>

        {/* Content grid */}
        <div className="px-5 pt-3 pb-6">
          {loading ? (
            <div className="grid grid-cols-2 gap-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton h-48 rounded-[14px]" />
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-text-tertiary text-sm">No content found for this filter.</p>
            </div>
          ) : (
            <motion.div
              className="grid grid-cols-2 gap-3"
              initial="hidden"
              animate="visible"
              variants={{
                hidden: {},
                visible: { transition: { staggerChildren: 0.05 } },
              }}
            >
              <AnimatePresence mode="popLayout">
                {filteredItems.map((item) => (
                  <motion.button
                    key={item.id}
                    variants={{
                      hidden: { opacity: 0, y: 12 },
                      visible: { opacity: 1, y: 0 },
                    }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    whileTap={{ scale: 0.97 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    onClick={() => handleItemClick(item)}
                    className={cn(
                      'relative flex flex-col rounded-[14px] border-[0.5px] border-border-default',
                      'bg-canvas-elevated overflow-hidden text-left',
                      'shadow-[0_1px_3px_rgba(42,36,51,0.04)]',
                      'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:outline-none',
                    )}
                  >
                    {/* Thumbnail placeholder */}
                    <div
                      className={cn(
                        'w-full aspect-[4/3] flex items-center justify-center',
                        item.type === 'exercise'
                          ? 'bg-gradient-to-br from-brand-accent/20 to-brand-primary/10'
                          : 'bg-gradient-to-br from-brand-primary/15 to-brand-accent/15',
                      )}
                    >
                      <span className="text-3xl">
                        {item.type === 'exercise' ? '\u{1F3CB}' : '\u{1F9D8}'}
                      </span>
                    </div>

                    {/* Completed badge */}
                    {item.completed && (
                      <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-success text-white flex items-center justify-center text-xs font-bold">
                        ✓
                      </div>
                    )}

                    {/* Content info */}
                    <div className="p-3 flex flex-col gap-1.5">
                      <h3 className="text-sm font-medium text-text-primary line-clamp-2 leading-tight">
                        {item.title}
                      </h3>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-text-tertiary">
                          {formatDuration(item.duration)}
                        </span>
                        {item.intensity && (
                          <span
                            className={cn(
                              'text-[10px] font-medium px-1.5 py-0.5 rounded-full capitalize',
                              intensityColor(item.intensity),
                            )}
                          >
                            {item.intensity}
                          </span>
                        )}
                      </div>
                    </div>
                  </motion.button>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>

      {/* Media Player */}
      {activeItem && (
        <MediaPlayer
          open={playerOpen}
          onClose={() => setPlayerOpen(false)}
          type={activeItem.mediaType}
          src={activeItem.src}
          title={activeItem.title}
          contentId={activeItem.id}
        />
      )}

      {/* Bottom navigation */}
      <BottomNav activeTab={navTab} onTabChange={handleNavChange} />
    </div>
  );
}
