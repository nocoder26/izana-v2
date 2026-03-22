'use client';

import { motion } from 'framer-motion';
import type { Source } from './types';

interface SourcePillsProps {
  sources: Source[];
  onSourceTap?: (source: Source) => void;
}

export default function SourcePills({ sources, onSourceTap }: SourcePillsProps) {
  if (!sources.length) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {sources.map((source, i) => (
        <motion.button
          key={source.id}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2, delay: i * 0.2 }}
          onClick={() => onSourceTap?.(source)}
          className="inline-flex items-center px-2.5 py-1 rounded-full
            bg-brand-primary-bg text-brand-primary border border-brand-primary/15
            hover:opacity-80 transition-opacity cursor-pointer"
          style={{ fontSize: '9px' }}
          title={source.title}
        >
          {source.title}
        </motion.button>
      ))}
    </div>
  );
}
