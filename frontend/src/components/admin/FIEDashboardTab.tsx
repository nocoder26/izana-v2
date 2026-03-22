'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiGet } from '@/lib/api-client';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ────────────────────────────────────────────────────── */

interface DataOverview {
  totalFeatureRecords: number;
  completedCycles: number;
  qualityDistribution: {
    high: number;
    medium: number;
    low: number;
  };
}

interface Insight {
  id: string;
  title: string;
  description: string;
  significance: number;
  type: 'correlation' | 'trend' | 'anomaly' | 'recommendation';
  createdAt: string;
}

interface TrainingData {
  totalCount: number;
  qualityDistribution: {
    high: number;
    medium: number;
    low: number;
  };
}

interface TrainedModel {
  id: string;
  name: string;
  version: string;
  accuracy: number;
  f1Score: number;
  trainedAt: string;
  status: 'active' | 'training' | 'archived';
}

interface FIEData {
  overview: DataOverview;
  insights: Insight[];
  trainingData: TrainingData;
  models: TrainedModel[];
}

type InsightFilter = 'all' | Insight['type'];

/* ── Helpers ──────────────────────────────────────────────────── */

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/* ── Sub-Components ───────────────────────────────────────────── */

function StatCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: string | number;
  subtitle?: string;
}) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border-default bg-canvas-elevated p-4',
      )}
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      <p className="text-xs text-text-tertiary mb-1">{label}</p>
      <p className="text-xl font-semibold text-text-primary">{value}</p>
      {subtitle && (
        <p className="text-xs text-text-secondary mt-0.5">{subtitle}</p>
      )}
    </div>
  );
}

function QualityBar({
  high,
  medium,
  low,
}: {
  high: number;
  medium: number;
  low: number;
}) {
  const total = high + medium + low;
  if (total === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex h-3 rounded-full overflow-hidden bg-canvas-sunken">
        <motion.div
          className="bg-success"
          initial={{ width: 0 }}
          animate={{ width: `${(high / total) * 100}%` }}
          transition={{ duration: 0.5 }}
        />
        <motion.div
          className="bg-warning"
          initial={{ width: 0 }}
          animate={{ width: `${(medium / total) * 100}%` }}
          transition={{ duration: 0.5, delay: 0.1 }}
        />
        <motion.div
          className="bg-error"
          initial={{ width: 0 }}
          animate={{ width: `${(low / total) * 100}%` }}
          transition={{ duration: 0.5, delay: 0.2 }}
        />
      </div>
      <div className="flex gap-4 text-xs text-text-tertiary">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-success inline-block" />
          High {high}
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-warning inline-block" />
          Med {medium}
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-error inline-block" />
          Low {low}
        </span>
      </div>
    </div>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const typeLabels: Record<Insight['type'], string> = {
    correlation: 'Correlation',
    trend: 'Trend',
    anomaly: 'Anomaly',
    recommendation: 'Recommendation',
  };

  const typeColors: Record<Insight['type'], string> = {
    correlation: 'bg-brand-primary/10 text-brand-primary',
    trend: 'bg-brand-accent/10 text-brand-accent',
    anomaly: 'bg-error/10 text-error',
    recommendation: 'bg-success/10 text-success',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'rounded-xl border border-border-default bg-canvas-elevated p-4',
      )}
      style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'text-xs font-medium px-2 py-0.5 rounded-md',
              typeColors[insight.type],
            )}
          >
            {typeLabels[insight.type]}
          </span>
          <span className="text-xs text-text-tertiary">
            {formatDate(insight.createdAt)}
          </span>
        </div>
        {/* Significance score */}
        <div
          className={cn(
            'text-xs font-semibold px-2 py-0.5 rounded-md shrink-0',
            insight.significance >= 0.8
              ? 'bg-success/10 text-success'
              : insight.significance >= 0.5
                ? 'bg-warning/10 text-warning'
                : 'bg-canvas-sunken text-text-tertiary',
          )}
        >
          {(insight.significance * 100).toFixed(0)}%
        </div>
      </div>
      <p className="text-sm font-medium text-text-primary">{insight.title}</p>
      <p className="text-sm text-text-secondary mt-1 leading-relaxed">
        {insight.description}
      </p>
    </motion.div>
  );
}

function ModelRow({ model }: { model: TrainedModel }) {
  const statusStyles: Record<TrainedModel['status'], string> = {
    active: 'bg-success/10 text-success',
    training: 'bg-warning/10 text-warning',
    archived: 'bg-canvas-sunken text-text-tertiary',
  };

  return (
    <div
      className={cn(
        'flex items-center gap-4 py-3',
        'border-b border-border-default last:border-0',
      )}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary truncate">
          {model.name}
        </p>
        <p className="text-xs text-text-tertiary">v{model.version}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="text-xs text-text-secondary">
          Acc: {(model.accuracy * 100).toFixed(1)}%
        </p>
        <p className="text-xs text-text-tertiary">
          F1: {(model.f1Score * 100).toFixed(1)}%
        </p>
      </div>
      <span
        className={cn(
          'text-xs font-medium px-2 py-0.5 rounded-md capitalize shrink-0',
          statusStyles[model.status],
        )}
      >
        {model.status}
      </span>
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────────── */

export default function FIEDashboardTab() {
  const [data, setData] = useState<FIEData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEnabled, setIsEnabled] = useState(false);
  const [insightFilter, setInsightFilter] = useState<InsightFilter>('all');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function checkFeatureAndLoad() {
      try {
        // Check if FIE feature is enabled
        const featureRes = await apiGet<{ enabled: boolean }>(
          '/admin/features/fie',
        );
        if (!cancelled) setIsEnabled(featureRes.enabled);
        if (!featureRes.enabled) {
          setIsLoading(false);
          return;
        }

        // Load FIE dashboard data
        const fieData = await apiGet<FIEData>('/admin/fie/dashboard');
        if (!cancelled) setData(fieData);
      } catch (err) {
        if (!cancelled)
          setError(
            err instanceof Error
              ? err.message
              : 'Could not load FIE dashboard',
          );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    checkFeatureAndLoad();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleExport = useCallback(() => {
    // Placeholder — in production, trigger download via API
    window.alert('Export functionality coming soon');
  }, []);

  const filteredInsights =
    data?.insights.filter(
      (i) => insightFilter === 'all' || i.type === insightFilter,
    ) ?? [];

  const FILTER_OPTIONS: { value: InsightFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'correlation', label: 'Correlations' },
    { value: 'trend', label: 'Trends' },
    { value: 'anomaly', label: 'Anomalies' },
    { value: 'recommendation', label: 'Recommendations' },
  ];

  /* ── Loading ───────────────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="space-y-4 p-5">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-24 skeleton rounded-xl" />
        ))}
      </div>
    );
  }

  /* ── Feature Disabled ──────────────────────────────────────── */

  if (!isEnabled) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
        <div className="w-14 h-14 rounded-full bg-canvas-sunken flex items-center justify-center mb-4">
          <span className="text-2xl">🧪</span>
        </div>
        <h3 className="font-serif text-lg text-text-primary mb-2">
          FIE Pipeline
        </h3>
        <p className="text-sm text-text-secondary max-w-xs">
          The Feature-Insight-Extraction pipeline is not enabled for this
          environment. Enable FEATURE_FIE_ENABLED to access this dashboard.
        </p>
      </div>
    );
  }

  /* ── Error ─────────────────────────────────────────────────── */

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
        <p className="text-sm text-error mb-4">
          {error ?? 'Could not load FIE data'}
        </p>
        <Button variant="secondary" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </div>
    );
  }

  /* ── Dashboard ─────────────────────────────────────────────── */

  return (
    <div className="space-y-6 p-5">
      {/* Data Overview */}
      <section>
        <h3 className="font-serif text-base text-text-primary mb-3">
          Data Overview
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard
            label="Total feature records"
            value={formatNumber(data.overview.totalFeatureRecords)}
          />
          <StatCard
            label="Completed cycles"
            value={formatNumber(data.overview.completedCycles)}
          />
          <StatCard
            label="Quality"
            value={`${((data.overview.qualityDistribution.high / (data.overview.totalFeatureRecords || 1)) * 100).toFixed(0)}% high`}
          />
        </div>
        <div className="mt-3">
          <QualityBar
            high={data.overview.qualityDistribution.high}
            medium={data.overview.qualityDistribution.medium}
            low={data.overview.qualityDistribution.low}
          />
        </div>
      </section>

      {/* Insight Feed */}
      <section>
        <h3 className="font-serif text-base text-text-primary mb-3">
          Insight Feed
        </h3>
        {/* Filters */}
        <div className="flex gap-2 mb-3 flex-wrap">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setInsightFilter(opt.value)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border',
                insightFilter === opt.value
                  ? 'bg-brand-primary text-white border-brand-primary'
                  : 'bg-canvas-elevated text-text-secondary border-border-default hover:bg-canvas-sunken',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <AnimatePresence mode="popLayout">
          <div className="space-y-2">
            {filteredInsights.length > 0 ? (
              filteredInsights.map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))
            ) : (
              <p className="text-sm text-text-tertiary text-center py-6">
                No insights match this filter.
              </p>
            )}
          </div>
        </AnimatePresence>
      </section>

      {/* Training Data */}
      <section>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <h3 className="font-serif text-base text-text-primary">
                Training Data
              </h3>
              <Button variant="secondary" size="sm" onClick={handleExport}>
                Export
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <StatCard
              label="Total records"
              value={formatNumber(data.trainingData.totalCount)}
            />
            <div className="mt-3">
              <QualityBar
                high={data.trainingData.qualityDistribution.high}
                medium={data.trainingData.qualityDistribution.medium}
                low={data.trainingData.qualityDistribution.low}
              />
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Model Registry */}
      <section>
        <Card>
          <CardHeader>
            <h3 className="font-serif text-base text-text-primary">
              Model Registry
            </h3>
          </CardHeader>
          <CardContent>
            {data.models.length > 0 ? (
              data.models.map((model) => (
                <ModelRow key={model.id} model={model} />
              ))
            ) : (
              <p className="text-sm text-text-tertiary text-center py-4">
                No trained models yet.
              </p>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
