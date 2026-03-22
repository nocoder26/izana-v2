'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface SearchStage {
  id: number;
  label: string;
  icon: string;
  completed: boolean;
  active: boolean;
}

interface Source {
  title: string;
  url?: string;
}

interface SearchAnimationProps {
  /** Whether to use cached timings (for landing page) or live stages */
  cached?: boolean;
  /** For live mode: the current stage index (0-3) */
  currentStage?: number;
  /** For live mode: sources found */
  sources?: Source[];
  /** Called when all cached stages complete */
  onComplete?: () => void;
  /** Number of sources to display in stage 3 */
  sourceCount?: number;
}

const DEFAULT_SOURCES: Source[] = [
  { title: 'Reproductive Biology & Endocrinology, 2023' },
  { title: 'Fertility and Sterility, 2024' },
  { title: 'Human Reproduction Update, 2023' },
];

const STAGE_DEFINITIONS = [
  { label: 'Understanding your question...', icon: '🔍' },
  { label: 'Searching clinical literature...', icon: '📚' },
  { label: 'Found {n} relevant sources...', icon: '📄' },
  { label: 'Crafting your answer...', icon: '✨' },
];

/** Cached timings: Stage 1 = 0.5s, Stage 2 = 1.0s, Stage 3 = 0.5s, Stage 4 = 0.5s */
const CACHED_TIMINGS = [500, 1000, 500, 500];

export default function SearchAnimation({
  cached = false,
  currentStage: liveStage,
  sources = DEFAULT_SOURCES,
  onComplete,
  sourceCount,
}: SearchAnimationProps) {
  const [stages, setStages] = useState<SearchStage[]>([]);
  const [visibleSources, setVisibleSources] = useState<Source[]>([]);

  // Cached mode: auto-progress through stages with timers
  useEffect(() => {
    if (!cached) return;

    let cancelled = false;
    const resolvedSourceCount = sourceCount ?? sources.length;

    async function runStages() {
      for (let i = 0; i < STAGE_DEFINITIONS.length; i++) {
        if (cancelled) return;

        setStages((prev) => [
          ...prev,
          {
            id: i,
            label: STAGE_DEFINITIONS[i].label.replace(
              '{n}',
              String(resolvedSourceCount),
            ),
            icon: STAGE_DEFINITIONS[i].icon,
            completed: false,
            active: true,
          },
        ]);

        // Show sources during stage 3 (index 2)
        if (i === 2) {
          for (let s = 0; s < sources.length; s++) {
            if (cancelled) return;
            await new Promise((r) => setTimeout(r, 120));
            setVisibleSources((prev) => [...prev, sources[s]]);
          }
        }

        await new Promise((r) => setTimeout(r, CACHED_TIMINGS[i]));

        if (cancelled) return;

        // Mark stage as completed
        setStages((prev) =>
          prev.map((stage) =>
            stage.id === i
              ? { ...stage, completed: true, active: false }
              : stage,
          ),
        );
      }

      onComplete?.();
    }

    runStages();
    return () => {
      cancelled = true;
    };
  }, [cached, sources, onComplete, sourceCount]);

  // Live mode: update stages based on liveStage prop
  useEffect(() => {
    if (cached || liveStage === undefined) return;

    const resolvedSourceCount = sourceCount ?? sources.length;

    const newStages: SearchStage[] = [];
    for (let i = 0; i <= liveStage && i < STAGE_DEFINITIONS.length; i++) {
      newStages.push({
        id: i,
        label: STAGE_DEFINITIONS[i].label.replace(
          '{n}',
          String(resolvedSourceCount),
        ),
        icon: STAGE_DEFINITIONS[i].icon,
        completed: i < liveStage,
        active: i === liveStage,
      });
    }
    setStages(newStages);

    if (liveStage >= 2) {
      setVisibleSources(sources);
    }
  }, [cached, liveStage, sources, sourceCount]);

  return (
    <div className="flex flex-col gap-2 py-2">
      <AnimatePresence mode="sync">
        {stages.map((stage) => (
          <motion.div
            key={stage.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className={`flex items-center gap-2 text-sm ${
              stage.completed ? 'text-text-tertiary' : 'text-text-secondary'
            }`}
          >
            <span
              className={`text-base ${
                stage.active && !stage.completed
                  ? 'animate-gentle-pulse'
                  : ''
              }`}
            >
              {stage.completed ? '✓' : stage.icon}
            </span>
            <span>{stage.label}</span>
          </motion.div>
        ))}
      </AnimatePresence>

      {/* Sources sliding in one by one */}
      <AnimatePresence mode="sync">
        {visibleSources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1 ml-6">
            {visibleSources.map((source, i) => (
              <motion.span
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.15, delay: i * 0.05 }}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-brand-primary-bg text-brand-primary border border-brand-primary/15"
              >
                {source.title}
              </motion.span>
            ))}
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
