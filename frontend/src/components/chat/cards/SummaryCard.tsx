'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { SummaryCardData } from '../types';

interface SummaryCardProps {
  data: SummaryCardData;
}

export default function SummaryCard({ data }: SummaryCardProps) {
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
      <div className="px-4 py-3 border-b border-border-default">
        <p className="text-sm font-semibold text-text-primary">
          day {data.day} — done
        </p>
      </div>

      <div className="px-4 py-3 flex flex-col gap-2">
        {data.items.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: i * 0.08 }}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-text-secondary">{item.label}:</span>
            <span
              className={cn(
                'font-medium',
                item.status === 'done' && 'text-success',
                item.status === 'skipped' && 'text-text-tertiary',
                item.status === 'partial' && 'text-warning',
              )}
            >
              {item.value}
              {item.status === 'done' && ' ✓'}
            </span>
          </motion.div>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-border-default flex items-center justify-between">
        <span className="text-sm font-medium text-brand-primary">
          +{data.points} points
        </span>
        <span className="text-sm text-text-secondary">
          <span className="fire-pulse inline-block">🔥</span>{' '}
          {data.streakDays}-day
        </span>
      </div>
    </motion.div>
  );
}
