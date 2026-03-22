'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import MoodSelector from '../MoodSelector';
import type { CheckInCardData } from '../types';

interface CheckInCardProps {
  data: CheckInCardData;
  onAction?: (action: string, payload?: unknown) => void;
}

export default function CheckInCard({ data, onAction }: CheckInCardProps) {
  const [submitted, setSubmitted] = useState(data.submitted ?? false);
  const [selectedMood, setSelectedMood] = useState<string | null>(
    data.selectedMood ?? null,
  );

  const handleMoodSelect = (mood: string) => {
    setSelectedMood(mood);
    setSubmitted(true);
    onAction?.('checkin_submit', { mood });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={cn(
        'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
        'shadow-[0_1px_3px_rgba(42,36,51,0.04)] overflow-hidden',
      )}
    >
      <div className="px-4 py-3">
        <p className="text-sm text-text-primary leading-relaxed">
          {data.prompt}
        </p>

        <AnimatePresence mode="wait">
          {!submitted ? (
            <MoodSelector key="selector" onSelect={handleMoodSelect} />
          ) : (
            <motion.div
              key="summary"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              transition={{ duration: 0.3 }}
              className="mt-2"
            >
              <span className="text-sm text-text-secondary">
                Feeling {selectedMood} today
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
