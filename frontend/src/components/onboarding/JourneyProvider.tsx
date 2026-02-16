import { Suspense, lazy, useEffect } from 'react';
import { useJourneyStore } from '../../stores/journeyStore';
import { getCurrentStep } from './journeyConfig';

// Lazy load all journey components to keep bundle size minimal
const JourneyOverlay = lazy(() => import('./JourneyOverlay').then((m) => ({ default: m.JourneyOverlay })));
const JourneyTooltip = lazy(() => import('./JourneyTooltip').then((m) => ({ default: m.JourneyTooltip })));
const JourneyProgressBar = lazy(() => import('./JourneyProgressBar').then((m) => ({ default: m.JourneyProgressBar })));
const JourneySchematic = lazy(() => import('./JourneySchematic').then((m) => ({ default: m.JourneySchematic })));
const JourneyWelcome = lazy(() => import('./JourneyWelcome').then((m) => ({ default: m.JourneyWelcome })));
const JourneyCelebration = lazy(() => import('./JourneyCelebration').then((m) => ({ default: m.JourneyCelebration })));

export function JourneyProvider({ children }: { children: React.ReactNode }) {
  const isActive = useJourneyStore((s) => s.isActive);
  const showWelcome = useJourneyStore((s) => s.showWelcome);
  const showCelebration = useJourneyStore((s) => s.showCelebration);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const currentStep = useJourneyStore((s) => s.currentStep);
  const completeJourney = useJourneyStore((s) => s.completeJourney);
  const nextStep = useJourneyStore((s) => s.nextStep);

  const step = getCurrentStep(currentChapter, currentStep);

  // Handle navigation step completion
  useEffect(() => {
    if (!isActive || step?.type !== 'navigate') return;

    // Navigate step: just advance to next step (which will be in next chapter)
    const timer = setTimeout(() => {
      nextStep();
    }, (step?.schematicDuration || 500) + 1000); // Wait for schematic + extra time

    return () => clearTimeout(timer);
  }, [isActive, step?.id, step?.type, nextStep]);

  // Handle schematic step completion
  useEffect(() => {
    if (!isActive || step?.type !== 'schematic') return;

    const timer = setTimeout(() => {
      nextStep();
    }, step?.schematicDuration || 8000);

    return () => clearTimeout(timer);
  }, [isActive, step?.id, step?.type, step?.schematicDuration, nextStep]);

  // Check if we've reached the end of the journey
  useEffect(() => {
    if (!isActive || !step) {
      completeJourney();
    }
  }, [isActive, step, completeJourney]);

  const shouldRender = isActive || showWelcome || showCelebration;

  return (
    <>
      {children}
      {shouldRender && (
        <Suspense fallback={null}>
          {showWelcome && !isActive && <JourneyWelcome />}
          {isActive && (
            <>
              <JourneyProgressBar />
              <JourneySchematic />
              <JourneyOverlay />
              <JourneyTooltip />
            </>
          )}
          {showCelebration && <JourneyCelebration />}
        </Suspense>
      )}
    </>
  );
}
