import { motion } from 'framer-motion';
import {
  CheckCircle,
  Upload,
  MousePointer,
  Zap,
  ThumbsUp,
  Download,
  Circle,
} from 'lucide-react';

export function WorkflowSchematic() {
  const steps = [
    { icon: Upload, label: 'Učitaj datoteku', completed: true },
    { icon: MousePointer, label: 'Odaberi stavku', completed: true },
    { icon: Zap, label: 'AI analiza', completed: true },
    { icon: ThumbsUp, label: 'Prihvati cijenu', completed: true },
    { icon: Download, label: 'Preuzmi rezultate', completed: false },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, scale: 0.8 },
    show: { opacity: 1, scale: 1, transition: { duration: 0.5 } },
  };

  return (
    <motion.div
      className="flex flex-col gap-8"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Progress steps */}
      <div className="flex items-center gap-4">
        {steps.map((step, idx) => (
            <motion.div key={idx} variants={itemVariants} className="flex flex-col items-center gap-2">
              <motion.div
                className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                  step.completed
                    ? 'bg-green-100 text-green-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
                animate={step.completed ? { scale: [1, 1.1, 1] } : {}}
                transition={{ delay: 0.5, duration: 0.6 }}
              >
                {step.completed ? (
                  <CheckCircle size={24} />
                ) : (
                  <Circle size={24} />
                )}
              </motion.div>
              <span className={`text-xs font-medium text-center max-w-[60px] ${
                step.completed ? 'text-gray-900' : 'text-gray-500'
              }`}>
                {step.label}
              </span>
            </motion.div>
          )
        )}
      </div>

      {/* Step descriptions */}
      <motion.div variants={itemVariants} className="space-y-3">
        <motion.div className="bg-green-50 border border-green-200 rounded-lg p-3" variants={itemVariants}>
          <div className="flex gap-2">
            <div style={{ color: '#16a34a' }} className="flex-shrink-0">
              <CheckCircle size={20} />
            </div>
            <div className="text-sm">
              <p className="font-medium text-green-900">Učitaj Excel datoteku</p>
              <p className="text-xs text-green-800">Kliknuli ste na "Upload Excel" i odabrali datoteku</p>
            </div>
          </div>
        </motion.div>

        <motion.div className="bg-green-50 border border-green-200 rounded-lg p-3" variants={itemVariants}>
          <div className="flex gap-2">
            <div style={{ color: '#16a34a' }} className="flex-shrink-0">
              <CheckCircle size={20} />
            </div>
            <div className="text-sm">
              <p className="font-medium text-green-900">Odaberi stavku</p>
              <p className="text-xs text-green-800">Kliknuli ste na stavku u srednjoj ploči</p>
            </div>
          </div>
        </motion.div>

        <motion.div className="bg-green-50 border border-green-200 rounded-lg p-3" variants={itemVariants}>
          <div className="flex gap-2">
            <div style={{ color: '#16a34a' }} className="flex-shrink-0">
              <CheckCircle size={20} />
            </div>
            <div className="text-sm">
              <p className="font-medium text-green-900">AI analiza</p>
              <p className="text-xs text-green-800">Vidjeli ste kako AI analizira stavku i traži sličnu u povijesti</p>
            </div>
          </div>
        </motion.div>

        <motion.div className="bg-green-50 border border-green-200 rounded-lg p-3" variants={itemVariants}>
          <div className="flex gap-2">
            <div style={{ color: '#16a34a' }} className="flex-shrink-0">
              <CheckCircle size={20} />
            </div>
            <div className="text-sm">
              <p className="font-medium text-green-900">Prihvati ili odbij cijenu</p>
              <p className="text-xs text-green-800">Kliknuli ste ✓ ili ✕ za sugestiju</p>
            </div>
          </div>
        </motion.div>

        <motion.div className="bg-blue-50 border border-blue-200 rounded-lg p-3" variants={itemVariants}>
          <div className="flex gap-2">
            <div style={{ color: '#60a5fa' }} className="flex-shrink-0">
              <Circle size={20} />
            </div>
            <div className="text-sm">
              <p className="font-medium text-blue-900">Preuzmi rezultate</p>
              <p className="text-xs text-blue-800">Sljedeće: preuzmi azurirane stavke kao Excel datoteku</p>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Summary */}
      <motion.div variants={itemVariants} className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <p className="text-sm text-indigo-900">
          ✨ <strong>Uspjeh!</strong> Sada razumijete kako funkcionira aplikacija. Možete koristiti istu proceduru za sve stavke u vašem troškovniku.
        </p>
      </motion.div>

      {/* Tips */}
      <motion.div variants={itemVariants} className="space-y-2">
        <p className="text-sm font-medium text-gray-900">💡 Korisni savjeti:</p>
        <ul className="text-xs text-gray-700 space-y-1">
          <li>• Koristite "Scroll Linked" opciju za lakšu usporedbu stavaka</li>
          <li>• Možete odbiti sugestije i ručno unijeti cijenu</li>
          <li>• AI postaje precizniji s više historijskih podataka</li>
        </ul>
      </motion.div>
    </motion.div>
  );
}
