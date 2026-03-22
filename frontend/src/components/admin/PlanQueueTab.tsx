'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ─────────────────────────────────────────────────── */

type PlanQueueItem = {
  id: string;
  pseudonym: string;
  treatmentType: string;
  status: 'pending' | 'in_review' | 'approved' | 'rejected';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  deadline: string;
  assignedTo?: string;
  createdAt: string;
};

type PlanQueueData = {
  items: PlanQueueItem[];
  stats: {
    total: number;
    pending: number;
    inReview: number;
    avgTurnaround: number; // hours
  };
};

type SortKey = 'pseudonym' | 'status' | 'priority' | 'deadline' | 'assignedTo';
type SortDir = 'asc' | 'desc';

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Helpers ───────────────────────────────────────────────── */

function priorityRank(p: string): number {
  return { urgent: 0, high: 1, medium: 2, low: 3 }[p] ?? 4;
}

function statusDot(status: string): string {
  switch (status) {
    case 'pending': return 'bg-warning';
    case 'in_review': return 'bg-brand-primary';
    case 'approved': return 'bg-success';
    case 'rejected': return 'bg-error';
    default: return 'bg-text-tertiary';
  }
}

function priorityBadge(priority: string): string {
  switch (priority) {
    case 'urgent': return 'bg-error/15 text-error';
    case 'high': return 'bg-warning/15 text-warning';
    case 'medium': return 'bg-brand-primary/10 text-brand-primary';
    case 'low': return 'bg-canvas-sunken text-text-tertiary';
    default: return 'bg-canvas-sunken text-text-tertiary';
  }
}

function deadlineColor(deadline: string): string {
  const diff = new Date(deadline).getTime() - Date.now();
  const hours = diff / (1000 * 60 * 60);
  if (hours < 0) return 'text-error font-medium';
  if (hours < 12) return 'text-warning font-medium';
  return 'text-text-secondary';
}

/* ── Component ─────────────────────────────────────────────── */

export default function PlanQueueTab({ apiFetch }: Props) {
  const [data, setData] = useState<PlanQueueData | null>(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [search, setSearch] = useState('');

  // Sort
  const [sortKey, setSortKey] = useState<SortKey>('deadline');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  useEffect(() => {
    apiFetch<PlanQueueData>('/admin/plans/queue')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  const handleSort = (key: SortKey) => {
    setSortDir((prev) => (sortKey === key ? (prev === 'asc' ? 'desc' : 'asc') : 'asc'));
    setSortKey(key);
  };

  const filteredItems = useMemo(() => {
    if (!data) return [];
    let items = [...data.items];

    if (statusFilter !== 'all') items = items.filter((i) => i.status === statusFilter);
    if (priorityFilter !== 'all') items = items.filter((i) => i.priority === priorityFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (i) =>
          i.pseudonym.toLowerCase().includes(q) ||
          i.treatmentType.toLowerCase().includes(q) ||
          (i.assignedTo && i.assignedTo.toLowerCase().includes(q)),
      );
    }

    items.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'pseudonym':
          cmp = a.pseudonym.localeCompare(b.pseudonym);
          break;
        case 'status':
          cmp = a.status.localeCompare(b.status);
          break;
        case 'priority':
          cmp = priorityRank(a.priority) - priorityRank(b.priority);
          break;
        case 'deadline':
          cmp = new Date(a.deadline).getTime() - new Date(b.deadline).getTime();
          break;
        case 'assignedTo':
          cmp = (a.assignedTo ?? '').localeCompare(b.assignedTo ?? '');
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return items;
  }, [data, statusFilter, priorityFilter, search, sortKey, sortDir]);

  const stats = data?.stats ?? { total: 0, pending: 0, inReview: 0, avgTurnaround: 0 };

  const SortIcon = ({ column }: { column: SortKey }) => (
    <span className="inline-block ml-1 text-[10px]">
      {sortKey === column ? (sortDir === 'asc' ? '\u25B2' : '\u25BC') : '\u25B4'}
    </span>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Plans', value: stats.total, color: 'text-text-primary' },
          { label: 'Pending', value: stats.pending, color: 'text-warning' },
          { label: 'In Review', value: stats.inReview, color: 'text-brand-primary' },
          { label: 'Avg Turnaround', value: `${stats.avgTurnaround}h`, color: 'text-brand-accent' },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardContent className="py-4">
              <p className="text-xs text-text-tertiary font-medium uppercase tracking-wide">
                {stat.label}
              </p>
              <p className={cn('text-2xl font-semibold mt-1', stat.color)}>
                {loading ? '-' : stat.value}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="h-9 px-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          <option value="all">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_review">In Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="h-9 px-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
        >
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <div className="flex-1 max-w-xs">
          <input
            type="text"
            placeholder="Search by name, treatment, assigned..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 px-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20"
          />
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="skeleton h-14 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated overflow-hidden shadow-[0_1px_3px_rgba(42,36,51,0.04)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border-default bg-canvas-sunken/50">
                <th
                  onClick={() => handleSort('pseudonym')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  User <SortIcon column="pseudonym" />
                </th>
                <th
                  onClick={() => handleSort('status')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  Status <SortIcon column="status" />
                </th>
                <th
                  onClick={() => handleSort('priority')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  Priority <SortIcon column="priority" />
                </th>
                <th
                  onClick={() => handleSort('deadline')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  Deadline <SortIcon column="deadline" />
                </th>
                <th
                  onClick={() => handleSort('assignedTo')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  Assigned To <SortIcon column="assignedTo" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-sm text-text-tertiary">
                    No items match your filters.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, idx) => (
                  <motion.tr
                    key={item.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.02 }}
                    className="border-b border-border-default last:border-b-0 hover:bg-canvas-sunken/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-text-primary">{item.pseudonym}</p>
                      <p className="text-xs text-text-tertiary">{item.treatmentType}</p>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={cn('w-2 h-2 rounded-full', statusDot(item.status))} />
                        <span className="text-sm text-text-secondary capitalize">
                          {item.status.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full capitalize', priorityBadge(item.priority))}>
                        {item.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('text-sm', deadlineColor(item.deadline))}>
                        {new Date(item.deadline).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-text-secondary">
                        {item.assignedTo || <span className="text-text-tertiary italic">Unassigned</span>}
                      </span>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
