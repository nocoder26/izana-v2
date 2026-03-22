'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useUserStore } from '@/stores/user-store';
import { useThemeStore } from '@/stores/theme-store';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';
import { apiGet } from '@/lib/api-client';
import { supabase } from '@/lib/supabase/client';
import PartnerInvite from '@/components/sharing/PartnerInvite';
import type { Theme } from '@/lib/theme';

/* ── Types ─────────────────────────────────────────────────── */

type GamificationSummary = {
  points: number;
  streak: number;
  badges_earned: number;
  treatment_type?: string;
};

type Badge = {
  id: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  earned_at?: string;
};

/* ── Panel components ──────────────────────────────────────── */

type PanelName = 'partner' | 'achievements' | 'settings' | 'privacy' | 'about' | null;

function AchievementsPanel({ onClose }: { onClose: () => void }) {
  const [badges, setBadges] = useState<Badge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet<{ badges: Badge[] }>('/gamification/badges')
      .then((res) => setBadges(res.badges ?? []))
      .catch(() => setBadges([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="px-5 pb-4"
    >
      <div className="rounded-xl border border-border-default bg-canvas-elevated p-4" style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">Achievements</h3>
          <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">Close</button>
        </div>

        {loading ? (
          <p className="text-sm text-text-tertiary py-4 text-center">Loading badges...</p>
        ) : badges.length === 0 ? (
          <p className="text-sm text-text-tertiary py-4 text-center">
            Complete daily plans and maintain streaks to unlock achievements.
          </p>
        ) : (
          <div className="grid grid-cols-3 gap-3">
            {badges.map((badge) => (
              <div
                key={badge.id}
                className={cn(
                  'flex flex-col items-center gap-1 py-3 rounded-xl text-center',
                  badge.earned ? 'bg-brand-primary-bg' : 'bg-canvas-sunken opacity-50',
                )}
              >
                <span className="text-2xl">{badge.icon || '🏅'}</span>
                <span className="text-[10px] font-medium text-text-primary leading-tight px-1">
                  {badge.name}
                </span>
                {badge.earned && (
                  <span className="text-[9px] text-success font-medium">Earned</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function SettingsPanel({ onClose }: { onClose: () => void }) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  const themes: { value: Theme; label: string; icon: string }[] = [
    { value: 'light', label: 'Light', icon: '☀️' },
    { value: 'dark', label: 'Dark', icon: '🌙' },
    { value: 'system', label: 'System', icon: '💻' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="px-5 pb-4"
    >
      <div className="rounded-xl border border-border-default bg-canvas-elevated p-4" style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">Settings</h3>
          <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">Close</button>
        </div>

        <p className="text-xs font-medium text-text-secondary mb-2">Theme</p>
        <div className="flex gap-2">
          {themes.map((t) => (
            <button
              key={t.value}
              onClick={() => setTheme(t.value)}
              className={cn(
                'flex-1 flex flex-col items-center gap-1 py-3 rounded-xl transition-colors',
                'border',
                theme === t.value
                  ? 'bg-brand-primary-bg border-brand-primary/40 text-brand-primary'
                  : 'bg-canvas-sunken border-border-default text-text-secondary hover:border-brand-primary/20',
              )}
            >
              <span className="text-lg">{t.icon}</span>
              <span className="text-xs font-medium">{t.label}</span>
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function PrivacyPanel({ onClose }: { onClose: () => void }) {
  const [downloading, setDownloading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const clearUser = useUserStore((s) => s.clearUser);

  const handleDownloadData = useCallback(async () => {
    setDownloading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
      const res = await fetch(`${apiUrl}/data-export`, {
        headers: session?.access_token
          ? { Authorization: `Bearer ${session.access_token}` }
          : {},
      });
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'izana-data-export.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Silently fail - could show error toast
    } finally {
      setDownloading(false);
    }
  }, []);

  const handleDeleteAccount = useCallback(async () => {
    setDeleting(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? '';
      await fetch(`${apiUrl}/auth/delete-account`, {
        method: 'DELETE',
        headers: session?.access_token
          ? { Authorization: `Bearer ${session.access_token}` }
          : {},
      });
      await supabase.auth.signOut();
      clearUser();
      window.location.href = '/';
    } catch {
      setDeleting(false);
    }
  }, [clearUser]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="px-5 pb-4"
    >
      <div className="rounded-xl border border-border-default bg-canvas-elevated p-4" style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">Privacy & Data</h3>
          <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">Close</button>
        </div>

        <div className="space-y-3">
          <button
            onClick={handleDownloadData}
            disabled={downloading}
            className={cn(
              'w-full py-3 rounded-xl text-sm font-medium transition-colors',
              'bg-canvas-sunken text-text-primary hover:bg-brand-primary-bg',
              downloading && 'opacity-50',
            )}
          >
            {downloading ? 'Downloading...' : '📥 Download my data'}
          </button>

          {!showDeleteConfirm ? (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="w-full py-3 rounded-xl text-sm font-medium text-error bg-error/5 hover:bg-error/10 transition-colors"
            >
              🗑️ Delete my account
            </button>
          ) : (
            <div className="bg-error/5 rounded-xl p-3 space-y-2">
              <p className="text-xs text-error font-medium">
                This will permanently delete all your data. This action cannot be undone.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 py-2 rounded-lg text-xs font-medium bg-canvas-elevated text-text-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleting}
                  className="flex-1 py-2 rounded-lg text-xs font-medium bg-error text-white"
                >
                  {deleting ? 'Deleting...' : 'Confirm delete'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function AboutPanel({ onClose }: { onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="px-5 pb-4"
    >
      <div className="rounded-xl border border-border-default bg-canvas-elevated p-4 text-center" style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-primary">About</h3>
          <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">Close</button>
        </div>

        <div className="py-3 space-y-2">
          <div className="izana-avatar flex items-center justify-center mx-auto" style={{ width: 40, height: 40 }}>
            <span className="text-white text-lg">✦</span>
          </div>
          <h4 className="font-serif text-lg text-text-primary">Izana Chat</h4>
          <p className="text-xs text-text-secondary">Version 2.0</p>
          <p className="text-xs text-text-tertiary leading-relaxed px-2">
            Your fertility wellness companion. Izana combines clinical research with
            your personal profile to provide nutrition, supplement, and lifestyle
            guidance tailored to your treatment phase. Built with care.
          </p>
        </div>
      </div>
    </motion.div>
  );
}

function PartnerPanel({ onClose }: { onClose: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="px-5 pb-4"
    >
      <div className="flex items-center justify-end mb-2">
        <button onClick={onClose} className="text-text-tertiary text-xs hover:text-text-primary">Close</button>
      </div>
      <PartnerInvite />
    </motion.div>
  );
}

/* ── Main Page ──────────────────────────────────────────────── */

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<TabId>('you');
  const [activePanel, setActivePanel] = useState<PanelName>(null);
  const pseudonym = useUserStore((s) => s.pseudonym) ?? 'Luna';
  const avatar = useUserStore((s) => s.avatar);
  const clearUser = useUserStore((s) => s.clearUser);

  // Real stats from API
  const [stats, setStats] = useState({
    points: 0,
    streak: 0,
    badges: 0,
    treatmentType: 'Loading...',
  });

  useEffect(() => {
    apiGet<GamificationSummary>('/gamification/summary')
      .then((res) => {
        setStats({
          points: res.points ?? 0,
          streak: res.streak ?? 0,
          badges: res.badges_earned ?? 0,
          treatmentType: res.treatment_type ?? 'Your journey',
        });
      })
      .catch(() => {
        setStats({
          points: 0,
          streak: 0,
          badges: 0,
          treatmentType: 'Your journey',
        });
      });
  }, []);

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    if (tab === 'today') {
      window.location.href = '/chat';
    } else if (tab === 'journey') {
      window.location.href = '/journey';
    }
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
    } catch {
      // Continue with logout even if signOut fails
    }
    clearUser();
    window.location.href = '/';
  };

  const togglePanel = (panel: PanelName) => {
    setActivePanel(activePanel === panel ? null : panel);
  };

  const PRIMARY_MENU = [
    { label: 'Partner', icon: '💑', panel: 'partner' as PanelName },
    { label: 'Content library', icon: '📚', href: '/content' },
    { label: 'Achievements', icon: '🏆', panel: 'achievements' as PanelName },
    { label: 'Settings', icon: '⚙️', panel: 'settings' as PanelName },
  ];

  const SECONDARY_MENU = [
    { label: 'Privacy & data', icon: '🔒', panel: 'privacy' as PanelName },
    { label: 'About', icon: 'ℹ️', panel: 'about' as PanelName },
  ];

  return (
    <div className="flex flex-col h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Header */}
      <header
        className="bg-canvas-elevated border-b border-border-default px-5 py-4"
        style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
      >
        <h1 className="text-lg font-semibold text-text-primary">You</h1>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto pb-[68px]">
        {/* Avatar + Info */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center py-8 px-5"
        >
          <div
            className={cn(
              'w-20 h-20 rounded-full mb-3',
              'bg-gradient-to-br from-brand-primary to-brand-accent',
              'flex items-center justify-center text-white text-2xl font-semibold',
              'shadow-[0_4px_12px_rgba(74,61,143,0.2)]',
            )}
          >
            {avatar ? (
              <img
                src={avatar}
                alt={pseudonym}
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              pseudonym.charAt(0).toUpperCase()
            )}
          </div>
          <h2 className="text-lg font-semibold text-text-primary">{pseudonym}</h2>
          <p className="text-sm text-text-secondary mt-0.5">
            {stats.treatmentType}
          </p>
        </motion.div>

        {/* Stats Row */}
        <div className="px-5 pb-6">
          <div
            className={cn(
              'flex rounded-xl border border-border-default bg-canvas-elevated overflow-hidden',
            )}
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            {[
              { label: 'Points', value: stats.points.toLocaleString() },
              {
                label: 'Streak',
                value: (
                  <>
                    <span className="fire-pulse inline-block mr-0.5">🔥</span>
                    {stats.streak}
                  </>
                ),
              },
              { label: 'Badges', value: stats.badges },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className={cn(
                  'flex-1 py-3 text-center',
                  i < 2 && 'border-r border-border-default',
                )}
              >
                <p className="text-lg font-semibold text-text-primary">
                  {stat.value}
                </p>
                <p className="text-xs text-text-tertiary">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Primary Menu */}
        <div className="px-5 pb-4">
          <div
            className="rounded-xl border border-border-default bg-canvas-elevated overflow-hidden"
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            {PRIMARY_MENU.map((item, i) => (
              <motion.button
                key={item.label}
                onClick={() => item.panel ? togglePanel(item.panel) : item.href ? (window.location.href = item.href) : null}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-3.5 w-full text-left',
                  'hover:bg-canvas-sunken transition-colors cursor-pointer',
                  i > 0 && 'border-t border-border-default',
                  activePanel === item.panel && 'bg-brand-primary-bg',
                )}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-sm font-medium text-text-primary flex-1">
                  {item.label}
                </span>
                <span className="text-text-tertiary text-sm">›</span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* Inline panel for primary menu */}
        <AnimatePresence>
          {activePanel === 'partner' && <PartnerPanel onClose={() => setActivePanel(null)} />}
          {activePanel === 'achievements' && <AchievementsPanel onClose={() => setActivePanel(null)} />}
          {activePanel === 'settings' && <SettingsPanel onClose={() => setActivePanel(null)} />}
        </AnimatePresence>

        {/* Secondary Menu */}
        <div className="px-5 pb-6">
          <div
            className="rounded-xl border border-border-default bg-canvas-elevated overflow-hidden"
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            {SECONDARY_MENU.map((item, i) => (
              <button
                key={item.label}
                onClick={() => item.panel ? togglePanel(item.panel) : null}
                className={cn(
                  'flex items-center gap-3 px-4 py-3.5 w-full text-left',
                  'hover:bg-canvas-sunken transition-colors cursor-pointer',
                  i > 0 && 'border-t border-border-default',
                  activePanel === item.panel && 'bg-brand-primary-bg',
                )}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="text-sm font-medium text-text-primary flex-1">
                  {item.label}
                </span>
                <span className="text-text-tertiary text-sm">›</span>
              </button>
            ))}

            {/* Log out */}
            <button
              onClick={handleLogout}
              className={cn(
                'flex items-center gap-3 px-4 py-3.5 w-full',
                'hover:bg-canvas-sunken transition-colors',
                'border-t border-border-default',
              )}
            >
              <span className="text-lg">🚪</span>
              <span className="text-sm font-medium text-error flex-1 text-left">
                Log out
              </span>
            </button>
          </div>
        </div>

        {/* Inline panel for secondary menu */}
        <AnimatePresence>
          {activePanel === 'privacy' && <PrivacyPanel onClose={() => setActivePanel(null)} />}
          {activePanel === 'about' && <AboutPanel onClose={() => setActivePanel(null)} />}
        </AnimatePresence>
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
