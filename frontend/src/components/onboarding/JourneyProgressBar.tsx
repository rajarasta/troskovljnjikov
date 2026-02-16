import {
  Home,
  Upload,
  LayoutGrid,
  Zap,
  CheckCircle,
  SkipForward,
} from 'lucide-react';
import { useJourneyStore } from '../../stores/journeyStore';
import { JOURNEY_CHAPTERS } from './journeyConfig';

// Map icon names to lucide components
const ICON_MAP: Record<string, React.ComponentType<{ size: number }>> = {
  Home,
  Upload,
  Layout: LayoutGrid,
  Zap,
  CheckCircle,
  SkipForward,
};

export function JourneyProgressBar() {
  const isActive = useJourneyStore((s) => s.isActive);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const skipJourney = useJourneyStore((s) => s.skipJourney);

  if (!isActive) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-[65] shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="flex items-center gap-4">
          {/* Progress indicator */}
          <div className="flex-1">
            <div className="flex gap-2">
              {JOURNEY_CHAPTERS.map((chapter, idx) => {
                const IconComponent = ICON_MAP[chapter.icon] || Home;
                const isComplete = idx < currentChapter;
                const isCurrent = idx === currentChapter;

                return (
                  <div
                    key={chapter.id}
                    className={`flex flex-col items-center gap-1.5 transition-all ${
                      isCurrent ? 'opacity-100' : isComplete ? 'opacity-60' : 'opacity-40'
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                        isComplete
                          ? 'bg-green-100'
                          : isCurrent
                            ? 'bg-indigo-100 ring-2 ring-indigo-400'
                            : 'bg-gray-100'
                      }`}
                    >
                      <div
                        style={{
                          color: isComplete ? '#16a34a' : isCurrent ? '#4f46e5' : '#6b7280',
                        }}
                      >
                        <IconComponent size={16} />
                      </div>
                    </div>
                    <span className="text-xs font-medium text-gray-700 text-center whitespace-nowrap">
                      {chapter.title}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Skip button */}
          <button
            onClick={skipJourney}
            className="text-xs font-medium text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors"
          >
            Preskoči
          </button>
        </div>
      </div>
    </div>
  );
}
