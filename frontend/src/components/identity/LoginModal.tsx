'use client';

import { useState, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import { supabase } from '@/lib/supabase/client';
import { apiGet } from '@/lib/api-client';
import { useUserStore } from '@/stores/user-store';

/* ── Types ────────────────────────────────────────────────────── */

interface LoginModalProps {
  onClose: () => void;
  onSwitchToSignup: () => void;
}

interface LookupResponse {
  email: string;
  user_id: string;
}

export default function LoginModal({ onClose, onSwitchToSignup }: LoginModalProps) {
  const [pseudonym, setPseudonym] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryPhrase, setRecoveryPhrase] = useState('');
  const [recoveryStatus, setRecoveryStatus] = useState<string | null>(null);

  const setUser = useUserStore((s) => s.setUser);

  const isValid = useMemo(
    () => pseudonym.trim().length > 0 && password.length >= 8,
    [pseudonym, password],
  );

  const handleSubmit = useCallback(async () => {
    if (!isValid || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);

    try {
      // Step 1: Lookup the pseudonym to get the associated email
      const lookup = await apiGet<LookupResponse>(
        `/auth/lookup?pseudonym=${encodeURIComponent(pseudonym.trim())}`,
      );

      // Step 2: Sign in via Supabase with the resolved email
      const { error: authError } = await supabase.auth.signInWithPassword({
        email: lookup.email,
        password,
      });

      if (authError) {
        throw new Error(authError.message);
      }

      setUser({
        userId: lookup.user_id,
        pseudonym: pseudonym.trim(),
        avatar: '🦋', // Will be fetched from profile later
      });

      onClose();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Login failed. Check your pseudonym and password.',
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [isValid, isSubmitting, pseudonym, password, setUser, onClose]);

  const handleRecovery = useCallback(async () => {
    if (!recoveryPhrase.trim()) return;
    setRecoveryStatus(null);

    try {
      await apiGet(
        `/auth/recover?phrase=${encodeURIComponent(recoveryPhrase.trim())}`,
      );
      setRecoveryStatus('Recovery successful! You can now log in with your pseudonym.');
      setShowRecovery(false);
    } catch (err) {
      setRecoveryStatus(
        err instanceof Error ? err.message : 'Recovery failed. Please try again.',
      );
    }
  }, [recoveryPhrase]);

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
          maxHeight: '85dvh',
          boxShadow: '0 -8px 24px rgba(42, 36, 51, 0.12)',
        }}
      >
        <div className="overflow-y-auto px-6 pb-8 pt-2" style={{ maxHeight: '83dvh' }}>
          {/* Drag handle */}
          <div className="flex justify-center pt-1 pb-4">
            <div className="w-10 h-1 rounded-full bg-border-default" />
          </div>

          {!showRecovery ? (
            <>
              {/* Header */}
              <h2 className="text-xl font-serif text-text-primary text-center mb-6">
                Welcome back ✨
              </h2>

              {/* Pseudonym input */}
              <div className="mb-4">
                <input
                  type="text"
                  value={pseudonym}
                  onChange={(e) => setPseudonym(e.target.value)}
                  placeholder="Your pseudonym"
                  autoCapitalize="none"
                  autoCorrect="off"
                  className="w-full px-4 py-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-primary transition-colors"
                />
              </div>

              {/* Password input */}
              <div className="relative mb-5">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full px-4 py-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-brand-primary transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-tertiary text-xs hover:text-text-secondary"
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
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
                {isSubmitting ? 'Signing in...' : 'Welcome back'}
              </button>

              {/* Forgot password */}
              <button
                onClick={() => setShowRecovery(true)}
                className="block mx-auto mt-4 text-xs text-text-tertiary hover:text-brand-primary transition-colors"
              >
                Forgot password?
              </button>

              {/* Switch to signup */}
              <p className="text-center text-xs text-text-tertiary mt-4">
                Don&apos;t have an account?{' '}
                <button
                  onClick={onSwitchToSignup}
                  className="text-brand-primary font-medium hover:underline underline-offset-2"
                >
                  Sign up
                </button>
              </p>
            </>
          ) : (
            <>
              {/* Recovery mode */}
              <h2 className="text-xl font-serif text-text-primary text-center mb-2">
                Account Recovery
              </h2>
              <p className="text-sm text-text-secondary text-center mb-6">
                Enter the recovery phrase you saved when you created your account.
              </p>

              <input
                type="text"
                value={recoveryPhrase}
                onChange={(e) => setRecoveryPhrase(e.target.value)}
                placeholder="XXXX-XXXX-XXXX-XXXX"
                className="w-full px-4 py-3 rounded-xl border border-border-default bg-canvas-elevated text-sm text-text-primary placeholder:text-text-tertiary font-mono text-center tracking-wider focus:outline-none focus:border-brand-primary transition-colors mb-4"
              />

              {recoveryStatus && (
                <p className="text-xs text-text-secondary text-center mb-3">
                  {recoveryStatus}
                </p>
              )}

              <button
                onClick={handleRecovery}
                disabled={!recoveryPhrase.trim()}
                className={`w-full py-3.5 rounded-full text-sm font-medium transition-all ${
                  recoveryPhrase.trim()
                    ? 'bg-brand-primary text-white active:scale-[0.97]'
                    : 'bg-canvas-sunken text-text-tertiary cursor-not-allowed'
                }`}
              >
                Recover account
              </button>

              <button
                onClick={() => setShowRecovery(false)}
                className="block mx-auto mt-4 text-xs text-text-tertiary hover:text-brand-primary transition-colors"
              >
                ← Back to login
              </button>
            </>
          )}
        </div>
      </motion.div>
    </>
  );
}
