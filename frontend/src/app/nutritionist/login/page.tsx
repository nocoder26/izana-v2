'use client';

import { useState, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

export default function NutritionistLoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/nutritionist/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(body || 'Invalid credentials');
      }

      const data = await res.json();
      sessionStorage.setItem('nutritionist_jwt', data.token ?? data.access_token ?? '');
      window.location.href = '/nutritionist/queue';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-dvh bg-canvas-base px-6" style={{ minHeight: '100vh' }}>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="izana-avatar w-12 h-12 mb-4" />
          <h1 className="text-2xl font-semibold text-text-primary font-serif">Izana</h1>
          <p className="text-sm text-text-secondary mt-1">Nutritionist Portal</p>
        </div>

        {/* Form card */}
        <div
          className={cn(
            'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
            'shadow-[0_1px_3px_rgba(42,36,51,0.04)]',
            'p-6',
          )}
        >
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="Email"
              type="email"
              placeholder="name@clinic.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />

            <Input
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              showPasswordToggle
              required
              autoComplete="current-password"
            />

            {error && (
              <p className="text-xs text-error" role="alert">
                {error}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={loading}
              className="w-full mt-2"
            >
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-text-tertiary mt-6">
          Protected portal. Contact admin for access.
        </p>
      </motion.div>
    </div>
  );
}
