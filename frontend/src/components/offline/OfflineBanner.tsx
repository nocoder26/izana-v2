'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';

/* ── Component ────────────────────────────────────────────────── */

export default function OfflineBanner() {
  const { isOnline, wasOffline, isSyncing } = useOnlineStatus();
  const [dismissed, setDismissed] = useState(false);
  const [showReconnected, setShowReconnected] = useState(false);

  // Reset dismissed state when going offline again
  useEffect(() => {
    if (!isOnline) {
      setDismissed(false);
      setShowReconnected(false);
    }
  }, [isOnline]);

  // Show "All caught up" briefly on reconnect
  useEffect(() => {
    if (isOnline && wasOffline && !isSyncing) {
      setShowReconnected(true);
      const timer = setTimeout(() => {
        setShowReconnected(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isOnline, wasOffline, isSyncing]);

  const shouldShow = !isOnline || isSyncing || showReconnected;

  if (dismissed && !isOnline && !isSyncing && !showReconnected) {
    // Stay dismissed until next offline action attempt or reconnection
    return null;
  }

  return (
    <AnimatePresence>
      {shouldShow && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div
            className={cn(
              'flex items-center justify-between px-4 py-2',
              'text-xs font-medium',
              !isOnline && 'bg-warning/15 text-warning',
              isSyncing && 'bg-brand-primary/10 text-brand-primary',
              showReconnected &&
                !isSyncing &&
                'bg-success/10 text-success',
            )}
          >
            <div className="flex items-center gap-2">
              {/* Status icon */}
              {!isOnline && !isSyncing && (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M1 1l12 12M3.5 3.5A6.5 6.5 0 0113 7M1 7a6.5 6.5 0 012.1-2.1M5.5 5.5A3.5 3.5 0 0110.5 7M7 9v.5" />
                </svg>
              )}
              {isSyncing && (
                <motion.svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 1,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                >
                  <path d="M1 7a6 6 0 0111.5-2.3M13 7A6 6 0 011.5 9.3" />
                  <path d="M12.5 1.5v3.2h-3.2M1.5 12.5V9.3h3.2" />
                </motion.svg>
              )}
              {showReconnected && !isSyncing && (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3.5 7l2.5 2.5L10.5 4" />
                </svg>
              )}

              {/* Status text */}
              <span>
                {!isOnline && !isSyncing &&
                  "You're offline — some features may be limited"}
                {isSyncing && 'Reconnecting...'}
                {showReconnected && !isSyncing && 'All caught up ✓'}
              </span>
            </div>

            {/* Dismiss button (only when offline) */}
            {!isOnline && !isSyncing && (
              <button
                onClick={() => setDismissed(true)}
                className={cn(
                  'p-1 rounded-md hover:bg-warning/20 transition-colors',
                  'text-warning',
                )}
                aria-label="Dismiss offline banner"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M3 3l6 6M9 3l-6 6" />
                </svg>
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
