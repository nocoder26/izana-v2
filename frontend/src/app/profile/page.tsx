'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useUserStore } from '@/stores/user-store';
import { BottomNav, type TabId } from '@/components/navigation/BottomNav';

interface MenuItem {
  label: string;
  icon: string;
  href?: string;
  danger?: boolean;
  onClick?: () => void;
}

const PRIMARY_MENU: MenuItem[] = [
  { label: 'Partner', icon: '💑', onClick: () => alert('Partner support is coming soon! Connect your partner for daily coaching.') },
  { label: 'Content library', icon: '📚', href: '/content' },
  { label: 'Achievements', icon: '🏆', onClick: () => alert('Achievements will unlock as you complete your daily plans and maintain streaks!') },
  { label: 'Settings', icon: '⚙️', onClick: () => alert('Settings: Theme, language, and notification preferences coming soon.') },
];

const SECONDARY_MENU: MenuItem[] = [
  { label: 'Privacy & data', icon: '🔒', onClick: () => alert('Privacy & data management: Download your data or delete your account. Coming soon.') },
  { label: 'About', icon: 'ℹ️', onClick: () => alert('Izana Chat v2.0 — Your fertility wellness companion. Built with care.') },
];

export default function ProfilePage() {
  const [activeTab, setActiveTab] = useState<TabId>('you');
  const pseudonym = useUserStore((s) => s.pseudonym) ?? 'Luna';
  const avatar = useUserStore((s) => s.avatar);
  const clearUser = useUserStore((s) => s.clearUser);

  // Placeholder stats; in production, fetch from API
  const stats = {
    points: 1240,
    streak: 8,
    badges: 5,
    treatmentType: 'IVF — Cycle 1',
  };

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    if (tab === 'today') {
      window.location.href = '/chat';
    } else if (tab === 'journey') {
      window.location.href = '/journey';
    }
  };

  const handleLogout = () => {
    clearUser();
    window.location.href = '/';
  };

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
                onClick={() => item.onClick ? item.onClick() : item.href ? (window.location.href = item.href) : null}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.05 }}
                className={cn(
                  'flex items-center gap-3 px-4 py-3.5 w-full text-left',
                  'hover:bg-canvas-sunken transition-colors cursor-pointer',
                  i > 0 && 'border-t border-border-default',
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

        {/* Secondary Menu */}
        <div className="px-5 pb-6">
          <div
            className="rounded-xl border border-border-default bg-canvas-elevated overflow-hidden"
            style={{ boxShadow: '0 1px 3px rgba(42,36,51,0.04)' }}
          >
            {SECONDARY_MENU.map((item, i) => (
              <button
                key={item.label}
                onClick={() => item.onClick ? item.onClick() : item.href ? (window.location.href = item.href) : null}
                className={cn(
                  'flex items-center gap-3 px-4 py-3.5 w-full text-left',
                  'hover:bg-canvas-sunken transition-colors cursor-pointer',
                  i > 0 && 'border-t border-border-default',
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
      </div>

      {/* Bottom navigation */}
      <BottomNav activeTab={activeTab} onTabChange={handleTabChange} />
    </div>
  );
}
