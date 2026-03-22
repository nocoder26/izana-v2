'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface MoodSelectorProps {
  onSelect: (mood: string) => void;
  disabled?: boolean;
}

const moods = [
  { emoji: '😊', label: 'great' },
  { emoji: '🙂', label: 'good' },
  { emoji: '😐', label: 'okay' },
  { emoji: '😢', label: 'tough' },
];

export default function MoodSelector({ onSelect, disabled = false }: MoodSelectorProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);

  const handleSelect = (mood: string) => {
    if (disabled || selected) return;
    setSelected(mood);
    onSelect(mood);
    setTimeout(() => setCollapsed(true), 300);
  };

  return (
    <AnimatePresence>
      {!collapsed && (
        <motion.div
          initial={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0, marginTop: 0, marginBottom: 0 }}
          transition={{ duration: 0.3, ease: 'easeInOut' }}
          className="overflow-hidden"
        >
          <div className="flex flex-col items-center gap-2 py-3">
            <div className="flex gap-4">
              {moods.map((mood) => (
                <motion.button
                  key={mood.label}
                  onClick={() => handleSelect(mood.label)}
                  disabled={disabled || !!selected}
                  className="text-3xl p-2 rounded-full transition-all focus:outline-none
                    focus-visible:ring-2 focus-visible:ring-brand-primary"
                  animate={
                    selected === mood.label
                      ? { scale: 1.3, opacity: 1 }
                      : selected
                        ? { scale: 1, opacity: 0.3 }
                        : { scale: 1, opacity: 1 }
                  }
                  transition={
                    selected === mood.label
                      ? { type: 'spring', stiffness: 400, damping: 15 }
                      : { duration: 0.2 }
                  }
                  whileHover={!selected ? { scale: 1.15 } : undefined}
                  whileTap={!selected ? { scale: 0.95 } : undefined}
                  aria-label={mood.label}
                >
                  {mood.emoji}
                </motion.button>
              ))}
            </div>
            <span className="text-xs text-text-tertiary">tap how you feel</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
