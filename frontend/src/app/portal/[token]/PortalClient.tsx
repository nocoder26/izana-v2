'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

/* ── Types ────────────────────────────────────────────────────── */

interface TimelineEvent {
  date: string;
  title: string;
  description: string;
  type: 'milestone' | 'medication' | 'procedure' | 'note';
}

interface BloodworkResult {
  date: string;
  markers: Array<{
    name: string;
    value: number;
    unit: string;
    normalRange: string;
    status: 'normal' | 'high' | 'low';
  }>;
}

interface CheckinEntry {
  date: string;
  mood: string;
  symptoms: string[];
  notes: string;
}

interface PlanAdherence {
  period: string;
  completionRate: number;
  totalTasks: number;
  completedTasks: number;
}

interface PortalReport {
  patientPseudonym: string;
  generatedAt: string;
  expiresAt: string;
  treatmentTimeline?: TimelineEvent[];
  bloodworkResults?: BloodworkResult[];
  checkinHistory?: CheckinEntry[];
  planAdherence?: PlanAdherence[];
}

/* ── Helpers ──────────────────────────────────────────────────── */

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/* ── Sub-Components ───────────────────────────────────────────── */

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-serif text-lg text-text-primary mb-3">{children}</h2>
  );
}

function TimelineSection({ events }: { events: TimelineEvent[] }) {
  const typeColors: Record<string, string> = {
    milestone: 'bg-brand-primary',
    medication: 'bg-brand-accent',
    procedure: 'bg-brand-secondary',
    note: 'bg-text-tertiary',
  };

  return (
    <section className="space-y-3">
      <SectionHeading>Treatment Timeline</SectionHeading>
      <div className="relative pl-6 space-y-4">
        {/* Vertical line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-[2px] bg-border-default" />
        {events.map((event, i) => (
          <motion.div
            key={`${event.date}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="relative"
          >
            {/* Dot */}
            <div
              className={cn(
                'absolute -left-6 top-1.5 w-4 h-4 rounded-full border-2 border-canvas-elevated',
                typeColors[event.type] ?? 'bg-text-tertiary',
              )}
            />
            <div
              className={cn(
                'rounded-xl border border-border-default bg-canvas-elevated p-4',
              )}
              style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
            >
              <p className="text-xs text-text-tertiary">{formatDate(event.date)}</p>
              <p className="text-sm font-medium text-text-primary mt-0.5">
                {event.title}
              </p>
              {event.description && (
                <p className="text-sm text-text-secondary mt-1">
                  {event.description}
                </p>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function BloodworkSection({ results }: { results: BloodworkResult[] }) {
  const statusColors: Record<string, string> = {
    normal: 'text-success',
    high: 'text-error',
    low: 'text-warning',
  };

  return (
    <section className="space-y-3">
      <SectionHeading>Bloodwork Results</SectionHeading>
      {results.map((result, ri) => (
        <div
          key={`${result.date}-${ri}`}
          className={cn(
            'rounded-xl border border-border-default bg-canvas-elevated overflow-hidden',
          )}
          style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
        >
          <div className="px-4 py-3 bg-canvas-sunken border-b border-border-default">
            <p className="text-xs font-medium text-text-secondary">
              {formatDate(result.date)}
            </p>
          </div>
          <div className="divide-y divide-border-default">
            {result.markers.map((marker, mi) => (
              <div
                key={`${marker.name}-${mi}`}
                className="px-4 py-3 flex items-center justify-between"
              >
                <div>
                  <p className="text-sm text-text-primary">{marker.name}</p>
                  <p className="text-xs text-text-tertiary">
                    Normal: {marker.normalRange}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={cn(
                      'text-sm font-semibold',
                      statusColors[marker.status] ?? 'text-text-primary',
                    )}
                  >
                    {marker.value} {marker.unit}
                  </p>
                  <p className="text-xs text-text-tertiary capitalize">
                    {marker.status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}

function CheckinSection({ entries }: { entries: CheckinEntry[] }) {
  return (
    <section className="space-y-3">
      <SectionHeading>Check-in History</SectionHeading>
      <div className="space-y-2">
        {entries.map((entry, i) => (
          <div
            key={`${entry.date}-${i}`}
            className={cn(
              'rounded-xl border border-border-default bg-canvas-elevated p-4',
            )}
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs text-text-tertiary">
                {formatDate(entry.date)}
              </p>
              <span className="text-lg">{entry.mood}</span>
            </div>
            {entry.symptoms.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {entry.symptoms.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-canvas-sunken text-text-secondary px-2 py-0.5 rounded-md"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
            {entry.notes && (
              <p className="text-sm text-text-secondary">{entry.notes}</p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function AdherenceSection({ data }: { data: PlanAdherence[] }) {
  return (
    <section className="space-y-3">
      <SectionHeading>Plan Adherence</SectionHeading>
      <div className="space-y-2">
        {data.map((item, i) => (
          <div
            key={`${item.period}-${i}`}
            className={cn(
              'rounded-xl border border-border-default bg-canvas-elevated p-4',
            )}
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-text-primary">
                {item.period}
              </p>
              <p className="text-sm font-semibold text-brand-primary">
                {item.completionRate}%
              </p>
            </div>
            {/* Progress bar */}
            <div className="w-full h-2 rounded-full bg-canvas-sunken overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-brand-primary"
                initial={{ width: 0 }}
                animate={{ width: `${item.completionRate}%` }}
                transition={{ duration: 0.6, delay: i * 0.1 }}
              />
            </div>
            <p className="text-xs text-text-tertiary mt-1.5">
              {item.completedTasks} of {item.totalTasks} tasks completed
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── Main Page ────────────────────────────────────────────────── */

export default function ProviderPortalPage() {
  const params = useParams();
  const token = params.token as string;
  const [report, setReport] = useState<PortalReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function fetchReport() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
        const res = await fetch(`${apiUrl}/api/v1/reports/portal/${token}`);
        if (!res.ok) {
          if (res.status === 404) throw new Error('Report not found or expired');
          if (res.status === 410) throw new Error('This report has expired');
          if (res.status === 429) throw new Error('Maximum views reached');
          throw new Error(`Error ${res.status}`);
        }
        const data: PortalReport = await res.json();
        if (!cancelled) setReport(data);
      } catch (err) {
        if (!cancelled)
          setError(
            err instanceof Error ? err.message : 'Could not load report',
          );
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchReport();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const downloadPDF = useCallback(async () => {
    setIsDownloading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${apiUrl}/api/v1/reports/download/${token}`);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `izana-report-${token.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Could add toast notification here
    } finally {
      setIsDownloading(false);
    }
  }, [token]);

  /* ── Loading ───────────────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="min-h-dvh bg-canvas-base flex items-center justify-center" style={{ minHeight: '100vh' }}>
        <div className="space-y-4 text-center">
          <div className="izana-avatar mx-auto" />
          <p className="text-sm text-text-secondary animate-gentle-pulse">
            Loading report...
          </p>
        </div>
      </div>
    );
  }

  /* ── Error / Expired ───────────────────────────────────────── */

  if (error || !report) {
    return (
      <div className="min-h-dvh bg-canvas-base flex items-center justify-center p-6" style={{ minHeight: '100vh' }}>
        <div className="text-center max-w-sm space-y-4">
          <div className="w-16 h-16 rounded-full bg-canvas-sunken flex items-center justify-center mx-auto">
            <span className="text-2xl">🔒</span>
          </div>
          <h1 className="font-serif text-xl text-text-primary">
            Report unavailable
          </h1>
          <p className="text-sm text-text-secondary">
            {error ?? 'This report could not be found.'}
          </p>
          <p className="text-xs text-text-tertiary">
            If you believe this is an error, please ask the patient to generate
            a new report link.
          </p>
        </div>
      </div>
    );
  }

  /* ── Main Report ───────────────────────────────────────────── */

  return (
    <div className="min-h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        className={cn(
          'bg-canvas-elevated border-b border-border-default',
          'px-5 py-4 sticky top-0 z-10',
        )}
        style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
      >
        <div className="max-w-2xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="font-serif text-lg text-text-primary">
              Patient Report
            </h1>
            <p className="text-xs text-text-tertiary mt-0.5">
              Generated {formatDateTime(report.generatedAt)}
            </p>
          </div>
          <button
            onClick={downloadPDF}
            disabled={isDownloading}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl',
              'border border-border-default bg-canvas-elevated',
              'hover:bg-canvas-sunken transition-colors',
              'text-sm font-medium text-text-primary',
              'disabled:opacity-50',
            )}
          >
            {isDownloading ? (
              <svg
                className="w-4 h-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M8 2v8m0 0l-3-3m3 3l3-3M3 12v1.5h10V12" />
              </svg>
            )}
            Download PDF
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-2xl mx-auto px-5 py-6 space-y-8">
        <AnimatePresence>
          {report.treatmentTimeline &&
            report.treatmentTimeline.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                <TimelineSection events={report.treatmentTimeline} />
              </motion.div>
            )}

          {report.bloodworkResults &&
            report.bloodworkResults.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <BloodworkSection results={report.bloodworkResults} />
              </motion.div>
            )}

          {report.checkinHistory &&
            report.checkinHistory.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <CheckinSection entries={report.checkinHistory} />
              </motion.div>
            )}

          {report.planAdherence &&
            report.planAdherence.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <AdherenceSection data={report.planAdherence} />
              </motion.div>
            )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="border-t border-border-default bg-canvas-sunken px-5 py-6 mt-8">
        <div className="max-w-2xl mx-auto text-center space-y-1">
          <p className="text-xs text-text-tertiary">
            Generated by Izana Chat &middot; Shared by patient &middot; Expires{' '}
            {formatDate(report.expiresAt)}
          </p>
          <p className="text-xs text-text-tertiary">
            This report is for informational purposes. Always confirm findings
            with clinical assessments.
          </p>
        </div>
      </footer>
    </div>
  );
}
