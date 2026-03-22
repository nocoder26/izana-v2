'use client';

import { cn } from '@/lib/utils';

type NavItem = {
  id: string;
  label: string;
  href: string;
  badge?: number;
  icon: React.ReactNode;
};

type NutritionistSidebarProps = {
  activeItem: string;
  queueCount?: number;
};

export default function NutritionistSidebar({ activeItem, queueCount }: NutritionistSidebarProps) {
  const navItems: NavItem[] = [
    {
      id: 'queue',
      label: 'Queue',
      href: '/nutritionist/queue',
      badge: queueCount,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
          />
        </svg>
      ),
    },
    {
      id: 'plans',
      label: 'My Plans',
      href: '/nutritionist/queue?view=my-plans',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
      ),
    },
    {
      id: 'analytics',
      label: 'Analytics',
      href: '/nutritionist/queue?view=analytics',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
      ),
    },
  ];

  return (
    <aside
      className={cn(
        'w-[220px] min-h-dvh bg-canvas-elevated border-r border-border-default',
        'flex flex-col',
      )}
      style={{ minHeight: '100vh' }}
    >
      {/* Logo / Brand */}
      <div className="px-5 py-6 border-b border-border-default">
        <div className="flex items-center gap-2.5">
          <div className="izana-avatar w-8 h-8" />
          <div>
            <p className="text-sm font-semibold text-text-primary">Izana</p>
            <p className="text-[10px] text-text-tertiary">Nutritionist Portal</p>
          </div>
        </div>
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {navItems.map((item) => {
          const isActive = activeItem === item.id;
          return (
            <a
              key={item.id}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-colors duration-150',
                isActive
                  ? 'bg-brand-primary-bg text-brand-primary font-medium'
                  : 'text-text-secondary hover:bg-canvas-sunken hover:text-text-primary',
              )}
            >
              <span className={cn(isActive ? 'text-brand-primary' : 'text-text-tertiary')}>
                {item.icon}
              </span>
              <span className="flex-1">{item.label}</span>
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={cn(
                    'min-w-[20px] h-5 flex items-center justify-center rounded-full text-[10px] font-bold px-1.5',
                    isActive
                      ? 'bg-brand-primary text-white'
                      : 'bg-canvas-sunken text-text-tertiary',
                  )}
                >
                  {item.badge}
                </span>
              )}
            </a>
          );
        })}
      </nav>

      {/* Sign out */}
      <div className="px-3 pb-6">
        <button
          onClick={() => {
            sessionStorage.removeItem('nutritionist_jwt');
            window.location.href = '/nutritionist/login';
          }}
          className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-text-tertiary hover:text-error hover:bg-error/5 transition-colors w-full"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
          Sign Out
        </button>
      </div>
    </aside>
  );
}
