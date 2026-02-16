import { motion } from 'framer-motion';
import { useJourneyStore } from '../../stores/journeyStore';
import { CheckCircle, RotateCcw } from 'lucide-react';

export function JourneyCelebration() {
  const skipJourney = useJourneyStore((s) => s.skipJourney);
  const restartJourney = useJourneyStore((s) => s.restartJourney);

  const containerVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    show: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.6 },
    },
  } as any;


  return (
    <div className="fixed inset-0 bg-black/50 z-[80] flex items-center justify-center p-4">
      <motion.div
        className="bg-white rounded-lg shadow-xl max-w-md w-full"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        <div className="p-8 text-center">
          {/* Celebration icon with animation */}
          <motion.div
            className="mb-6 flex justify-center"
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 0.6, repeat: 3 }}
          >
            <div className="relative">
              <CheckCircle size={64} className="text-green-500" />
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-green-500"
                animate={{ scale: [1, 1.3], opacity: [1, 0] }}
                transition={{ duration: 0.8, repeat: 3 }}
              />
            </div>
          </motion.div>

          {/* Title and subtitle */}
          <motion.h2 className="text-2xl font-bold text-gray-900 mb-2">
            Bravo! 🎉
          </motion.h2>

          <motion.p className="text-gray-600 mb-6">
            Sada ste spremni da koristite Troskovljnjikov aplikaciju kako treba. Razumijete kako funkcionira svaki dio!
          </motion.p>

          {/* Quick tips */}
          <motion.div
            className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left"
            variants={containerVariants}
          >
            <p className="text-sm font-medium text-blue-900 mb-2">💡 Sljedeće korake:</p>
            <ul className="text-xs text-blue-800 space-y-1">
              <li>✓ Nastavite s ostalim stavkama u vašem troškovniku</li>
              <li>✓ Koristite "Scroll Linked" za bolji pregled</li>
              <li>✓ Prebacujte se između stavaka klikanjem</li>
            </ul>
          </motion.div>

          {/* Confetti effect */}
          <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-lg">
            {[...Array(6)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute text-2xl"
                initial={{ x: '50%', y: '100%' }}
                animate={{ x: `${-50 + i * 20}%`, y: '-100%' }}
                transition={{ duration: 2, delay: i * 0.1 }}
                style={{ left: `${50 + i * 10}%` }}
              >
                {'🎉'[0]}
              </motion.div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <button
              onClick={skipJourney}
              className="flex-1 px-4 py-2 text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Završi
            </button>
            <button
              onClick={restartJourney}
              className="flex-1 px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
            >
              <RotateCcw size={16} />
              Ponovno
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
