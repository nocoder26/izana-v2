'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PreviewChat from '@/components/landing/PreviewChat';
import SignupModal from '@/components/identity/SignupModal';
import LoginModal from '@/components/identity/LoginModal';

const SUGGESTED_QUESTIONS = [
  'What foods boost egg quality during IVF?',
  'How does stress affect fertility treatment?',
  'What supplements should I take during my TWW?',
];

const TRUST_BADGES = [
  { icon: '🔒', label: 'Anonymous' },
  { icon: '🥗', label: 'Nutritionist reviewed' },
  { icon: '🌐', label: '11 languages' },
];

const BOTTOM_NAV_ITEMS = [
  { icon: '💬', label: 'Chat' },
  { icon: '📊', label: 'Track' },
  { icon: '🍽️', label: 'Meals' },
  { icon: '🧘', label: 'Wellness' },
  { icon: '👤', label: 'Profile' },
];

type LanguageCode =
  | 'en'
  | 'es'
  | 'fr'
  | 'de'
  | 'pt'
  | 'it'
  | 'ar'
  | 'hi'
  | 'zh'
  | 'ja'
  | 'ko';

const LANGUAGES: { code: LanguageCode; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'es', label: 'ES' },
  { code: 'fr', label: 'FR' },
  { code: 'de', label: 'DE' },
  { code: 'pt', label: 'PT' },
  { code: 'it', label: 'IT' },
  { code: 'ar', label: 'AR' },
  { code: 'hi', label: 'HI' },
  { code: 'zh', label: 'ZH' },
  { code: 'ja', label: 'JA' },
  { code: 'ko', label: 'KO' },
];

export default function LandingPage() {
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);
  const [showSignup, setShowSignup] = useState(false);
  const [showLogin, setShowLogin] = useState(false);
  const [language, setLanguage] = useState<LanguageCode>('en');
  const [showLangPicker, setShowLangPicker] = useState(false);

  const handleQuestionTap = (index: number) => {
    setPreviewIndex(index);
  };

  const handleCtaClick = () => {
    setShowSignup(true);
  };

  const handleLoginClick = () => {
    setShowLogin(true);
  };

  return (
    <div className="flex flex-col h-[100dvh] bg-canvas-base overflow-hidden">
      {/* ─── Top bar ─── */}
      <header className="flex items-center justify-between px-5 py-3 shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="text-brand-primary text-lg">✦</span>
          <span className="font-serif text-lg text-text-primary tracking-tight">
            izana
          </span>
        </div>

        {/* Language selector */}
        <div className="relative">
          <button
            onClick={() => setShowLangPicker(!showLangPicker)}
            className="flex items-center gap-1 text-xs text-text-secondary px-2 py-1 rounded-lg hover:bg-canvas-sunken transition-colors"
          >
            🌐 {language.toUpperCase()}
          </button>
          <AnimatePresence>
            {showLangPicker && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 bg-canvas-elevated rounded-xl border border-border-default py-1 z-50 min-w-[72px]"
                style={{ boxShadow: 'var(--shadow-md, 0 4px 12px rgba(45, 42, 38, 0.08))' }}
              >
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => {
                      setLanguage(lang.code);
                      setShowLangPicker(false);
                    }}
                    className={`block w-full text-left px-3 py-1.5 text-xs transition-colors ${
                      language === lang.code
                        ? 'text-brand-primary font-medium bg-brand-primary-bg'
                        : 'text-text-secondary hover:bg-canvas-sunken'
                    }`}
                  >
                    {lang.label}
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </header>

      {/* ─── Main content area ─── */}
      <main className="flex-1 flex flex-col px-5 overflow-y-auto">
        <AnimatePresence mode="wait">
          {previewIndex === null ? (
            <motion.div
              key="intro"
              initial={{ opacity: 1 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col items-center flex-1 justify-center gap-5"
            >
              {/* Izana avatar with breathing animation */}
              <div className="izana-avatar flex items-center justify-center" style={{ width: 56, height: 56 }}>
                <span className="text-white text-2xl">✦</span>
              </div>

              {/* Intro message */}
              <div className="text-center space-y-3">
                <h1 className="font-serif text-2xl leading-snug text-text-primary px-2">
                  Your fertility journey is unique. Your support should be too.
                </h1>
                <p className="text-sm text-text-secondary leading-relaxed px-4">
                  Izana combines clinical research with your personal profile to
                  give you nutrition, supplement, and lifestyle guidance tailored
                  to your treatment phase.
                </p>
              </div>

              {/* Suggested question chips */}
              <div className="flex flex-col gap-2 w-full mt-1">
                {SUGGESTED_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuestionTap(i)}
                    className="w-full text-left px-4 py-3 rounded-2xl bg-canvas-elevated border border-border-default text-sm text-text-primary active:scale-[0.97] transition-all hover:border-brand-primary/30"
                    style={{ boxShadow: 'var(--shadow-sm, 0 1px 2px rgba(45, 42, 38, 0.06))' }}
                  >
                    {q}
                  </button>
                ))}
              </div>

              {/* Trust badges */}
              <div className="flex items-center gap-2 mt-1">
                {TRUST_BADGES.map((badge, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-brand-primary-bg text-brand-primary border border-brand-primary/15"
                  >
                    <span>{badge.icon}</span>
                    {badge.label}
                  </span>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="preview"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col pt-2"
            >
              {/* Back button */}
              <button
                onClick={() => setPreviewIndex(null)}
                className="self-start text-xs text-text-secondary mb-3 flex items-center gap-1 hover:text-text-primary transition-colors"
              >
                ← Back
              </button>

              <PreviewChat
                questionIndex={previewIndex}
                onCtaClick={handleCtaClick}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* ─── Bottom section ─── */}
      <div className="shrink-0 px-5 pb-2 space-y-3 safe-area-bottom">
        {previewIndex === null && (
          <>
            {/* CTA button */}
            <button
              onClick={handleCtaClick}
              className="w-full bg-brand-primary text-white font-medium py-3.5 rounded-full text-sm active:scale-[0.97] transition-transform"
              style={{ boxShadow: 'var(--shadow-sm, 0 1px 2px rgba(45, 42, 38, 0.06))' }}
            >
              Start my journey — free &amp; anonymous
            </button>

            {/* Fake chat input */}
            <div className="flex items-center gap-2 bg-canvas-elevated border border-border-default rounded-full px-4 py-2.5 opacity-60">
              <span className="text-text-tertiary text-sm flex-1">
                Ask Izana anything...
              </span>
              <span className="text-brand-primary text-lg">↑</span>
            </div>

            <p className="text-center text-xs text-text-tertiary">
              Already have an account?{' '}
              <button
                onClick={handleLoginClick}
                className="text-brand-primary font-medium underline-offset-2 hover:underline"
              >
                Log in
              </button>
            </p>
          </>
        )}

        {/* Bottom nav (greyed out, non-functional pre-auth) */}
        <nav className="flex items-center justify-around pt-2 border-t border-border-default opacity-40">
          {BOTTOM_NAV_ITEMS.map((item) => (
            <div
              key={item.label}
              className="flex flex-col items-center gap-0.5 py-1"
            >
              <span className="text-base">{item.icon}</span>
              <span className="text-[10px] text-text-tertiary">{item.label}</span>
            </div>
          ))}
        </nav>
      </div>

      {/* ─── Modals ─── */}
      <AnimatePresence>
        {showSignup && (
          <SignupModal
            onClose={() => setShowSignup(false)}
            onSwitchToLogin={() => {
              setShowSignup(false);
              setShowLogin(true);
            }}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showLogin && (
          <LoginModal
            onClose={() => setShowLogin(false)}
            onSwitchToSignup={() => {
              setShowLogin(false);
              setShowSignup(true);
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
