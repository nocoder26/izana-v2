'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ─────────────────────────────────────────────────── */

type SwarmOption = {
  id: string;
  name: string;
};

type PromptVersion = {
  version: number;
  updatedAt: string;
  updatedBy: string;
};

type PromptData = {
  swarmId: string;
  currentPrompt: string;
  versions: PromptVersion[];
};

type Props = {
  apiFetch: <T>(endpoint: string, options?: RequestInit) => Promise<T>;
};

/* ── Component ─────────────────────────────────────────────── */

export default function PromptsTab({ apiFetch }: Props) {
  const [swarms, setSwarms] = useState<SwarmOption[]>([]);
  const [selectedSwarm, setSelectedSwarm] = useState('');
  const [promptText, setPromptText] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [versions, setVersions] = useState<PromptVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Load swarm list
  useEffect(() => {
    apiFetch<{ swarms: SwarmOption[] }>('/admin/swarms')
      .then((res) => {
        setSwarms(res.swarms);
        if (res.swarms.length > 0) {
          setSelectedSwarm(res.swarms[0].id);
        }
      })
      .catch(() => setSwarms([]))
      .finally(() => setLoading(false));
  }, [apiFetch]);

  // Load prompt when swarm changes
  useEffect(() => {
    if (!selectedSwarm) return;
    setLoading(true);
    apiFetch<PromptData>(`/admin/prompts/${selectedSwarm}`)
      .then((res) => {
        setPromptText(res.currentPrompt);
        setOriginalText(res.currentPrompt);
        setVersions(res.versions);
      })
      .catch(() => {
        setPromptText('');
        setOriginalText('');
        setVersions([]);
      })
      .finally(() => setLoading(false));
  }, [selectedSwarm, apiFetch]);

  const hasChanges = promptText !== originalText;

  const handleSave = useCallback(async () => {
    if (!selectedSwarm || !hasChanges) return;
    setSaving(true);
    try {
      await apiFetch(`/admin/prompts/${selectedSwarm}`, {
        method: 'PUT',
        body: JSON.stringify({ prompt: promptText }),
      });
      setOriginalText(promptText);
      // Reload versions
      const res = await apiFetch<PromptData>(`/admin/prompts/${selectedSwarm}`);
      setVersions(res.versions);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  }, [selectedSwarm, promptText, hasChanges, apiFetch]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="grid grid-cols-[1fr_300px] gap-6">
        {/* Left — Prompt editor */}
        <div className="space-y-4">
          {/* Swarm selector */}
          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">Swarm</label>
            <select
              value={selectedSwarm}
              onChange={(e) => setSelectedSwarm(e.target.value)}
              className="h-10 px-4 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20 w-full max-w-xs"
            >
              {swarms.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Prompt textarea */}
          {loading ? (
            <div className="skeleton h-96 rounded-xl" />
          ) : (
            <div className="relative">
              <textarea
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                rows={20}
                className={cn(
                  'w-full rounded-xl border border-border-default bg-canvas-elevated px-4 py-3',
                  'text-sm text-text-primary font-mono leading-relaxed',
                  'placeholder:text-text-tertiary',
                  'focus:border-brand-primary focus:outline-none focus:ring-2 focus:ring-brand-primary/20',
                  'resize-y',
                  hasChanges && 'border-warning',
                )}
                placeholder="Enter system prompt..."
              />
              {hasChanges && (
                <span className="absolute top-3 right-3 text-[10px] font-medium px-2 py-0.5 rounded-full bg-warning/15 text-warning">
                  Unsaved changes
                </span>
              )}
            </div>
          )}

          {/* Save button */}
          <div className="flex justify-end">
            <Button
              variant="primary"
              size="md"
              isLoading={saving}
              disabled={!hasChanges || loading}
              onClick={handleSave}
            >
              Save Prompt
            </Button>
          </div>
        </div>

        {/* Right — Version history */}
        <Card>
          <CardContent className="py-4">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Version History</h3>
            {versions.length === 0 ? (
              <p className="text-xs text-text-tertiary">No version history available.</p>
            ) : (
              <div className="space-y-3 max-h-[500px] overflow-y-auto">
                {versions.map((v) => (
                  <div
                    key={v.version}
                    className="border-l-2 border-border-default pl-3 py-1"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-text-primary">v{v.version}</span>
                    </div>
                    <p className="text-[11px] text-text-tertiary mt-0.5">
                      {v.updatedBy} &middot;{' '}
                      {new Date(v.updatedAt).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}
