import { useJourneyStore } from '../../stores/journeyStore';
import { Play, X } from 'lucide-react';

export function JourneyWelcome() {
  const startJourney = useJourneyStore((s) => s.startJourney);
  const skipJourney = useJourneyStore((s) => s.skipJourney);

  return (
    <div className="fixed inset-0 bg-black/50 z-[75] flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dobro došli! 👋</h1>
            <p className="text-gray-600 text-sm mt-1">Troskovljnjikov</p>
          </div>
          <button
            onClick={skipJourney}
            className="p-1 hover:bg-gray-100 rounded-md transition-colors"
            aria-label="Preskoči"
          >
            <X size={20} className="text-gray-500" />
          </button>
        </div>

        <p className="text-gray-700 mb-2">
          Ova aplikacija ima neobičnu arhitekturu s nekoliko panela koji rade zajedno da vam pomognu da
          analizirate i ažurirate vaše troškovnike.
        </p>

        <p className="text-gray-700 mb-6">
          Slijedi vas kroz sve korake - od učitavanja Excel datoteke do prihvaćanja predloženih cijena.
        </p>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
          <p className="text-sm text-blue-900">
            💡 <strong>Savjet:</strong> Trebat će vam par minuta. Možete je prekinuti bilo kada.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={skipJourney}
            className="flex-1 px-4 py-2 text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
          >
            Preskoči
          </button>
          <button
            onClick={startJourney}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
          >
            <Play size={16} />
            Započni turneju
          </button>
        </div>
      </div>
    </div>
  );
}
