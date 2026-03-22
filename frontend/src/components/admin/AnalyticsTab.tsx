'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ─────────────────────────────────────────────────── */

type GapItem = {
  id: string;
  question: string;
  count: number;
  lastAsked: string;
  reviewed: boolean;
};

type CitationItem = {
  id: string;
  documentTitle: string;
  citationCount: number;
  lastCited: string;
};

type SentimentData = {
  positive: number;
  neutral: number;
  negative: number;
  total: number;
};

type AnalyticsData = {
  gaps: GapItem[];
  citations: CitationItem[];
  sentiment: SentimentData;
};

type SortKey = 'question' | 'count';
type SortDir = 'asc' | 'desc';

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function AnalyticsTab({ apiFetch }: Props) {
  const [subTab, setSubTab] = useState<'gaps' | 'citations' | 'sentiment'>('gaps');
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  // Sort for gaps table
  const [gapSortKey, setGapSortKey] = useState<SortKey>('count');
  const [gapSortDir, setGapSortDir] = useState<SortDir>('desc');

  useEffect(() => {
    apiFetch<AnalyticsData>('/admin/analytics')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const handleGapSort = (key: SortKey) => {
    setGapSortDir((prev) => (gapSortKey === key ? (prev === 'asc' ? 'desc' : 'asc') : 'desc'));
    setGapSortKey(key);
  };

  const sortedGaps = useMemo(() => {
    if (!data) return [];
    const items = [...data.gaps];
    items.sort((a, b) => {
      let cmp = 0;
      if (gapSortKey === 'question') cmp = a.question.localeCompare(b.question);
      else cmp = a.count - b.count;
      return gapSortDir === 'asc' ? cmp : -cmp;
    });
    return items;
  }, [data, gapSortKey, gapSortDir]);

  const GapSortIcon = ({ column }: { column: SortKey }) => (
    <span className="inline-block ml-1 text-[10px]">
      {gapSortKey === column ? (gapSortDir === 'asc' ? '\u25B2' : '\u25BC') : '\u25B4'}
    </span>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Sub-tabs */}
      <div className="flex gap-0 border-b border-border-default mb-6">
        {(['gaps', 'citations', 'sentiment'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setSubTab(tab)}
            className={cn(
              'px-4 pb-3 text-sm font-medium border-b-2 transition-colors capitalize',
              subTab === tab
                ? 'border-brand-primary text-brand-primary'
                : 'border-transparent text-text-tertiary hover:text-text-secondary',
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-14 rounded-xl" />
          ))}
        </div>
      ) : (
        <>
          {/* Gaps */}
          {subTab === 'gaps' && (
            <div className="rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated overflow-hidden shadow-[0_1px_3px_rgba(42,36,51,0.04)]">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-default bg-canvas-sunken/50">
                    <th
                      onClick={() => handleGapSort('question')}
                      className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                    >
                      Question <GapSortIcon column="question" />
                    </th>
                    <th
                      onClick={() => handleGapSort('count')}
                      className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary w-24"
                    >
                      Count <GapSortIcon column="count" />
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-32">
                      Last Asked
                    </th>
                    <th className="text-right px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-28">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedGaps.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="text-center py-12 text-sm text-text-tertiary">
                        No unanswered questions found.
                      </td>
                    </tr>
                  ) : (
                    sortedGaps.map((gap) => (
                      <tr key={gap.id} className="border-b border-border-default last:border-b-0 hover:bg-canvas-sunken/30 transition-colors">
                        <td className="px-4 py-3">
                          <p className="text-sm text-text-primary">{gap.question}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-medium text-text-primary">{gap.count}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-text-tertiary">
                            {new Date(gap.lastAsked).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button variant={gap.reviewed ? 'ghost' : 'secondary'} size="sm">
                            {gap.reviewed ? 'Reviewed' : 'Review'}
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Citations */}
          {subTab === 'citations' && (
            <div className="rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated overflow-hidden shadow-[0_1px_3px_rgba(42,36,51,0.04)]">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border-default bg-canvas-sunken/50">
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide">
                      Document
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-32">
                      Citations
                    </th>
                    <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-32">
                      Last Cited
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(!data?.citations || data.citations.length === 0) ? (
                    <tr>
                      <td colSpan={3} className="text-center py-12 text-sm text-text-tertiary">
                        No citation data available.
                      </td>
                    </tr>
                  ) : (
                    data.citations.map((cit) => (
                      <tr key={cit.id} className="border-b border-border-default last:border-b-0 hover:bg-canvas-sunken/30 transition-colors">
                        <td className="px-4 py-3">
                          <p className="text-sm text-text-primary">{cit.documentTitle}</p>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-medium text-brand-primary">{cit.citationCount}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-xs text-text-tertiary">
                            {new Date(cit.lastCited).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* Sentiment */}
          {subTab === 'sentiment' && data?.sentiment && (
            <div className="max-w-lg">
              <Card>
                <CardContent className="py-6">
                  <h3 className="text-sm font-semibold text-text-primary mb-4">Mood Distribution</h3>
                  <div className="space-y-4">
                    {[
                      { label: 'Positive', value: data.sentiment.positive, total: data.sentiment.total, color: 'bg-success' },
                      { label: 'Neutral', value: data.sentiment.neutral, total: data.sentiment.total, color: 'bg-brand-primary' },
                      { label: 'Negative', value: data.sentiment.negative, total: data.sentiment.total, color: 'bg-error' },
                    ].map((item) => {
                      const pct = item.total > 0 ? Math.round((item.value / item.total) * 100) : 0;
                      return (
                        <div key={item.label}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm text-text-secondary">{item.label}</span>
                            <span className="text-sm font-medium text-text-primary">{pct}%</span>
                          </div>
                          <div className="h-2 rounded-full bg-canvas-sunken overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ duration: 0.6, ease: 'easeOut' }}
                              className={cn('h-full rounded-full', item.color)}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-text-tertiary mt-4 text-center">
                    Total responses: {data.sentiment.total.toLocaleString()}
                  </p>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
