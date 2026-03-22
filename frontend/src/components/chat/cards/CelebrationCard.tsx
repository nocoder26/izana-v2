'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import { cn } from '@/lib/utils';
import type { CelebrationCardData } from '../types';

interface CelebrationCardProps {
  data: CelebrationCardData;
}

export default function CelebrationCard({ data }: CelebrationCardProps) {
  useEffect(() => {
    confetti({
      particleCount: 80,
      spread: 70,
      colors: ['#4A3D8F', '#C4956A', '#E8DFF0'],
      origin: { y: 0.6 },
    });
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.4,
        ease: 'easeOut',
      }}
      className={cn(
        'rounded-[14px] border-[0.5px] border-border-default bg-canvas-elevated',
        'shadow-[0_1px_3px_rgba(42,36,51,0.04)] overflow-hidden',
        'text-center',
      )}
    >
      <div className="px-6 py-8 bg-gradient-to-br from-brand-primary/5 to-brand-accent/5">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{
            type: 'spring',
            stiffness: 300,
            damping: 15,
            delay: 0.2,
          }}
          className="text-4xl mb-3"
        >
          🎉
        </motion.div>
        <h3 className="text-lg font-semibold text-text-primary mb-1">
          {data.title}
        </h3>
        {data.subtitle && (
          <p className="text-sm text-text-secondary">{data.subtitle}</p>
        )}
      </div>
    </motion.div>
  );
}
