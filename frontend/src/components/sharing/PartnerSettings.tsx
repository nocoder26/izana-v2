'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiGet, apiPut } from '@/lib/api-client';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

/* ── Types ────────────────────────────────────────────────────── */

interface VisibilitySettings {
  mood: boolean;
  phase: boolean;
  symptoms: boolean;
  planAdherence: boolean;
}

/* ── Toggle Component ─────────────────────────────────────────── */

function ToggleSwitch({
  checked,
  onChange,
  disabled,
  label,
  description,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
  label: string;
  description?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        'flex items-center justify-between gap-4 w-full py-3',
        'text-left transition-opacity',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary">{label}</p>
        {description && (
          <p className="text-xs text-text-tertiary mt-0.5">{description}</p>
        )}
      </div>
      <div
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0',
          checked ? 'bg-brand-primary' : 'bg-border-default',
        )}
      >
        <motion.div
          className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow-sm"
          animate={{ left: checked ? 22 : 2 }}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      </div>
    </button>
  );
}

/* ── Main Component ───────────────────────────────────────────── */

export default function PartnerSettings() {
  const [settings, setSettings] = useState<VisibilitySettings>({
    mood: true,
    phase: true,
    symptoms: false,
    planAdherence: false,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [savedSettings, setSavedSettings] = useState<VisibilitySettings | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    async function fetchSettings() {
      try {
        const data = await apiGet<VisibilitySettings>(
          '/partner/visibility',
        );
        if (!cancelled) {
          setSettings(data);
          setSavedSettings(data);
        }
      } catch {
        // Use defaults if fetch fails
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    fetchSettings();
    return () => {
      cancelled = true;
    };
  }, []);

  const updateSetting = useCallback(
    (key: keyof VisibilitySettings, value: boolean) => {
      setSettings((prev) => {
        const next = { ...prev, [key]: value };
        setHasChanges(
          savedSettings ? JSON.stringify(next) !== JSON.stringify(savedSettings) : true,
        );
        return next;
      });
    },
    [savedSettings],
  );

  const saveSettings = useCallback(async () => {
    setIsSaving(true);
    try {
      await apiPut('/partner/visibility', settings);
      setSavedSettings(settings);
      setHasChanges(false);
    } catch {
      // Silently fail — could add toast here
    } finally {
      setIsSaving(false);
    }
  }, [settings]);

  if (isLoading) {
    return (
      <Card className="mx-auto max-w-md">
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center justify-between py-3">
                <div className="space-y-1.5">
                  <div className="w-24 h-4 skeleton rounded" />
                  <div className="w-40 h-3 skeleton rounded" />
                </div>
                <div className="w-11 h-6 skeleton rounded-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-md">
      <CardHeader>
        <h2 className="font-serif text-lg text-text-primary">
          Partner visibility
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Control what your partner can see about your journey.
        </p>
      </CardHeader>

      <CardContent className="space-y-1">
        {/* Toggleable Settings */}
        <div className="divide-y divide-border-default">
          <ToggleSwitch
            label="Mood"
            description="Daily mood check-in results"
            checked={settings.mood}
            onChange={(val) => updateSetting('mood', val)}
          />
          <ToggleSwitch
            label="Phase"
            description="Current treatment phase and day"
            checked={settings.phase}
            onChange={(val) => updateSetting('phase', val)}
          />
          <ToggleSwitch
            label="Symptoms"
            description="Reported symptoms and severity"
            checked={settings.symptoms}
            onChange={(val) => updateSetting('symptoms', val)}
          />
          <ToggleSwitch
            label="Plan adherence"
            description="Completion of daily plan items"
            checked={settings.planAdherence}
            onChange={(val) => updateSetting('planAdherence', val)}
          />
        </div>

        {/* Bloodwork — Always Hidden */}
        <div
          className={cn(
            'flex items-center justify-between py-3 mt-2',
            'border-t border-border-default',
          )}
        >
          <div>
            <p className="text-sm font-medium text-text-primary">Bloodwork</p>
            <p className="text-xs text-text-tertiary mt-0.5">
              Lab results and hormone levels
            </p>
          </div>
          <span className="text-xs font-medium text-text-tertiary bg-canvas-sunken px-2.5 py-1 rounded-lg">
            Never shared
          </span>
        </div>

        {/* Save Button */}
        {hasChanges && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="pt-3"
          >
            <Button
              variant="primary"
              size="md"
              className="w-full"
              isLoading={isSaving}
              onClick={saveSettings}
            >
              Save changes
            </Button>
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}
