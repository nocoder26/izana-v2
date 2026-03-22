'use client';

import { openDB, type IDBPDatabase } from 'idb';

/* ── Constants ────────────────────────────────────────────────── */

const DB_NAME = 'izana-offline';
const DB_VERSION = 1;

const STORE_MESSAGES = 'messages';
const STORE_PLAN = 'plan';
const STORE_QUEUE = 'queue';

/** Maximum offline storage budget in bytes (5 MB) — A6.2 */
const MAX_STORE_BYTES = 5 * 1024 * 1024;

/* ── Types ────────────────────────────────────────────────────── */

export interface OfflineMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  conversationId?: string;
}

export interface OfflinePlan {
  id: string;
  data: Record<string, unknown>;
  cachedAt: string;
}

export interface QueuedAction {
  id: string;
  type: string;
  endpoint: string;
  method: 'POST' | 'PUT' | 'DELETE';
  body?: unknown;
  createdAt: string;
}

/* ── Database ─────────────────────────────────────────────────── */

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (typeof window === 'undefined') {
    return Promise.reject(new Error('IndexedDB is not available on the server'));
  }

  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Messages store — keyed by id, indexed by createdAt
        if (!db.objectStoreNames.contains(STORE_MESSAGES)) {
          const msgStore = db.createObjectStore(STORE_MESSAGES, {
            keyPath: 'id',
          });
          msgStore.createIndex('by-date', 'createdAt');
        }

        // Plan store — single current plan
        if (!db.objectStoreNames.contains(STORE_PLAN)) {
          db.createObjectStore(STORE_PLAN, { keyPath: 'id' });
        }

        // Queue store — offline actions to replay
        if (!db.objectStoreNames.contains(STORE_QUEUE)) {
          const queueStore = db.createObjectStore(STORE_QUEUE, {
            keyPath: 'id',
          });
          queueStore.createIndex('by-date', 'createdAt');
        }
      },
    });
  }

  return dbPromise;
}

/* ── Messages ─────────────────────────────────────────────────── */

/**
 * Cache messages, keeping only today + last 2 days.
 * Evicts oldest messages first when approaching 5 MB limit.
 */
export async function cacheMessages(
  messages: OfflineMessage[],
): Promise<void> {
  const db = await getDB();
  const tx = db.transaction(STORE_MESSAGES, 'readwrite');
  const store = tx.objectStore(STORE_MESSAGES);

  // Determine cutoff: 2 days ago at midnight
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 2);
  cutoff.setHours(0, 0, 0, 0);
  const cutoffISO = cutoff.toISOString();

  // Remove messages older than cutoff
  const index = store.index('by-date');
  let cursor = await index.openCursor();
  while (cursor) {
    if (cursor.value.createdAt < cutoffISO) {
      await cursor.delete();
    }
    cursor = await cursor.continue();
  }

  // Add new messages
  for (const msg of messages) {
    await store.put(msg);
  }

  await tx.done;

  // Enforce size limit
  await enforceStorageLimit();
}

/**
 * Retrieve all cached messages, sorted by date.
 */
export async function getCachedMessages(): Promise<OfflineMessage[]> {
  const db = await getDB();
  const index = db
    .transaction(STORE_MESSAGES, 'readonly')
    .objectStore(STORE_MESSAGES)
    .index('by-date');
  return index.getAll();
}

/* ── Plan ─────────────────────────────────────────────────────── */

/**
 * Cache the current plan.
 */
export async function cachePlan(
  plan: Record<string, unknown>,
): Promise<void> {
  const db = await getDB();
  await db.put(STORE_PLAN, {
    id: 'current',
    data: plan,
    cachedAt: new Date().toISOString(),
  });
}

/**
 * Retrieve the cached plan.
 */
export async function getCachedPlan(): Promise<OfflinePlan | undefined> {
  const db = await getDB();
  return db.get(STORE_PLAN, 'current');
}

/* ── Queue (Offline Actions) ──────────────────────────────────── */

/**
 * Enqueue an action to replay when back online.
 */
export async function queueAction(
  action: Omit<QueuedAction, 'id' | 'createdAt'>,
): Promise<void> {
  const db = await getDB();
  await db.add(STORE_QUEUE, {
    ...action,
    id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
  });
}

/**
 * Get all queued actions, ordered by creation date.
 */
export async function getQueuedActions(): Promise<QueuedAction[]> {
  const db = await getDB();
  const index = db
    .transaction(STORE_QUEUE, 'readonly')
    .objectStore(STORE_QUEUE)
    .index('by-date');
  return index.getAll();
}

/**
 * Clear all queued actions (after successful sync).
 */
export async function clearQueue(): Promise<void> {
  const db = await getDB();
  await db.clear(STORE_QUEUE);
}

/**
 * Remove a single queued action by id.
 */
export async function removeQueuedAction(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE_QUEUE, id);
}

/**
 * Replay all queued actions against the API.
 * Removes each action after successful replay.
 * Returns the count of successfully replayed actions.
 */
export async function syncQueue(): Promise<number> {
  const actions = await getQueuedActions();
  if (actions.length === 0) return 0;

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
  let synced = 0;

  for (const action of actions) {
    try {
      // Dynamically import to avoid circular deps in SSR
      const { supabase } = await import('@/lib/supabase/client');
      const {
        data: { session },
      } = await supabase.auth.getSession();

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const res = await fetch(`${apiUrl}${action.endpoint}`, {
        method: action.method,
        headers,
        body: action.body ? JSON.stringify(action.body) : undefined,
      });

      if (res.ok) {
        await removeQueuedAction(action.id);
        synced++;
      } else if (res.status >= 400 && res.status < 500) {
        // Client error — won't succeed on retry, discard
        await removeQueuedAction(action.id);
      }
      // 5xx errors are left in the queue for next retry
    } catch {
      // Network still down — stop trying
      break;
    }
  }

  return synced;
}

/* ── Storage Enforcement ──────────────────────────────────────── */

/**
 * Evict oldest messages until total size is under the limit.
 */
async function enforceStorageLimit(): Promise<void> {
  const db = await getDB();

  // Estimate total size
  const allMessages = await db.getAll(STORE_MESSAGES);
  let totalSize = estimateSize(allMessages);

  if (totalSize <= MAX_STORE_BYTES) return;

  // Sort by date ascending (oldest first)
  const sorted = [...allMessages].sort((a, b) =>
    a.createdAt.localeCompare(b.createdAt),
  );

  const tx = db.transaction(STORE_MESSAGES, 'readwrite');
  const store = tx.objectStore(STORE_MESSAGES);

  for (const msg of sorted) {
    if (totalSize <= MAX_STORE_BYTES) break;
    totalSize -= estimateSize([msg]);
    await store.delete(msg.id);
  }

  await tx.done;
}

/**
 * Rough byte-size estimate of serialized data.
 */
function estimateSize(data: unknown): number {
  try {
    return new Blob([JSON.stringify(data)]).size;
  } catch {
    return 0;
  }
}
