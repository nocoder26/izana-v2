'use client';

import { useEffect } from 'react';
import { Inter, DM_Serif_Display, JetBrains_Mono } from 'next/font/google';
import { Toaster } from 'sonner';
import { applyTheme, listenForSystemThemeChanges } from '@/lib/theme';
import { useThemeStore } from '@/stores/theme-store';
import '@/styles/globals.css';

/* ── Font loading via next/font ─────────────────────────────── */

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const dmSerifDisplay = DM_Serif_Display({
  subsets: ['latin'],
  weight: ['400'],
  variable: '--font-dm-serif',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
});

/* ── Root Layout ────────────────────────────────────────────── */

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = useThemeStore((s) => s.theme);

  /* Apply theme on mount + listen for OS changes */
  useEffect(() => {
    applyTheme(theme);
    const unsubscribe = listenForSystemThemeChanges();
    return unsubscribe;
  }, [theme]);

  /* Register service worker for PWA */
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        // SW registration failed — app still works without it
      });
    }
  }, []);

  return (
    <html
      lang="en"
      className={`${inter.variable} ${dmSerifDisplay.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <title>Izana Chat</title>
        <meta name="description" content="Your fertility wellness companion" />
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#FAF9F7" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#1A171F" media="(prefers-color-scheme: dark)" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" href="/icons/icon-192.png" type="image/png" sizes="192x192" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
      </head>
      <body
        className="min-h-dvh bg-canvas-base font-sans text-text-primary antialiased"
        style={{ minHeight: '100vh' }}
      >
        {children}

        <Toaster
          position="bottom-center"
          toastOptions={{
            style: {
              background: 'var(--canvas-elevated)',
              color: 'var(--text-primary)',
              border: '0.5px solid var(--border-default)',
              borderRadius: '14px',
              boxShadow: '0 4px 12px rgba(42, 36, 51, 0.08)',
              fontFamily: 'var(--font-inter, Inter, sans-serif)',
            },
          }}
          offset={16}
          gap={8}
        />
      </body>
    </html>
  );
}
