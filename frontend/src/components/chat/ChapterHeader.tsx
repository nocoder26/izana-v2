'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { ChapterInfo } from './types';

interface ChapterHeaderProps {
  chapter: ChapterInfo;
  compact?: boolean;
  onShareWithDoctor?: () => void;
  onOpenSettings?: () => void;
  onToggleTheme?: () => void;
}

export default function ChapterHeader({
  chapter,
  compact = false,
  onShareWithDoctor,
  onOpenSettings,
  onToggleTheme,
}: ChapterHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <motion.header
      layout
      className={cn(
        'flex items-center justify-between w-full bg-canvas-elevated',
        'border-b border-border-default transition-all',
        compact ? 'px-4 py-2' : 'px-5 py-3',
      )}
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      {/* Left: Phase + Day */}
      <div className="flex items-baseline gap-1.5 min-w-0">
        <span
          className={cn(
            'font-semibold text-text-primary truncate transition-all',
            compact ? 'text-sm' : 'text-base',
          )}
        >
          Your {chapter.phaseName}
        </span>
        <span
          className={cn(
            'text-text-tertiary transition-all',
            compact ? 'text-xs' : 'text-sm',
          )}
        >
          &middot; day {chapter.day}
        </span>
      </div>

      {/* Right: Streak + Menu */}
      <div className="flex items-center gap-3 shrink-0">
        {/* Streak */}
        <div className="flex items-center gap-1">
          <span className="fire-pulse text-base" aria-label="Streak fire">
            🔥
          </span>
          <span
            className={cn(
              'font-medium text-text-primary',
              compact ? 'text-xs' : 'text-sm',
            )}
          >
            {chapter.streak}
          </span>
        </div>

        {/* 3-dot menu */}
        <div className="relative">
          <button
            onClick={() => setMenuOpen((prev) => !prev)}
            className="p-1.5 rounded-full hover:bg-canvas-sunken transition-colors"
            aria-label="Menu"
          >
            <span className="text-text-secondary text-lg leading-none select-none">
              &#8942;
            </span>
          </button>

          <AnimatePresence>
            {menuOpen && (
              <>
                {/* Backdrop */}
                <motion.div
                  className="fixed inset-0 z-40"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => setMenuOpen(false)}
                />
                {/* Dropdown */}
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -4 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -4 }}
                  transition={{ duration: 0.15 }}
                  className={cn(
                    'absolute right-0 top-full mt-1 z-50 w-48',
                    'bg-canvas-elevated rounded-xl border border-border-default overflow-hidden',
                  )}
                  style={{ boxShadow: '0 4px 12px rgba(42,36,51,0.08)' }}
                >
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onShareWithDoctor?.();
                    }}
                    className="w-full text-left px-4 py-3 text-sm text-text-primary
                      hover:bg-canvas-sunken transition-colors"
                  >
                    Share with doctor
                  </button>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onOpenSettings?.();
                    }}
                    className="w-full text-left px-4 py-3 text-sm text-text-primary
                      hover:bg-canvas-sunken transition-colors border-t border-border-default"
                  >
                    Settings
                  </button>
                  <button
                    onClick={() => {
                      setMenuOpen(false);
                      onToggleTheme?.();
                    }}
                    className="w-full text-left px-4 py-3 text-sm text-text-primary
                      hover:bg-canvas-sunken transition-colors border-t border-border-default"
                  >
                    Theme toggle
                  </button>
                </motion.div>
              </>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.header>
  );
}
