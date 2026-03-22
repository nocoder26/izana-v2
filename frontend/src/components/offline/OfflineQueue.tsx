'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { getQueuedActions } from '@/lib/offline-store';
import { useOnlineStatus } from '@/hooks/useOnlineStatus';

/* ── Component ────────────────────────────────────────────────── */

export default function OfflineQueue() {
  const { isOnline, isSyncing } = useOnlineStatus();
  const [queueCount, setQueueCount] = useState(0);

  // Poll queue count periodically when offline
  useEffect(() => {
    let cancelled = false;

    async function checkQueue() {
      try {
        const actions = await getQueuedActions();
        if (!cancelled) setQueueCount(actions.length);
      } catch {
        // IndexedDB unavailable
      }
    }

    checkQueue();

    // Re-check when online status changes
    const interval = setInterval(checkQueue, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [isOnline]);

  if (queueCount === 0 && !isSyncing) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full',
          'text-xs font-medium',
          'border',
          isSyncing
            ? 'bg-brand-primary/10 text-brand-primary border-brand-primary/20'
            : 'bg-warning/10 text-warning border-warning/20',
        )}
      >
        {/* Sync icon */}
        {isSyncing ? (
          <motion.svg
            width="12"
            height="12"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <path d="M1 7a6 6 0 0111.5-2.3M13 7A6 6 0 011.5 9.3" />
            <path d="M12.5 1.5v3.2h-3.2M1.5 12.5V9.3h3.2" />
          </motion.svg>
        ) : (
          <svg
            width="12"
            height="12"
            viewBox="0 0 14 14"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          >
            <circle cx="7" cy="7" r="6" />
            <path d="M7 4v3l2 1.5" />
          </svg>
        )}

        <span>
          {isSyncing
            ? 'Syncing...'
            : `${queueCount} queued action${queueCount !== 1 ? 's' : ''}`}
        </span>
      </motion.div>
    </AnimatePresence>
  );
}
