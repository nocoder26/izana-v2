'use client';

import { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/* ── Types ─────────────────────────────────────────────────── */

type ContentItem = {
  id: string;
  title: string;
  type: 'exercise' | 'meditation';
  phases: string[];
  active: boolean;
};

type ContentManagerData = {
  items: ContentItem[];
};

type SortKey = 'title' | 'type' | 'active';
type SortDir = 'asc' | 'desc';

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function ContentManagerTab({ apiFetch }: Props) {
  const [data, setData] = useState<ContentManagerData | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('title');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  useEffect(() => {
    apiFetch<ContentManagerData>('/admin/content')
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

    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (i) => i.title.toLowerCase().includes(q) || i.type.toLowerCase().includes(q),
      );
    }

    items.sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'title') cmp = a.title.localeCompare(b.title);
      else if (sortKey === 'type') cmp = a.type.localeCompare(b.type);
      else cmp = (a.active ? 1 : 0) - (b.active ? 1 : 0);
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return items;
  }, [data, search, sortKey, sortDir]);

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
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <input
          type="text"
          placeholder="Search content..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-9 px-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 w-72"
        />
        <Button variant="primary" size="sm" onClick={() => { /* placeholder */ }}>
          Upload Content
        </Button>
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
                <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-24">
                  ID
                </th>
                <th
                  onClick={() => handleSort('title')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide cursor-pointer select-none hover:text-text-secondary"
                >
                  Title <SortIcon column="title" />
                </th>
                <th
                  onClick={() => handleSort('type')}
                  className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-28 cursor-pointer select-none hover:text-text-secondary"
                >
                  Type <SortIcon column="type" />
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-40">
                  Phases
                </th>
                <th
                  onClick={() => handleSort('active')}
                  className="text-center px-4 py-3 text-xs font-medium text-text-tertiary uppercase tracking-wide w-20 cursor-pointer select-none hover:text-text-secondary"
                >
                  Active <SortIcon column="active" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-sm text-text-tertiary">
                    No content items found.
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
                      <span className="text-xs font-mono text-text-tertiary">{item.id.slice(0, 8)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-text-primary">{item.title}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full capitalize bg-canvas-sunken text-text-secondary">
                        {item.type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {item.phases.map((phase) => (
                          <span
                            key={phase}
                            className="text-[10px] px-1.5 py-0.5 rounded-full bg-brand-primary-bg text-brand-primary capitalize"
                          >
                            {phase}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          'w-2.5 h-2.5 rounded-full inline-block',
                          item.active ? 'bg-success' : 'bg-text-tertiary',
                        )}
                      />
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
