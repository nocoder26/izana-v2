'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import type { JourneyPhase } from '@/components/chat/types';

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

const QUICK_ACTIONS = [
  { emoji: '🩸', label: 'Bloodwork', action: () => alert('Bloodwork upload coming soon! You can upload bloodwork results in the Chat tab.') },
  { emoji: '📊', label: 'Trends', action: () => alert('Mood and adherence trends will be available after your first week of check-ins.') },
  { emoji: '🩺', label: 'Doctor', action: () => alert('Share your journey with your doctor — this feature is coming soon!') },
];

export default function JourneyPage() {
  const [activeTab, setActiveTab] = useState<TabId>('journey');

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    if (tab === 'today') {
      window.location.href = '/chat';
    } else if (tab === 'you') {
      window.location.href = '/profile';
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
                  className="relative flex items-start gap-4 py-3"
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
                        'bg-canvas-sunken',
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
                          ✓
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

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
