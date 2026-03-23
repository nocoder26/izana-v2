'use client';

import { useState, useCallback, type FormEvent } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import AdminLayout from '@/components/admin/AdminLayout';
import DashboardTab from '@/components/admin/DashboardTab';
import AnalyticsTab from '@/components/admin/AnalyticsTab';
import FeedbackTab from '@/components/admin/FeedbackTab';
import TrainingTab from '@/components/admin/TrainingTab';
import HealthTab from '@/components/admin/HealthTab';
import PromptsTab from '@/components/admin/PromptsTab';
import ContentManagerTab from '@/components/admin/ContentManagerTab';
import PlanQueueTab from '@/components/admin/PlanQueueTab';

/* ── API Helper ────────────────────────────────────────────── */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

function createAdminFetch() {
  return async function adminFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = typeof window !== 'undefined' ? sessionStorage.getItem('admin_jwt') : null;
    const apiKey = typeof window !== 'undefined' ? sessionStorage.getItem('admin_api_key') : null;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> | undefined),
    };

    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json() as Promise<T>;
  };
}

/* ── Page Component ────────────────────────────────────────── */

export default function AdminPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    if (typeof window === 'undefined') return false;
    return !!(sessionStorage.getItem('admin_jwt') || sessionStorage.getItem('admin_api_key'));
  });

  const [email, setEmail] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const apiFetch = useCallback(createAdminFetch(), []);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);

    try {
      // Admin auth uses X-Admin-API-Key header — validate by testing /admin/dashboard
      const res = await fetch(`${API_URL}/admin/dashboard`, {
        headers: { 'X-Admin-API-Key': apiKey },
      });

      if (!res.ok) {
        throw new Error('Invalid API key');
      }

      sessionStorage.setItem('admin_api_key', apiKey);
      setIsAuthenticated(true);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoginLoading(false);
    }
  };

  /* ── Login screen ──────────────────────────────────────── */
  if (!isAuthenticated) {
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
            <p className="text-sm text-text-secondary mt-1">Admin Dashboard</p>
          </div>

          {/* Form card */}
          <div
            className={cn(
              'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
              'shadow-[0_1px_3px_rgba(42,36,51,0.04)]',
              'p-6',
            )}
          >
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <Input
                label="Email"
                type="email"
                placeholder="admin@izana.io"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />

              <Input
                label="API Key"
                type="password"
                placeholder="Enter your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                showPasswordToggle
                required
              />

              {loginError && (
                <p className="text-xs text-error" role="alert">
                  {loginError}
                </p>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={loginLoading}
                className="w-full mt-2"
              >
                Sign in
              </Button>
            </form>
          </div>

          <p className="text-center text-xs text-text-tertiary mt-6">
            Admin access only. Contact engineering for credentials.
          </p>
        </motion.div>
      </div>
    );
  }

  /* ── Authenticated dashboard ───────────────────────────── */
  return (
    <AdminLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'dashboard' && <DashboardTab apiFetch={apiFetch} />}
      {activeTab === 'analytics' && <AnalyticsTab apiFetch={apiFetch} />}
      {activeTab === 'feedback' && <FeedbackTab apiFetch={apiFetch} />}
      {activeTab === 'training' && <TrainingTab apiFetch={apiFetch} />}
      {activeTab === 'health' && <HealthTab apiFetch={apiFetch} />}
      {activeTab === 'prompts' && <PromptsTab apiFetch={apiFetch} />}
      {activeTab === 'content' && <ContentManagerTab apiFetch={apiFetch} />}
      {activeTab === 'plans' && <PlanQueueTab apiFetch={apiFetch} />}
    </AdminLayout>
  );
}
