import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface Props {
  value: string;
  isAnimating: boolean;
}

export function TypewriterCell({ value, isAnimating }: Props) {
  const [displayedChars, setDisplayedChars] = useState(isAnimating ? 0 : value.length);

  useEffect(() => {
    if (!isAnimating) {
      setDisplayedChars(value.length);
      return;
    }
    setDisplayedChars(0);
    const interval = setInterval(() => {
      setDisplayedChars((prev) => {
        if (prev >= value.length) {
          clearInterval(interval);
          return prev;
        }
        return prev + 1;
      });
    }, 50);
    return () => clearInterval(interval);
  }, [value, isAnimating]);

  return (
    <span style={{ color: 'var(--accent)' }}>
      {value.slice(0, displayedChars)}
      {displayedChars < value.length && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ repeat: Infinity, duration: 0.5 }}
          style={{ color: 'var(--accent)' }}
        >
          |
        </motion.span>
      )}
    </span>
  );
}
