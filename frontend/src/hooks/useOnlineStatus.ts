'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { syncQueue } from '@/lib/offline-store';

/* ── Types ────────────────────────────────────────────────────── */

export interface OnlineStatus {
  /** Whether the browser currently reports being online */
  isOnline: boolean;
  /** Whether we were offline during this session (useful for showing "reconnected" states) */
  wasOffline: boolean;
  /** Whether a sync is currently in progress */
  isSyncing: boolean;
  /** Number of actions synced on last reconnection */
  lastSyncCount: number;
}

/* ── Hook ─────────────────────────────────────────────────────── */

export function useOnlineStatus(): OnlineStatus {
  const [isOnline, setIsOnline] = useState(() =>
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );
  const [wasOffline, setWasOffline] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncCount, setLastSyncCount] = useState(0);
  const wasOfflineRef = useRef(false);

  const handleSync = useCallback(async () => {
    setIsSyncing(true);
    try {
      const count = await syncQueue();
      setLastSyncCount(count);
    } catch {
      // Sync failed silently — will retry next time
    } finally {
      setIsSyncing(false);
    }
  }, []);

  useEffect(() => {
    function handleOnline() {
      setIsOnline(true);
      if (wasOfflineRef.current) {
        setWasOffline(true);
        // Trigger sync from offline store on reconnect
        handleSync();
      }
    }

    function handleOffline() {
      setIsOnline(false);
      wasOfflineRef.current = true;
    }

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Check initial state
    if (!navigator.onLine) {
      wasOfflineRef.current = true;
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [handleSync]);

  return {
    isOnline,
    wasOffline,
    isSyncing,
    lastSyncCount,
  };
}

export default useOnlineStatus;
