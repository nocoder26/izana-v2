'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

type AdminLayoutProps = {
  children: ReactNode;
  activeTab: string;
  onTabChange: (tab: string) => void;
};

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'analytics', label: 'Analytics' },
  { id: 'feedback', label: 'Feedback' },
  { id: 'training', label: 'Training' },
  { id: 'health', label: 'Health' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'content', label: 'Content Manager' },
  { id: 'plans', label: 'Plans Queue' },
];

export default function AdminLayout({ children, activeTab, onTabChange }: AdminLayoutProps) {
  const [isTooSmall, setIsTooSmall] = useState(false);

  useEffect(() => {
    const check = () => setIsTooSmall(window.innerWidth < 1024);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  if (isTooSmall) {
    return (
      <div className="flex items-center justify-center h-dvh bg-canvas-base px-6" style={{ minHeight: '100vh' }}>
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 rounded-full bg-brand-primary/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-brand-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-text-primary mb-2">Desktop Required</h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            The Admin Dashboard requires a screen width of at least 1024px.
            Please switch to a desktop or laptop browser.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-canvas-base" style={{ minHeight: '100vh' }}>
      {/* Top header */}
      <header className="border-b border-border-default bg-canvas-elevated sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-6">
          {/* Brand row */}
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="izana-avatar w-7 h-7" />
              <div>
                <span className="text-sm font-semibold text-text-primary">Izana</span>
                <span className="text-xs text-text-tertiary ml-2">Admin</span>
              </div>
            </div>
            <button
              onClick={() => {
                sessionStorage.removeItem('admin_jwt');
                sessionStorage.removeItem('admin_api_key');
                window.location.href = '/admin';
              }}
              className="text-xs text-text-tertiary hover:text-error transition-colors"
            >
              Sign Out
            </button>
          </div>

          {/* Tabs row */}
          <div className="flex gap-0 -mb-px overflow-x-auto">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={cn(
                  'px-4 pb-3 pt-1 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                  activeTab === tab.id
                    ? 'border-brand-primary text-brand-primary'
                    : 'border-transparent text-text-tertiary hover:text-text-secondary',
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-[1400px] mx-auto px-6 py-6">
        {children}
      </main>
    </div>
  );
}
