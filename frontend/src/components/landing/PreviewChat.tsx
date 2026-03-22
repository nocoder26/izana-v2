'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SearchAnimation from '@/components/chat/SearchAnimation';

interface CachedResponse {
  question: string;
  answer: string;
  sources: { title: string }[];
}

const CACHED_RESPONSES: CachedResponse[] = [
  {
    question: 'What foods boost egg quality during IVF?',
    answer:
      'Research suggests several dietary patterns can support egg quality during IVF. The Mediterranean diet, rich in omega-3 fatty acids, antioxidants, and whole grains, has been associated with improved outcomes. Key foods include wild salmon, avocados, berries, leafy greens, and nuts. CoQ10-rich foods like sardines and organ meats may also help support mitochondrial function in eggs. Limiting processed foods, trans fats, and excess sugar is equally important.',
    sources: [
      { title: 'Fertility and Sterility, 2024' },
      { title: 'Human Reproduction, 2023' },
      { title: 'Nutrients Journal, 2023' },
    ],
  },
  {
    question: 'How does stress affect fertility treatment?',
    answer:
      'While stress alone does not cause infertility, research shows it can affect fertility treatment outcomes through several pathways. Elevated cortisol may impact hormonal balance, disrupting ovulation timing and implantation. Studies show that women with lower stress levels during IVF had higher pregnancy rates. Mind-body techniques like yoga, meditation, and acupuncture have shown promising results in reducing treatment-related anxiety and improving outcomes.',
    sources: [
      { title: 'Reproductive Biology & Endocrinology, 2023' },
      { title: 'Journal of Psychosomatic Research, 2024' },
      { title: 'Fertility and Sterility, 2023' },
    ],
  },
  {
    question: 'What supplements should I take during my TWW?',
    answer:
      'During the two-week wait (TWW), continuing your prenatal vitamins is essential. Key supplements backed by research include folic acid (at least 400mcg daily), vitamin D (1000-2000 IU), omega-3 DHA, and CoQ10. Progesterone support as prescribed by your doctor is crucial. Avoid new supplements during this time without consulting your fertility specialist. Stay hydrated, maintain gentle activity, and prioritize sleep quality.',
    sources: [
      { title: 'Cochrane Database of Systematic Reviews, 2023' },
      { title: 'Human Reproduction Update, 2024' },
      { title: 'Journal of Assisted Reproduction, 2023' },
    ],
  },
];

interface PreviewChatProps {
  questionIndex: number;
  onCtaClick: () => void;
}

export default function PreviewChat({
  questionIndex,
  onCtaClick,
}: PreviewChatProps) {
  const [phase, setPhase] = useState<'searching' | 'streaming' | 'complete'>(
    'searching',
  );
  const [streamedText, setStreamedText] = useState('');
  const [showFollowUp, setShowFollowUp] = useState(false);

  const response = CACHED_RESPONSES[questionIndex] ?? CACHED_RESPONSES[0];

  const handleSearchComplete = useCallback(() => {
    setPhase('streaming');
  }, []);

  // Word-by-word streaming
  useEffect(() => {
    if (phase !== 'streaming') return;

    const words = response.answer.split(' ');
    let i = 0;
    let cancelled = false;

    const interval = setInterval(() => {
      if (cancelled || i >= words.length) {
        if (!cancelled) {
          setPhase('complete');
          setTimeout(() => setShowFollowUp(true), 300);
        }
        clearInterval(interval);
        return;
      }
      setStreamedText((prev) => (prev ? prev + ' ' + words[i] : words[i]));
      i++;
    }, 30);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [phase, response.answer]);

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* User question bubble */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="self-end"
      >
        <div className="user-bubble text-sm max-w-[85%]">
          {response.question}
        </div>
      </motion.div>

      {/* Izana response area */}
      <div className="self-start max-w-[92%]">
        <div className="flex items-start gap-2">
          {/* Izana avatar */}
          <div className="izana-avatar flex items-center justify-center" style={{ width: 28, height: 28 }}>
            <span className="text-white text-xs">✦</span>
          </div>

          <div className="flex flex-col gap-1">
            {/* Search animation */}
            {phase === 'searching' && (
              <SearchAnimation
                cached
                sources={response.sources}
                onComplete={handleSearchComplete}
              />
            )}

            {/* Streaming / Complete text */}
            <AnimatePresence>
              {(phase === 'streaming' || phase === 'complete') && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15 }}
                  className="izana-bubble text-sm leading-relaxed"
                >
                  {streamedText}
                  {phase === 'streaming' && (
                    <span className="inline-block w-1.5 h-4 bg-brand-primary/60 ml-0.5 animate-pulse rounded-sm align-text-bottom" />
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Sources */}
            {phase === 'complete' && (
              <motion.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: 0.1 }}
                className="flex flex-wrap gap-1.5 mt-1"
              >
                {response.sources.map((src, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-brand-primary-bg text-brand-primary border border-brand-primary/15"
                  >
                    {src.title}
                  </span>
                ))}
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Follow-up CTA */}
      <AnimatePresence>
        {showFollowUp && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col items-center gap-2 mt-2"
          >
            <p className="text-xs text-text-secondary text-center px-4">
              Want advice personalised to YOUR treatment?
            </p>
            <button
              onClick={onCtaClick}
              className="w-full bg-brand-primary text-white font-medium py-3 px-6 rounded-full text-sm active:scale-[0.97] transition-transform"
            >
              Start my journey
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
