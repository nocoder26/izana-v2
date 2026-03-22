'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { apiPost } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

/* ── Types ────────────────────────────────────────────────────── */

interface InviteCode {
  code: string;
  expiresAt: string;
  shareUrl: string;
}

/* ── Component ────────────────────────────────────────────────── */

export default function PartnerInvite() {
  const [inviteCode, setInviteCode] = useState<InviteCode | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateCode = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const data = await apiPost<InviteCode>('/api/v1/partner/invite');
      setInviteCode(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not generate invite code',
      );
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const copyCode = useCallback(async () => {
    if (!inviteCode) return;
    try {
      await navigator.clipboard.writeText(inviteCode.shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = inviteCode.shareUrl;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [inviteCode]);

  const shareViaWhatsApp = useCallback(() => {
    if (!inviteCode) return;
    const text = encodeURIComponent(
      `Join me on Izana Chat as my partner! Use this link to connect: ${inviteCode.shareUrl}`,
    );
    window.open(`https://wa.me/?text=${text}`, '_blank');
  }, [inviteCode]);

  const shareViaSMS = useCallback(() => {
    if (!inviteCode) return;
    const text = encodeURIComponent(
      `Join me on Izana Chat as my partner! Use this link: ${inviteCode.shareUrl}`,
    );
    window.open(`sms:?body=${text}`, '_self');
  }, [inviteCode]);

  const expiresInDays = inviteCode
    ? Math.ceil(
        (new Date(inviteCode.expiresAt).getTime() - Date.now()) /
          (1000 * 60 * 60 * 24),
      )
    : 0;

  return (
    <Card className="mx-auto max-w-md">
      <CardContent className="space-y-5">
        {/* Header */}
        <div className="text-center space-y-2 pt-1">
          <div className="mx-auto w-14 h-14 rounded-full bg-brand-primary-bg flex items-center justify-center">
            <span className="text-2xl" role="img" aria-label="couple">
              💑
            </span>
          </div>
          <h2 className="font-serif text-xl text-text-primary">
            Invite your partner
          </h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            Share your journey with someone who cares. Your partner will see
            what you choose to share — mood, phase, and more — so they can
            support you better.
          </p>
        </div>

        {/* Generate / Show Code */}
        <AnimatePresence mode="wait">
          {!inviteCode ? (
            <motion.div
              key="generate"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                isLoading={isGenerating}
                onClick={generateCode}
              >
                Generate invite code
              </Button>
            </motion.div>
          ) : (
            <motion.div
              key="code"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              {/* Code Display */}
              <div
                className={cn(
                  'rounded-xl border border-border-default bg-canvas-sunken',
                  'px-4 py-3 text-center',
                )}
              >
                <p className="text-xs text-text-tertiary mb-1">Invite code</p>
                <p className="font-mono text-xl font-semibold tracking-[0.2em] text-brand-primary">
                  {inviteCode.code}
                </p>
                <p className="text-xs text-text-tertiary mt-1.5">
                  Expires in {expiresInDays} day{expiresInDays !== 1 ? 's' : ''}
                </p>
              </div>

              {/* Share Options */}
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={shareViaWhatsApp}
                  className={cn(
                    'flex flex-col items-center gap-1.5 py-3 rounded-xl',
                    'border border-border-default bg-canvas-elevated',
                    'hover:bg-canvas-sunken transition-colors',
                    'text-text-secondary hover:text-text-primary',
                  )}
                >
                  <span className="text-lg" role="img" aria-label="WhatsApp">
                    💬
                  </span>
                  <span className="text-xs font-medium">WhatsApp</span>
                </button>
                <button
                  onClick={shareViaSMS}
                  className={cn(
                    'flex flex-col items-center gap-1.5 py-3 rounded-xl',
                    'border border-border-default bg-canvas-elevated',
                    'hover:bg-canvas-sunken transition-colors',
                    'text-text-secondary hover:text-text-primary',
                  )}
                >
                  <span className="text-lg" role="img" aria-label="SMS">
                    📱
                  </span>
                  <span className="text-xs font-medium">SMS</span>
                </button>
                <button
                  onClick={copyCode}
                  className={cn(
                    'flex flex-col items-center gap-1.5 py-3 rounded-xl',
                    'border border-border-default bg-canvas-elevated',
                    'hover:bg-canvas-sunken transition-colors',
                    copied
                      ? 'text-success border-success/30'
                      : 'text-text-secondary hover:text-text-primary',
                  )}
                >
                  <span className="text-lg" role="img" aria-label="copy">
                    {copied ? '✅' : '📋'}
                  </span>
                  <span className="text-xs font-medium">
                    {copied ? 'Copied!' : 'Copy link'}
                  </span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="text-sm text-error text-center"
              role="alert"
            >
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
