'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ─────────────────────────────────────────────────── */

type TrainingData = {
  totalFeedback: number;
  helpfulCount: number;
  validForTraining: number;
  qualityScore: number; // 0-100
};

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function TrainingTab({ apiFetch }: Props) {
  const [data, setData] = useState<TrainingData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<TrainingData>('/admin/training')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const stats = data ?? { totalFeedback: 0, helpfulCount: 0, validForTraining: 0, qualityScore: 0 };

  const cards = [
    { label: 'Total Feedback', value: stats.totalFeedback.toLocaleString(), color: 'text-text-primary' },
    { label: 'Helpful', value: stats.helpfulCount.toLocaleString(), color: 'text-success' },
    { label: 'Valid for Training', value: stats.validForTraining.toLocaleString(), color: 'text-brand-primary' },
    { label: 'Quality Score', value: `${stats.qualityScore}%`, color: stats.qualityScore >= 80 ? 'text-success' : stats.qualityScore >= 60 ? 'text-warning' : 'text-error' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Overview cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <Card key={card.label}>
            <CardContent className="py-5">
              <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">
                {card.label}
              </p>
              <p className={cn('text-3xl font-semibold mt-1', card.color)}>
                {loading ? (
                  <span className="inline-block skeleton w-16 h-8 rounded-lg" />
                ) : (
                  card.value
                )}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quality score bar */}
      {!loading && data && (
        <Card className="mb-8 max-w-xl">
          <CardContent className="py-5">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Training Data Quality</h3>
            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-text-secondary">Quality Score</span>
                  <span className={cn('text-sm font-medium', cards[3].color)}>
                    {stats.qualityScore}%
                  </span>
                </div>
                <div className="h-3 rounded-full bg-canvas-sunken overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${stats.qualityScore}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className={cn(
                      'h-full rounded-full',
                      stats.qualityScore >= 80 ? 'bg-success' : stats.qualityScore >= 60 ? 'bg-warning' : 'bg-error',
                    )}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-text-secondary">Valid for training</span>
                  <span className="text-sm font-medium text-text-primary">
                    {stats.totalFeedback > 0
                      ? `${Math.round((stats.validForTraining / stats.totalFeedback) * 100)}%`
                      : '0%'}
                  </span>
                </div>
                <div className="h-3 rounded-full bg-canvas-sunken overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${stats.totalFeedback > 0 ? Math.round((stats.validForTraining / stats.totalFeedback) * 100) : 0}%`,
                    }}
                    transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
                    className="h-full rounded-full bg-brand-primary"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export */}
      <div className="flex items-center gap-4">
        <Button
          variant="secondary"
          size="md"
          onClick={() => {
            /* placeholder — export training data */
          }}
        >
          Export Training Data
        </Button>
        <p className="text-xs text-text-tertiary">
          Export valid feedback pairs for DPO fine-tuning.
        </p>
      </div>
    </motion.div>
  );
}
