'use client';

import { useState, useCallback, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { supabase } from '@/lib/supabase/client';

export type TabId = 'today' | 'journey' | 'you';

type Tab = {
  id: TabId;
  label: string;
};

const TABS: Tab[] = [
  { id: 'today', label: 'Today' },
  { id: 'journey', label: 'Journey' },
  { id: 'you', label: 'You' },
];

type BottomNavProps = {
  activeTab?: TabId;
  onTabChange?: (tab: TabId) => void;
  className?: string;
};

export function BottomNav({ activeTab: controlledTab, onTabChange, className }: BottomNavProps) {
  const [internalTab, setInternalTab] = useState<TabId>('today');
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check Supabase session (persists across page reloads, unlike Zustand)
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setIsAuthenticated(!!session);
    });
  }, []);

  const activeTab = controlledTab ?? internalTab;

  const handleTabChange = useCallback(
    (tab: TabId) => {
      if (!isAuthenticated) return;
      setInternalTab(tab);
      onTabChange?.(tab);
    },
    [isAuthenticated, onTabChange],
  );

  return (
    <nav
      className={cn(
        'fixed bottom-0 left-0 right-0 z-[100]',
        'bg-canvas-elevated/95 backdrop-blur-md',
        'border-t border-border-default',
        'safe-area-bottom',
        className,
      )}
      style={{ height: 'calc(52px + env(safe-area-inset-bottom, 0px))' }}
      role="tablist"
      aria-label="Main navigation"
    >
      <div className="flex h-[52px] items-center justify-around px-6">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          const isDisabled = !isAuthenticated;

          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-disabled={isDisabled}
              onClick={() => handleTabChange(tab.id)}
              className={cn(
                'relative px-4 py-1 text-sm transition-colors duration-200',
                'rounded-2xl select-none',
                isDisabled && 'cursor-not-allowed opacity-40',
                !isDisabled && !isActive && 'text-text-tertiary text-[13px] hover:text-text-secondary',
                !isDisabled && isActive && 'text-brand-primary font-medium',
              )}
            >
              {/* Active pill background */}
              <AnimatePresence>
                {isActive && !isDisabled && (
                  <motion.span
                    layoutId="bottom-nav-pill"
                    className="absolute inset-0 rounded-2xl bg-brand-primary-bg"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{
                      type: 'spring',
                      stiffness: 350,
                      damping: 30,
                    }}
                  />
                )}
              </AnimatePresence>
              <span className="relative z-10">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default BottomNav;
