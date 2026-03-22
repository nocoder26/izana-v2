'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';

/* ── Types ─────────────────────────────────────────────────── */

type SwarmHealth = {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  queriesPerHour: number;
  avgLatency: number; // ms
  p95Latency: number; // ms
  errorRate: number; // percentage
};

type HealthData = {
  systemStatus: 'healthy' | 'degraded' | 'down';
  swarms: SwarmHealth[];
};

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Helpers ───────────────────────────────────────────────── */

function statusConfig(status: string) {
  switch (status) {
    case 'healthy':
      return { dot: 'bg-success', bg: 'bg-success/10', text: 'text-success', label: 'Healthy' };
    case 'degraded':
      return { dot: 'bg-warning', bg: 'bg-warning/10', text: 'text-warning', label: 'Degraded' };
    case 'down':
      return { dot: 'bg-error', bg: 'bg-error/10', text: 'text-error', label: 'Down' };
    default:
      return { dot: 'bg-text-tertiary', bg: 'bg-canvas-sunken', text: 'text-text-tertiary', label: 'Unknown' };
  }
}

/* ── Component ─────────────────────────────────────────────── */

export default function HealthTab({ apiFetch }: Props) {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<HealthData>('/admin/health')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const systemStatus = data?.systemStatus ?? 'healthy';
  const sys = statusConfig(systemStatus);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* System status banner */}
      <div
        className={cn(
          'rounded-[14px] border-[0.5px] border-border-default p-4 mb-6 flex items-center gap-3',
          sys.bg,
        )}
      >
        <span className={cn('w-3 h-3 rounded-full', sys.dot)} />
        <div>
          <p className={cn('text-sm font-semibold', sys.text)}>System {sys.label}</p>
          <p className="text-xs text-text-secondary mt-0.5">
            {data ? `${data.swarms.length} swarms monitored` : 'Loading...'}
          </p>
        </div>
      </div>

      {/* Swarm cards grid */}
      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="skeleton h-36 rounded-[14px]" />
          ))}
        </div>
      ) : !data || data.swarms.length === 0 ? (
        <p className="text-center text-sm text-text-tertiary py-16">No swarm data available.</p>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {data.swarms.map((swarm, idx) => {
            const cfg = statusConfig(swarm.status);
            return (
              <motion.div
                key={swarm.name}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.03 }}
              >
                <Card>
                  <CardContent className="py-4">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-medium text-text-primary truncate pr-2">
                        {swarm.name}
                      </h4>
                      <div className="flex items-center gap-1.5">
                        <span className={cn('w-2 h-2 rounded-full', cfg.dot)} />
                        <span className={cn('text-xs font-medium', cfg.text)}>
                          {cfg.label}
                        </span>
                      </div>
                    </div>

                    {/* Metrics */}
                    <div className="grid grid-cols-2 gap-2">
                      <MetricItem label="Queries/hr" value={swarm.queriesPerHour.toLocaleString()} />
                      <MetricItem label="Avg Latency" value={`${swarm.avgLatency}ms`} />
                      <MetricItem label="P95 Latency" value={`${swarm.p95Latency}ms`} />
                      <MetricItem
                        label="Error Rate"
                        value={`${swarm.errorRate}%`}
                        valueClass={swarm.errorRate > 5 ? 'text-error' : swarm.errorRate > 1 ? 'text-warning' : 'text-success'}
                      />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}

function MetricItem({
  label,
  value,
  valueClass,
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="bg-canvas-sunken rounded-lg px-2.5 py-2">
      <p className="text-[10px] text-text-tertiary uppercase tracking-wide">{label}</p>
      <p className={cn('text-sm font-medium text-text-primary mt-0.5', valueClass)}>{value}</p>
    </div>
  );
}
