'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiGet } from '@/lib/api-client';
import CelebrationCard from './CelebrationCard';
import type { PlanStatusCardData, PlanReviewStatus } from '../types';

interface PlanStatusCardProps {
  data: PlanStatusCardData;
  onAction?: (action: string, payload?: unknown) => void;
}

export default function PlanStatusCard({ data, onAction }: PlanStatusCardProps) {
  const [status, setStatus] = useState<PlanReviewStatus>(data.currentStatus);
  const [steps, setSteps] = useState(data.steps);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Poll /plan-status every 30 seconds until approved
  useEffect(() => {
    if (status === 'approved') return;

    intervalRef.current = setInterval(async () => {
      try {
        const result = await apiGet<{
          status: PlanReviewStatus;
          steps: typeof data.steps;
        }>('/plan-status');

        setStatus(result.status);
        setSteps(result.steps);

        if (result.status === 'approved') {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onAction?.('plan_approved', {});
        }
      } catch {
        // silently retry on next interval
      }
    }, 30_000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [status, onAction]);

  // When approved, show celebration
  if (status === 'approved') {
    return (
      <AnimatePresence mode="wait">
        <CelebrationCard
          data={{
            type: 'celebration',
            title: 'Your plan is ready!',
            subtitle: 'Reviewed and approved by our care team.',
          }}
        />
      </AnimatePresence>
    );
  }

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
          Plan Review Status
        </p>
      </div>

      <div className="px-4 py-3 flex flex-col gap-3">
        {steps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2, delay: i * 0.1 }}
            className="flex items-center justify-between text-sm"
          >
            <span
              className={cn(
                'font-medium',
                step.status === 'done' && 'text-text-primary',
                step.status === 'active' && 'text-brand-primary',
                step.status === 'pending' && 'text-text-tertiary',
              )}
            >
              {step.label}
            </span>

            <div className="flex items-center gap-2">
              <span className="text-text-tertiary text-xs">
                {step.time ?? '—'}
              </span>
              {step.status === 'done' && (
                <span className="text-success text-sm">✓</span>
              )}
              {step.status === 'active' && (
                <span className="animate-gentle-pulse text-brand-primary text-sm">
                  ⏳
                </span>
              )}
              {step.status === 'pending' && (
                <span className="text-text-tertiary text-sm">—</span>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
