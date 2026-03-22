'use client';

import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

interface RecoveryPhraseProps {
  phrase: string;
  onContinue: () => void;
}

export default function RecoveryPhrase({ phrase, onContinue }: RecoveryPhraseProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(phrase);
      setCopied(true);
      toast.success('Copied ✓');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = phrase;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      toast.success('Copied ✓');
      setTimeout(() => setCopied(false), 2000);
    }
  }, [phrase]);

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
      />

      {/* Bottom sheet */}
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 28, stiffness: 300 }}
        className="fixed bottom-0 left-0 right-0 z-50 bg-canvas-elevated rounded-t-3xl safe-area-bottom"
        style={{
          boxShadow: '0 -8px 24px rgba(42, 36, 51, 0.12)',
        }}
      >
        <div className="px-6 pb-8 pt-2">
          {/* Drag handle */}
          <div className="flex justify-center pt-1 pb-6">
            <div className="w-10 h-1 rounded-full bg-border-default" />
          </div>

          {/* Key emoji */}
          <div className="text-center mb-4">
            <span className="text-4xl">🔑</span>
          </div>

          {/* Header */}
          <h2 className="text-xl font-serif text-text-primary text-center mb-2">
            Save your recovery phrase
          </h2>

          {/* Explanation */}
          <p className="text-sm text-text-secondary text-center mb-6 leading-relaxed px-2">
            This phrase is the only way to recover your anonymous account.
            Write it down or save it somewhere safe. We cannot recover it for you.
          </p>

          {/* Phrase box */}
          <div className="border border-border-default rounded-xl p-4 mb-4 bg-canvas-sunken">
            <p className="text-center font-mono text-base tracking-[0.15em] text-text-primary select-all">
              {phrase}
            </p>
          </div>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="w-full py-3 rounded-xl border border-border-default text-sm font-medium text-text-secondary hover:bg-canvas-sunken transition-colors mb-4"
          >
            {copied ? 'Copied ✓' : 'Copy to clipboard'}
          </button>

          {/* Continue button */}
          <button
            onClick={onContinue}
            className="w-full py-3.5 rounded-full bg-brand-primary text-white text-sm font-medium active:scale-[0.97] transition-transform"
          >
            I&apos;ve saved it — continue
          </button>
        </div>
      </motion.div>
    </>
  );
}
