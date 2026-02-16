import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';
import { useJourneyStore } from '../../stores/journeyStore';
import { JOURNEY_CHAPTERS, getCurrentStep } from './journeyConfig';

interface TooltipPosition {
  x: number;
  y: number;
}

interface HoleRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function JourneyTooltip() {
  const isActive = useJourneyStore((s) => s.isActive);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const currentStep = useJourneyStore((s) => s.currentStep);
  const nextStep = useJourneyStore((s) => s.nextStep);
  const prevStep = useJourneyStore((s) => s.prevStep);
  const skipJourney = useJourneyStore((s) => s.skipJourney);

  const step = getCurrentStep(currentChapter, currentStep);
  const chapter = JOURNEY_CHAPTERS[currentChapter];

  const [position, setPosition] = useState<TooltipPosition>({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Calculate hole rect from target element
  const getHoleRect = (): HoleRect | null => {
    if (!step?.targetSelector) return null;
    const el = document.querySelector(step.targetSelector);
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const padding = step?.padding ?? 10;
    return {
      x: rect.left - padding,
      y: rect.top - padding,
      w: rect.width + padding * 2,
      h: rect.height + padding * 2,
    };
  };

  // Calculate tooltip position to avoid overlapping with hole
  const calculatePosition = (holeRect: HoleRect, tooltipWidth: number, tooltipHeight: number): TooltipPosition => {
    const gap = 16; // Gap between tooltip and hole/viewport edge
    const viewportW = window.innerWidth;
    const viewportH = window.innerHeight;
    const margin = 8;

    const candidates = [
      step?.tooltipPosition === 'auto' ? ['bottom', 'top', 'right', 'left'] : [step?.tooltipPosition || 'bottom', 'bottom', 'top', 'right', 'left'],
    ].flat() as string[];

    for (const pos of candidates) {
      let x = 0,
        y = 0;

      switch (pos) {
        case 'bottom':
          x = Math.max(margin, Math.min(holeRect.x + holeRect.w / 2 - tooltipWidth / 2, viewportW - tooltipWidth - margin));
          y = Math.min(holeRect.y + holeRect.h + gap, viewportH - tooltipHeight - margin);
          break;
        case 'top':
          x = Math.max(margin, Math.min(holeRect.x + holeRect.w / 2 - tooltipWidth / 2, viewportW - tooltipWidth - margin));
          y = Math.max(margin, holeRect.y - tooltipHeight - gap);
          break;
        case 'right':
          x = Math.min(holeRect.x + holeRect.w + gap, viewportW - tooltipWidth - margin);
          y = Math.max(margin, Math.min(holeRect.y + holeRect.h / 2 - tooltipHeight / 2, viewportH - tooltipHeight - margin));
          break;
        case 'left':
          x = Math.max(margin, holeRect.x - tooltipWidth - gap);
          y = Math.max(margin, Math.min(holeRect.y + holeRect.h / 2 - tooltipHeight / 2, viewportH - tooltipHeight - margin));
          break;
      }

      // Check if position doesn't overlap with hole
      const overlapsHole =
        x < holeRect.x + holeRect.w + gap &&
        x + tooltipWidth > holeRect.x - gap &&
        y < holeRect.y + holeRect.h + gap &&
        y + tooltipHeight > holeRect.y - gap;

      if (!overlapsHole) {
        return { x, y };
      }
    }

    // Fallback: bottom center
    return {
      x: Math.max(margin, Math.min(holeRect.x + holeRect.w / 2 - tooltipWidth / 2, viewportW - tooltipWidth - margin)),
      y: viewportH - tooltipHeight - margin,
    };
  };

  // Measure tooltip and position it
  useLayoutEffect(() => {
    if (!isActive || !visible || !tooltipRef.current || step?.type === 'schematic' || step?.type === 'navigate') return;

    const hole = getHoleRect();
    if (!hole) return;

    const { width, height } = tooltipRef.current.getBoundingClientRect();
    const newPos = calculatePosition(hole, width, height);
    setPosition(newPos);
  }, [isActive, visible, step?.targetSelector, step?.type, step?.tooltipPosition]);

  // Show/hide tooltip based on step type
  useEffect(() => {
    if (!isActive || !step || step.type === 'schematic' || step.type === 'navigate') {
      setVisible(false);
      return;
    }

    // Small delay to allow element to render
    const timer = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(timer);
  }, [isActive, step?.id]);

  // Keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'Enter') {
        nextStep();
      } else if (e.key === 'ArrowLeft') {
        prevStep();
      } else if (e.key === 'Escape') {
        skipJourney();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, nextStep, prevStep, skipJourney]);

  if (!isActive || !visible || !step || step.type === 'schematic' || step.type === 'navigate') {
    return null;
  }

  const totalSteps = JOURNEY_CHAPTERS.reduce((sum, ch) => sum + ch.steps.length, 0);
  const currentGlobalStep = JOURNEY_CHAPTERS.slice(0, currentChapter).reduce((sum, ch) => sum + ch.steps.length, 0) + currentStep;

  const canGoPrev = currentGlobalStep > 0;
  const canGoNext = currentGlobalStep < totalSteps - 1;

  return (
    <div
      ref={tooltipRef}
      className="fixed bg-white rounded-lg shadow-lg p-4 max-w-xs z-[71]"
      style={{
        left: position.x,
        top: position.y,
        opacity: visible ? 1 : 0,
        transition: 'opacity 300ms ease-in-out',
        pointerEvents: 'auto',
      }}
    >
      {/* Header with chapter and close button */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">{chapter?.title}</span>
        <button
          onClick={skipJourney}
          className="p-1 hover:bg-gray-100 rounded-md transition-colors"
          aria-label="Preskoči turneju"
        >
          <X size={16} className="text-gray-500" />
        </button>
      </div>

      {/* Title */}
      {step.title && <h3 className="font-semibold text-gray-900 mb-1 text-sm">{step.title}</h3>}

      {/* Description */}
      {step.tooltipContent && <p className="text-sm text-gray-700 mb-3 leading-relaxed">{step.tooltipContent}</p>}

      {/* Progress indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <div className="h-1 flex-1 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-600 transition-all"
            style={{ width: `${((currentGlobalStep + 1) / totalSteps) * 100}%` }}
          />
        </div>
        <span>
          {currentGlobalStep + 1}/{totalSteps}
        </span>
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center gap-2 justify-end">
        <button
          onClick={prevStep}
          disabled={!canGoPrev}
          className="p-1 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Prethodni korak"
        >
          <ChevronLeft size={16} className="text-gray-600" />
        </button>

        <button
          onClick={nextStep}
          className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-md hover:bg-indigo-700 transition-colors"
        >
          {canGoNext ? 'Dalje' : 'Završi'}
        </button>

        <button
          onClick={nextStep}
          disabled={!canGoNext}
          className="p-1 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Sljedeći korak"
        >
          <ChevronRight size={16} className="text-gray-600" />
        </button>
      </div>
    </div>
  );
}
