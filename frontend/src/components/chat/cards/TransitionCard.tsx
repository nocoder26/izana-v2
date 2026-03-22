'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { TransitionCardData } from '../types';

interface TransitionCardProps {
  data: TransitionCardData;
  onAction?: (action: string, payload?: unknown) => void;
}

export default function TransitionCard({ data, onAction }: TransitionCardProps) {
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
      <div className="px-4 py-4">
        <p className="text-xs text-text-tertiary font-medium mb-1">
          Day {data.day}
        </p>
        <p className="text-sm text-text-primary leading-relaxed mb-4">
          {data.message}
        </p>

        <div className="flex flex-col gap-2">
          {data.options.map((option, i) => (
            <motion.button
              key={option.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: i * 0.1 }}
              onClick={() => onAction?.('transition_select', { optionId: option.id })}
              className={cn(
                'w-full text-left px-4 py-3 rounded-xl text-sm',
                'border border-border-default',
                'hover:bg-brand-primary-bg hover:border-brand-primary',
                'transition-colors duration-200',
                'text-text-primary',
              )}
            >
              {option.label}
            </motion.button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
