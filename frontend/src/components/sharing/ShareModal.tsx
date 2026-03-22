'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';
import { cn } from '@/lib/utils';
import { apiPost } from '@/lib/api-client';
import { Button } from '@/components/ui/button';

/* ── Types ────────────────────────────────────────────────────── */

interface ShareableItem {
  key: string;
  label: string;
  defaultChecked: boolean;
}

interface GeneratedReport {
  url: string;
  expiresAt: string;
  maxViews: number;
}

const SHAREABLE_ITEMS: ShareableItem[] = [
  { key: 'treatmentTimeline', label: 'Treatment timeline', defaultChecked: true },
  { key: 'bloodworkResults', label: 'Bloodwork results', defaultChecked: true },
  { key: 'checkinHistory', label: 'Check-in history', defaultChecked: true },
  { key: 'planAdherence', label: 'Plan adherence', defaultChecked: false },
  { key: 'wellnessProfile', label: 'Wellness profile', defaultChecked: false },
];

const VALIDITY_OPTIONS = [
  { value: 1, label: '1 day' },
  { value: 7, label: '7 days' },
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
];

const MAX_VIEWS_OPTIONS = [1, 5, 10, 50, 100];

/* ── Component ────────────────────────────────────────────────── */

export default function ShareModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [selectedItems, setSelectedItems] = useState<Record<string, boolean>>(
    () =>
      SHAREABLE_ITEMS.reduce(
        (acc, item) => ({ ...acc, [item.key]: item.defaultChecked }),
        {} as Record<string, boolean>,
      ),
  );
  const [validDays, setValidDays] = useState(7);
  const [maxViews, setMaxViews] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [report, setReport] = useState<GeneratedReport | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleItem = useCallback((key: string) => {
    setSelectedItems((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const hasSelectedItems = Object.values(selectedItems).some(Boolean);

  const generateReport = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const included = Object.entries(selectedItems)
        .filter(([, v]) => v)
        .map(([k]) => k);

      const data = await apiPost<GeneratedReport>('/api/v1/reports/share', {
        included,
        validDays,
        maxViews,
      });
      setReport(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not generate report',
      );
    } finally {
      setIsGenerating(false);
    }
  }, [selectedItems, validDays, maxViews]);

  const copyUrl = useCallback(async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(report.url);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = report.url;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [report]);

  const shareViaWhatsApp = useCallback(() => {
    if (!report) return;
    const text = encodeURIComponent(
      `Here is my health report from Izana Chat: ${report.url}`,
    );
    window.open(`https://wa.me/?text=${text}`, '_blank');
  }, [report]);

  const handleClose = useCallback(
    (value: boolean) => {
      if (!value) {
        // Reset state on close
        setReport(null);
        setCopied(false);
        setError(null);
      }
      onOpenChange(value);
    },
    [onOpenChange],
  );

  return (
    <Dialog.Root open={open} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-50 bg-black/40',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0',
          )}
        />
        <Dialog.Content
          className={cn(
            'fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            'w-full max-w-md max-h-[85vh] overflow-y-auto',
            'rounded-2xl border border-border-default bg-canvas-elevated',
            'shadow-[0_8px_32px_rgba(42,36,51,0.12)]',
            'p-6 focus:outline-none',
          )}
        >
          <Dialog.Title className="font-serif text-lg text-text-primary">
            Share with your doctor
          </Dialog.Title>
          <Dialog.Description className="text-sm text-text-secondary mt-1 mb-5">
            Select what to include in your report.
          </Dialog.Description>

          <AnimatePresence mode="wait">
            {!report ? (
              <motion.div
                key="form"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0, x: -16 }}
                className="space-y-5"
              >
                {/* Checkboxes */}
                <div className="space-y-1">
                  {SHAREABLE_ITEMS.map((item) => (
                    <label
                      key={item.key}
                      className={cn(
                        'flex items-center gap-3 py-2.5 cursor-pointer',
                        'hover:bg-canvas-sunken -mx-2 px-2 rounded-lg transition-colors',
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedItems[item.key] ?? false}
                        onChange={() => toggleItem(item.key)}
                        className={cn(
                          'w-5 h-5 rounded-md border-2 border-border-default',
                          'text-brand-primary focus:ring-brand-primary/20',
                          'accent-[var(--brand-primary)]',
                        )}
                      />
                      <span className="text-sm text-text-primary">
                        {item.label}
                      </span>
                    </label>
                  ))}
                </div>

                {/* Valid For */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Valid for
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {VALIDITY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => setValidDays(opt.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                          'border',
                          validDays === opt.value
                            ? 'bg-brand-primary text-white border-brand-primary'
                            : 'bg-canvas-elevated text-text-secondary border-border-default hover:bg-canvas-sunken',
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Max Views */}
                <div>
                  <p className="text-xs font-medium text-text-secondary mb-2">
                    Max views
                  </p>
                  <div className="flex gap-2 flex-wrap">
                    {MAX_VIEWS_OPTIONS.map((count) => (
                      <button
                        key={count}
                        onClick={() => setMaxViews(count)}
                        className={cn(
                          'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                          'border',
                          maxViews === count
                            ? 'bg-brand-primary text-white border-brand-primary'
                            : 'bg-canvas-elevated text-text-secondary border-border-default hover:bg-canvas-sunken',
                        )}
                      >
                        {count}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <p className="text-sm text-error" role="alert">
                    {error}
                  </p>
                )}

                {/* Generate */}
                <Button
                  variant="primary"
                  size="lg"
                  className="w-full"
                  disabled={!hasSelectedItems}
                  isLoading={isGenerating}
                  onClick={generateReport}
                >
                  Generate report
                </Button>
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                className="space-y-4"
              >
                {/* Success */}
                <div className="text-center space-y-2 py-2">
                  <div className="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center mx-auto">
                    <span className="text-xl">✅</span>
                  </div>
                  <p className="text-sm font-medium text-text-primary">
                    Report generated
                  </p>
                  <p className="text-xs text-text-tertiary">
                    Valid for {validDays} day{validDays !== 1 ? 's' : ''} &middot;{' '}
                    {maxViews} view{maxViews !== 1 ? 's' : ''}
                  </p>
                </div>

                {/* URL Display */}
                <div
                  className={cn(
                    'rounded-xl border border-border-default bg-canvas-sunken',
                    'px-3 py-2.5',
                  )}
                >
                  <p className="text-xs text-text-tertiary truncate font-mono">
                    {report.url}
                  </p>
                </div>

                {/* Share Buttons */}
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={copyUrl}
                    className={cn(
                      'flex items-center justify-center gap-2 py-2.5 rounded-xl',
                      'border border-border-default bg-canvas-elevated',
                      'hover:bg-canvas-sunken transition-colors',
                      'text-sm font-medium',
                      copied ? 'text-success' : 'text-text-primary',
                    )}
                  >
                    {copied ? '✅ Copied!' : '📋 Copy link'}
                  </button>
                  <button
                    onClick={shareViaWhatsApp}
                    className={cn(
                      'flex items-center justify-center gap-2 py-2.5 rounded-xl',
                      'border border-border-default bg-canvas-elevated',
                      'hover:bg-canvas-sunken transition-colors',
                      'text-sm font-medium text-text-primary',
                    )}
                  >
                    💬 WhatsApp
                  </button>
                </div>

                {/* Close */}
                <Button
                  variant="secondary"
                  size="md"
                  className="w-full"
                  onClick={() => handleClose(false)}
                >
                  Done
                </Button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Close X */}
          <Dialog.Close asChild>
            <button
              className={cn(
                'absolute top-4 right-4 w-8 h-8 rounded-lg',
                'flex items-center justify-center',
                'text-text-tertiary hover:text-text-primary',
                'hover:bg-canvas-sunken transition-colors',
              )}
              aria-label="Close"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <path d="M4 4l8 8M12 4l-8 8" />
              </svg>
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
