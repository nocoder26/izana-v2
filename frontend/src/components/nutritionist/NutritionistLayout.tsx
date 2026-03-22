'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

type NutritionistLayoutProps = {
  children: ReactNode;
};

export default function NutritionistLayout({ children }: NutritionistLayoutProps) {
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
            The Nutritionist Portal requires a screen width of at least 1024px.
            Please switch to a desktop or laptop browser.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('min-h-dvh bg-canvas-base')} style={{ minHeight: '100vh' }}>
      {children}
    </div>
  );
}
