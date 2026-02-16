import { HelpCircle } from 'lucide-react';
import { useJourneyStore } from '../../stores/journeyStore';

export function HelpButton() {
  const hasCompletedJourney = useJourneyStore((s) => s.hasCompletedJourney);
  const restartJourney = useJourneyStore((s) => s.restartJourney);

  // Only show help button after journey is completed
  if (!hasCompletedJourney) {
    return null;
  }

  return (
    <button
      onClick={restartJourney}
      title="Ponovno pregled turneje"
      className="px-3 py-1 text-xs rounded-md transition-colors hover:bg-gray-100 text-gray-600 hover:text-gray-900"
      aria-label="Pomoć - Ponovno pregled turneje"
    >
      <HelpCircle size={16} />
    </button>
  );
}
