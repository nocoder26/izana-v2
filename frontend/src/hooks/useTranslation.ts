'use client';

import { useMemo, useCallback } from 'react';
import { en, type TranslationKeys } from '@/lib/translations/en';

/* ── Supported Languages ──────────────────────────────────────── */

type SupportedLang = 'en' | 'es';

const STORAGE_KEY = 'izana_lang';

/**
 * Lazily load translation files to avoid bundling all languages upfront.
 */
const translationLoaders: Record<
  SupportedLang,
  () => Promise<TranslationKeys>
> = {
  en: async () => en,
  es: async () => {
    const mod = await import('@/lib/translations/es');
    return mod.es;
  },
};

/* ── Cached translations ──────────────────────────────────────── */

const translationCache = new Map<SupportedLang, TranslationKeys>();
translationCache.set('en', en);

/* ── Utility: Deep key access ─────────────────────────────────── */

type NestedKeyOf<T> = T extends object
  ? {
      [K in keyof T & string]: T[K] extends object
        ? `${K}` | `${K}.${NestedKeyOf<T[K]>}`
        : `${K}`;
    }[keyof T & string]
  : never;

type TranslationKey = NestedKeyOf<TranslationKeys>;

function getNestedValue(obj: unknown, path: string): string | undefined {
  const keys = path.split('.');
  let current: unknown = obj;
  for (const key of keys) {
    if (current == null || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[key];
  }
  return typeof current === 'string' ? current : undefined;
}

/* ── Hook ─────────────────────────────────────────────────────── */

export function useTranslation() {
  const lang = useMemo<SupportedLang>(() => {
    if (typeof window === 'undefined') return 'en';
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'en' || stored === 'es') return stored;
    } catch {
      // localStorage unavailable
    }
    return 'en';
  }, []);

  // Eagerly load the active translation into cache
  useMemo(() => {
    if (!translationCache.has(lang)) {
      translationLoaders[lang]().then((t) => {
        translationCache.set(lang, t);
      });
    }
  }, [lang]);

  /**
   * Translate a dotted key path. Falls back to English for missing keys.
   *
   * Supports simple interpolation: `t('partner.codeExpires', { days: 7 })`
   */
  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>): string => {
      const translations = translationCache.get(lang) ?? en;

      let value = getNestedValue(translations, key);

      // Fallback to English
      if (value === undefined && lang !== 'en') {
        value = getNestedValue(en, key);
      }

      // Last resort: return the key itself
      if (value === undefined) return key;

      // Interpolate variables
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          value = value.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        }
      }

      return value;
    },
    [lang],
  );

  const setLanguage = useCallback((newLang: SupportedLang) => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY, newLang);
    } catch {
      // silently fail
    }
    // Reload to apply — simpler than full reactive i18n for a mobile-first app
    window.location.reload();
  }, []);

  return { t, lang, setLanguage };
}

export type { TranslationKey, SupportedLang };
export default useTranslation;
