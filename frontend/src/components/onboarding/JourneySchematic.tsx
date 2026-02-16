import { Suspense } from 'react';
import { useJourneyStore } from '../../stores/journeyStore';
import { getCurrentStep } from './journeyConfig';

export function JourneySchematic() {
  const isActive = useJourneyStore((s) => s.isActive);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const currentStep = useJourneyStore((s) => s.currentStep);

  const step = getCurrentStep(currentChapter, currentStep);

  if (!isActive || step?.type !== 'schematic' || !step?.schematicComponent) {
    return null;
  }

  const SchematicComponent = step.schematicComponent;

  return (
    <div className="fixed inset-0 bg-black/50 z-[75] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto">
        <div className="p-8">
          {step.title && <h2 className="text-2xl font-bold text-gray-900 mb-2">{step.title}</h2>}
          {step.description && <p className="text-gray-600 mb-6">{step.description}</p>}

          <Suspense fallback={<div className="h-64 bg-gray-100 rounded-lg animate-pulse" />}>
            <SchematicComponent />
          </Suspense>

          <p className="text-xs text-gray-500 text-center mt-6">
            Pritisnite bilo gdje ili čekajte da se nastavi...
          </p>
        </div>
      </div>
    </div>
  );
}
