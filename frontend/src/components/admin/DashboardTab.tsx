'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

/* ── Types ─────────────────────────────────────────────────── */

type DashboardData = {
  kpis: {
    totalUsers: number;
    activeToday: number;
    aiAccuracy: number;
    plansQueue: number;
  };
  userGrowth: Array<{ date: string; users: number }>;
  checkInRate: Array<{ date: string; rate: number }>;
};

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function DashboardTab({ apiFetch }: Props) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<DashboardData>('/admin/dashboard')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const kpis = data?.kpis ?? { totalUsers: 0, activeToday: 0, aiAccuracy: 0, plansQueue: 0 };

  const kpiCards = [
    { label: 'Total Users', value: kpis.totalUsers.toLocaleString(), color: 'text-brand-primary' },
    { label: 'Active Today', value: kpis.activeToday.toLocaleString(), color: 'text-success' },
    { label: 'AI Accuracy', value: `${kpis.aiAccuracy}%`, color: 'text-brand-accent' },
    { label: 'Plans Queue', value: kpis.plansQueue.toLocaleString(), color: 'text-warning' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {kpiCards.map((kpi) => (
          <Card key={kpi.label}>
            <CardContent className="py-5">
              <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">
                {kpi.label}
              </p>
              <p className={cn('text-3xl font-semibold mt-1', kpi.color)}>
                {loading ? (
                  <span className="inline-block skeleton w-16 h-8 rounded-lg" />
                ) : (
                  kpi.value
                )}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* User Growth */}
        <Card>
          <CardContent className="py-5">
            <h3 className="text-sm font-semibold text-text-primary mb-4">User Growth</h3>
            <div className="h-64">
              {loading || !data?.userGrowth ? (
                <div className="skeleton w-full h-full rounded-xl" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.userGrowth}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                      stroke="var(--border-default)"
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                      stroke="var(--border-default)"
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--canvas-elevated)',
                        border: '0.5px solid var(--border-default)',
                        borderRadius: '10px',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="users"
                      stroke="var(--brand-primary)"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: 'var(--brand-primary)' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Check-in Rate */}
        <Card>
          <CardContent className="py-5">
            <h3 className="text-sm font-semibold text-text-primary mb-4">Check-in Rate</h3>
            <div className="h-64">
              {loading || !data?.checkInRate ? (
                <div className="skeleton w-full h-full rounded-xl" />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.checkInRate}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                      stroke="var(--border-default)"
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
                      stroke="var(--border-default)"
                      domain={[0, 100]}
                      unit="%"
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--canvas-elevated)',
                        border: '0.5px solid var(--border-default)',
                        borderRadius: '10px',
                        fontSize: '12px',
                        color: 'var(--text-primary)',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="rate"
                      stroke="var(--brand-accent)"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: 'var(--brand-accent)' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
