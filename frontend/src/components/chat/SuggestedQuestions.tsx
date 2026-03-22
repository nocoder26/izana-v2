'use client';

import { motion } from 'framer-motion';

interface SuggestedQuestionsProps {
  questions: string[];
  onSelect: (question: string) => void;
}

export default function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  if (!questions.length) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {questions.map((q, i) => (
        <motion.button
          key={i}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: i * 0.1 }}
          onClick={() => onSelect(q)}
          className="px-3.5 py-2 rounded-xl text-sm text-brand-primary
            bg-brand-primary-bg border border-brand-primary/15
            hover:bg-brand-primary hover:text-white
            transition-colors duration-200 cursor-pointer"
        >
          {q}
        </motion.button>
      ))}
    </div>
  );
}
