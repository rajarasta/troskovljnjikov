import { useEffect, useMemo, useRef, useState } from 'react';
import { useJourneyStore } from '../../stores/journeyStore';
import { getCurrentStep } from './journeyConfig';

interface HoleRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

// Module-level counter for SVG mask IDs (NOT useId() - breaks url(#id) references)
let maskCounter = 0;

export function JourneyOverlay() {
  const isActive = useJourneyStore((s) => s.isActive);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const currentStep = useJourneyStore((s) => s.currentStep);
  const nextStep = useJourneyStore((s) => s.nextStep);

  const step = getCurrentStep(currentChapter, currentStep);

  const [hole, setHole] = useState<HoleRect>({ x: 0, y: 0, w: 0, h: 0 });
  const [visible, setVisible] = useState(false);
  const [targetMissing, setTargetMissing] = useState(false);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const maskId = useMemo(() => `journey-mask-${++maskCounter}`, []);

  const borderRadius = step?.borderRadius ?? 8;
  const padding = step?.padding ?? 10;

  const updateHolePosition = () => {
    if (!step?.targetSelector) {
      setVisible(false);
      return;
    }

    const el = document.querySelector(step.targetSelector);
    if (!el) {
      setVisible(false);
      return;
    }

    const rect = el.getBoundingClientRect();
    setHole({
      x: rect.left - padding,
      y: rect.top - padding,
      w: rect.width + padding * 2,
      h: rect.height + padding * 2,
    });
    setVisible(true);
    setTargetMissing(false);
  };

  // Try to find element and update hole position
  useEffect(() => {
    if (!step || step.type === 'schematic' || step.type === 'navigate') {
      setVisible(false);
      return;
    }

    let attempt = 0;
    const delays = [0, 100, 300, 600, 1000]; // First attempt immediate, then with backoff

    const tryUpdate = () => {
      if (document.querySelector(step.targetSelector!)) {
        updateHolePosition();
      } else if (attempt < delays.length - 1) {
        attempt++;
        retryRef.current = setTimeout(tryUpdate, delays[attempt]);
      } else {
        // Target not found - show centered tooltip, let user manually advance
        setTargetMissing(true);
        setVisible(true);
        setHole({
          x: window.innerWidth / 2 - 150,
          y: window.innerHeight / 2 - 50,
          w: 300,
          h: 100,
        });
      }
    };

    tryUpdate();

    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [step?.targetSelector, step?.type, step?.padding]);

  // Update hole position on window resize and scroll
  useEffect(() => {
    if (!isActive) return;

    window.addEventListener('resize', updateHolePosition);
    window.addEventListener('scroll', updateHolePosition, true); // capture phase

    const el = step?.targetSelector ? document.querySelector(step.targetSelector) : null;
    if (el) {
      observerRef.current = new ResizeObserver(updateHolePosition);
      observerRef.current.observe(el);
    }

    return () => {
      window.removeEventListener('resize', updateHolePosition);
      window.removeEventListener('scroll', updateHolePosition, true);
      observerRef.current?.disconnect();
    };
  }, [step?.targetSelector, isActive]);

  // Auto-advance for spotlight steps with autoAdvanceAfterMs
  useEffect(() => {
    if (!isActive || step?.type !== 'spotlight' || !step?.autoAdvanceAfterMs) return;

    const timer = setTimeout(() => {
      nextStep();
    }, step.autoAdvanceAfterMs);

    return () => clearTimeout(timer);
  }, [isActive, step?.type, step?.autoAdvanceAfterMs, step?.id, nextStep]);

  if (!isActive || !visible || step?.type === 'schematic' || step?.type === 'navigate') {
    return null;
  }

  const isClickThrough = step?.type === 'action';

  return (
    <div className="fixed inset-0 z-[70] pointer-events-none" style={{ mixBlendMode: 'multiply' }}>
      {/* SVG Mask */}
      <svg className="fixed inset-0 w-full h-full pointer-events-none" style={{ zIndex: 70 }}>
        <defs>
          <mask id={maskId}>
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            {!targetMissing && (
              <rect
                x={hole.x}
                y={hole.y}
                width={hole.w}
                height={hole.h}
                rx={borderRadius}
                fill="black"
                style={{
                  transition: 'all 400ms cubic-bezier(0.16, 1, 0.3, 1)',
                }}
              />
            )}
          </mask>
        </defs>
        {/* Dark overlay with hole */}
        <rect x="0" y="0" width="100%" height="100%" fill="rgba(0, 0, 0, 0.55)" mask={`url(#${maskId})`} />
      </svg>

      {/* Highlight ring around hole */}
      <div
        className="absolute pointer-events-none"
        style={{
          left: hole.x,
          top: hole.y,
          width: hole.w,
          height: hole.h,
          borderRadius,
          transition: 'all 400ms cubic-bezier(0.16, 1, 0.3, 1)',
          border: isClickThrough ? '2px solid rgba(99, 102, 241, 0.6)' : '2px solid rgba(255,255,255,0.2)',
          animation: isClickThrough ? 'pulse 2s ease-in-out infinite' : 'none',
          zIndex: 70,
        }}
      />

      {/* Pulse animation for action steps */}
      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7); }
          50% { box-shadow: 0 0 0 10px rgba(99, 102, 241, 0); }
        }
      `}</style>

      {/* Make spotlight clickable for spotlight steps (dark area is clickable to advance) */}
      {step?.type === 'spotlight' && (
        <div
          className="fixed inset-0 cursor-pointer"
          style={{ zIndex: 69, pointerEvents: 'auto' }}
          onClick={nextStep}
        />
      )}

      {/* Action steps: click-through overlay (dark area is not clickable, real element is) */}
      {step?.type === 'action' && (
        <div
          className="fixed inset-0"
          style={{
            zIndex: 69,
            pointerEvents: 'none', // Allow clicks to pass through to real elements
          }}
        />
      )}
    </div>
  );
}
