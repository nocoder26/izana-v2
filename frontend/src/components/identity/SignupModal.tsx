'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { apiPost } from '@/lib/api-client';
import { supabase } from '@/lib/supabase/client';
import { useUserStore } from '@/stores/user-store';
import RecoveryPhrase from '@/components/identity/RecoveryPhrase';

/* ── Pseudonym generation ─────────────────────────────────────── */

const ADJECTIVES = [
  'Hopeful', 'Radiant', 'Brave', 'Serene', 'Vibrant', 'Gentle',
  'Resilient', 'Luminous', 'Graceful', 'Steadfast', 'Tranquil', 'Fierce',
  'Bright', 'Joyful', 'Calm', 'Warm', 'Bold', 'Pure',
  'Free', 'Noble', 'Swift', 'Wise', 'True', 'Kind',
];

const NOUNS = [
  'Sunrise', 'Bloom', 'Journey', 'River', 'Meadow', 'Horizon',
  'Garden', 'Aurora', 'Coral', 'Haven', 'Ocean', 'Willow',
  'Phoenix', 'Ember', 'Crystal', 'Breeze', 'Harbor', 'Summit',
  'Valley', 'Lotus', 'Petal', 'Starlight', 'Moonbeam', 'Cascade',
];

function generatePseudonym(): string {
  const adj = ADJECTIVES[Math.floor(Math.random() * ADJECTIVES.length)];
  const noun = NOUNS[Math.floor(Math.random() * NOUNS.length)];
  const num = Math.floor(Math.random() * 900) + 100; // 100-999
  return `${adj}${noun}${num}`;
}

/* ── Avatar options ───────────────────────────────────────────── */

const AVATARS = ['🦋', '🌸', '🌟', '🌹', '💎', '🌺', '🌷', '🍃', '✨', '🌙'];

/* ── Types ────────────────────────────────────────────────────── */

type Sex = 'F' | 'M';

interface SignupModalProps {
  onClose: () => void;
  onSwitchToLogin: () => void;
}

interface SignupResponse {
  user_id: string;
  pseudonym: string;
  recovery_phrase: string;
  access_token: string;
}

export default function SignupModal({ onClose, onSwitchToLogin }: SignupModalProps) {
  const router = useRouter();
  const [pseudonym, setPseudonym] = useState(generatePseudonym);
  const [avatar, setAvatar] = useState('🦋');
  const [sex, setSex] = useState<Sex>('F');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recoveryPhrase, setRecoveryPhrase] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  const setUser = useUserStore((s) => s.setUser);

  const isValid = useMemo(() => password.length >= 8, [password]);

  const handleRegenerate = useCallback(() => {
    setPseudonym(generatePseudonym());
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!isValid || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);

    try {
      const res = await apiPost<SignupResponse>('/auth/signup', {
        pseudonym,
        avatar,
        gender: sex === 'M' ? 'Male' : 'Female',
        password,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
      });

      setUser({
        userId: res.user_id,
        pseudonym: res.pseudonym,
        avatar,
      });

      setRecoveryPhrase(res.recovery_phrase);
      setAccessToken(res.access_token);

      // Set the Supabase session so the user is authenticated
      if (res.access_token) {
        await supabase.auth.setSession({
          access_token: res.access_token,
          refresh_token: '',
        });
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong. Please try again.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [isValid, isSubmitting, pseudonym, avatar, sex, password, setUser]);

  /* ── Recovery phrase screen ─── */
  if (recoveryPhrase) {
    return (
      <RecoveryPhrase
        phrase={recoveryPhrase}
        onContinue={() => {
          onClose();
          router.push('/chat');
        }}
      />
    );
  }

  /* ── Signup sheet ─── */
  return (
    <>
      {/* Warm overlay */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-40"
        style={{ backgroundColor: 'rgba(42, 36, 51, 0.4)' }}
        onClick={onClose}
      />

      {/* Bottom sheet */}
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        drag="y"
        dragConstraints={{ top: 0 }}
        dragElastic={0.1}
        onDragEnd={(_, info) => {
          if (info.offset.y > 120) onClose();
        }}
        className="fixed bottom-0 left-0 right-0 z-50 bg-canvas-elevated rounded-t-3xl safe-area-bottom"
        style={{
          maxHeight: '92dvh',
          boxShadow: '0 -8px 24px rgba(42, 36, 51, 0.12)',
        }}
      >
        <div className="overflow-y-auto px-6 pb-8 pt-2" style={{ maxHeight: '90dvh' }}>
          {/* Drag handle */}
          <div className="flex justify-center pt-1 pb-4">
            <div className="w-10 h-1 rounded-full bg-border-default" />
          </div>

          {/* Avatar + Pseudonym row */}
          <div className="flex items-center gap-3 mb-5">
            <div
              className="w-[52px] h-[52px] rounded-full bg-brand-primary-bg flex items-center justify-center text-2xl shrink-0"
            >
              {avatar}
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-base font-medium text-text-primary">
                {pseudonym}
              </span>
              <button
                onClick={handleRegenerate}
                className="text-xs text-brand-primary font-medium self-start hover:underline underline-offset-2"
              >
                new
              </button>
            </div>
          </div>

          {/* Avatar selection (horizontal scroll) */}
          <div className="mb-5">
            <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-none">
              {AVATARS.map((a) => (
                <button
                  key={a}
                  onClick={() => setAvatar(a)}
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-lg shrink-0 transition-all ${
                    avatar === a
                      ? 'bg-brand-primary-bg border-2 border-brand-primary scale-110'
                      : 'bg-canvas-sunken border border-border-default hover:border-brand-primary/30'
                  }`}
                  style={{
                    transition: 'transform 150ms var(--ease-spring, ease), border-color 150ms ease',
                  }}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>

          {/* Sex toggle + Password field (side by side on wider screens, stacked on narrow) */}
          <div className="flex gap-3 mb-5">
            {/* Sex toggle */}
            <div className="flex rounded-xl border border-border-default overflow-hidden shrink-0">
              {(['F', 'M'] as Sex[]).map((s) => (
                <button
                  key={s}
                  onClick={() => setSex(s)}
                  className={`px-5 py-2.5 text-sm font-medium transition-colors ${
                    sex === s
                      ? 'bg-brand-primary text-white'
                      : 'bg-canvas-elevated text-text-secondary hover:bg-canvas-sunken'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Password field */}
            <div className="flex-1 relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password (8+ chars)"
                className="w-full px-4 py-2.5 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-primary transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary text-xs hover:text-text-secondary"
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          {/* Error message */}
          {error && (
            <p className="text-error text-xs mb-3 text-center">{error}</p>
          )}

          {/* Submit button */}
          <button
            onClick={handleSubmit}
            disabled={!isValid || isSubmitting}
            className={`w-full py-3.5 rounded-full text-sm font-medium transition-all ${
              isValid && !isSubmitting
                ? 'bg-brand-primary text-white active:scale-[0.97]'
                : 'bg-canvas-sunken text-text-tertiary cursor-not-allowed'
            }`}
          >
            {isSubmitting ? 'Creating...' : 'Create my account'}
          </button>

          {/* Caption */}
          <p className="text-center text-xs text-text-tertiary mt-3">
            Anonymous ·{' '}
            <a href="/terms" className="underline underline-offset-2">
              Terms
            </a>{' '}
            &amp;{' '}
            <a href="/privacy" className="underline underline-offset-2">
              Privacy
            </a>
          </p>

          {/* Switch to login */}
          <p className="text-center text-xs text-text-tertiary mt-4">
            Already have an account?{' '}
            <button
              onClick={onSwitchToLogin}
              className="text-brand-primary font-medium hover:underline underline-offset-2"
            >
              Log in
            </button>
          </p>
        </div>
      </motion.div>
    </>
  );
}
