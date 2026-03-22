'use client';

import { motion } from 'framer-motion';

interface StreamingTextProps {
  text: string;
}

export default function StreamingText({ text }: StreamingTextProps) {
  const words = text.split(' ');

  return (
    <p className="leading-relaxed">
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.15, delay: i * 0.04 }}
          className="inline"
        >
          {word}{' '}
        </motion.span>
      ))}
    </p>
  );
}
