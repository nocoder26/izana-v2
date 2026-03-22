'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';

/* ── Types ─────────────────────────────────────────────────── */

type FeedbackEntry = {
  id: string;
  messageId: string;
  messagePreview: string;
  feedback: 'helpful' | 'not_helpful';
  comment?: string;
  createdAt: string;
};

type FeedbackData = {
  distribution: {
    helpful: number;
    notHelpful: number;
    total: number;
  };
  recentEntries: FeedbackEntry[];
};

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function FeedbackTab({ apiFetch }: Props) {
  const [data, setData] = useState<FeedbackData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<FeedbackData>('/admin/feedback')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const dist = data?.distribution ?? { helpful: 0, notHelpful: 0, total: 0 };
  const helpfulPct = dist.total > 0 ? Math.round((dist.helpful / dist.total) * 100) : 0;
  const notHelpfulPct = dist.total > 0 ? Math.round((dist.notHelpful / dist.total) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Distribution */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <Card>
          <CardContent className="py-5">
            <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">Helpful</p>
            <p className="text-3xl font-semibold text-success mt-1">
              {loading ? <span className="skeleton inline-block w-12 h-8 rounded-lg" /> : `${helpfulPct}%`}
            </p>
            <p className="text-xs text-text-tertiary mt-1">{dist.helpful.toLocaleString()} responses</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-5">
            <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">Not Helpful</p>
            <p className="text-3xl font-semibold text-error mt-1">
              {loading ? <span className="skeleton inline-block w-12 h-8 rounded-lg" /> : `${notHelpfulPct}%`}
            </p>
            <p className="text-xs text-text-tertiary mt-1">{dist.notHelpful.toLocaleString()} responses</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-5">
            <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">Total Feedback</p>
            <p className="text-3xl font-semibold text-text-primary mt-1">
              {loading ? <span className="skeleton inline-block w-12 h-8 rounded-lg" /> : dist.total.toLocaleString()}
            </p>
            <p className="text-xs text-text-tertiary mt-1">DPO entries</p>
          </CardContent>
        </Card>
      </div>

      {/* Distribution bar */}
      {!loading && dist.total > 0 && (
        <div className="mb-8">
          <div className="h-4 rounded-full overflow-hidden flex bg-canvas-sunken">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${helpfulPct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
              className="bg-success"
            />
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${notHelpfulPct}%` }}
              transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
              className="bg-error"
            />
          </div>
          <div className="flex items-center justify-between mt-2 text-xs text-text-tertiary">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-success" />
              Helpful ({helpfulPct}%)
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-error" />
              Not Helpful ({notHelpfulPct}%)
            </div>
          </div>
        </div>
      )}

      {/* Recent feedback */}
      <h3 className="text-sm font-semibold text-text-primary mb-3">Recent Feedback</h3>
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-20 rounded-xl" />
          ))}
        </div>
      ) : (!data?.recentEntries || data.recentEntries.length === 0) ? (
        <p className="text-sm text-text-tertiary text-center py-12">No feedback entries yet.</p>
      ) : (
        <div className="space-y-3">
          {data.recentEntries.map((entry, idx) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.03 }}
            >
              <Card>
                <CardContent className="py-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 mr-4">
                      <p className="text-sm text-text-primary line-clamp-2">{entry.messagePreview}</p>
                      {entry.comment && (
                        <p className="text-xs text-text-secondary mt-1 italic">&ldquo;{entry.comment}&rdquo;</p>
                      )}
                      <p className="text-[11px] text-text-tertiary mt-1.5">
                        {new Date(entry.createdAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </p>
                    </div>
                    <span
                      className={cn(
                        'text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap flex-shrink-0',
                        entry.feedback === 'helpful'
                          ? 'bg-success/15 text-success'
                          : 'bg-error/15 text-error',
                      )}
                    >
                      {entry.feedback === 'helpful' ? 'Helpful' : 'Not Helpful'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
