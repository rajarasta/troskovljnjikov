import { motion } from 'framer-motion';
import {
  Upload,
  LayoutGrid,
  Zap,
  Database,
  Check,
  ArrowRight,
} from 'lucide-react';

export function ArchitectureSchematic() {
  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.5,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6 } },
  };

  const pulseVariants = {
    hidden: { scale: 1, opacity: 1 },
    pulse: {
      scale: 1.1,
      opacity: 0.8,
      transition: { duration: 0.8, repeat: 2 },
    },
  };

  return (
    <motion.div
      className="flex flex-col gap-8"
      variants={containerVariants}
      initial="hidden"
      animate="show"
    >
      {/* Toolbar */}
      <motion.div variants={itemVariants} className="bg-gray-100 rounded-lg p-4 flex items-center gap-4">
        <Upload size={24} className="text-blue-600" />
        <span className="font-medium text-gray-900">Učitaj Excel</span>
        <span className="ml-auto text-xs text-gray-600">ili Import Historic</span>
      </motion.div>

      {/* Main layout: 4 panels */}
      <motion.div variants={itemVariants} className="grid grid-cols-4 gap-3">
        {/* Left AI panel */}
        <div className="bg-gradient-to-b from-purple-100 to-purple-50 rounded-lg p-4 border border-purple-200">
          <div className="flex items-center gap-2 mb-2">
            <Zap size={16} className="text-purple-600" />
            <span className="text-xs font-semibold text-purple-900">AI Analiza</span>
          </div>
          <motion.div variants={pulseVariants} animate="pulse" className="space-y-1">
            <div className="h-2 bg-purple-300 rounded w-3/4" />
            <div className="h-2 bg-purple-300 rounded w-5/6" />
            <div className="h-2 bg-purple-300 rounded w-2/3" />
          </motion.div>
        </div>

        {/* Left Historic panel */}
        <div className="bg-gradient-to-b from-amber-100 to-amber-50 rounded-lg p-4 border border-amber-200">
          <div className="flex items-center gap-2 mb-2">
            <Database size={16} className="text-amber-600" />
            <span className="text-xs font-semibold text-amber-900">Historijski</span>
          </div>
          <motion.div variants={pulseVariants} animate="pulse" className="space-y-1">
            <div className="h-2 bg-amber-300 rounded w-full" />
            <div className="h-2 bg-amber-300 rounded w-5/6" />
          </motion.div>
        </div>

        {/* Middle carousel panel */}
        <div className="bg-gradient-to-b from-blue-100 to-blue-50 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <LayoutGrid size={16} className="text-blue-600" />
            <span className="text-xs font-semibold text-blue-900">Stavke</span>
          </div>
          <motion.div
            className="bg-white rounded border border-blue-300 p-2 text-center"
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 1, repeat: 2, delay: 2 }}
          >
            <span className="text-xs font-medium text-blue-900">Stavka 1</span>
          </motion.div>
        </div>

        {/* Right output panel */}
        <div className="bg-gradient-to-b from-green-100 to-green-50 rounded-lg p-4 border border-green-200">
          <div className="flex items-center gap-2 mb-2">
            <Check size={16} className="text-green-600" />
            <span className="text-xs font-semibold text-green-900">Output</span>
          </div>
          <motion.div variants={pulseVariants} animate="pulse" className="space-y-1">
            <div className="h-2 bg-green-300 rounded w-4/5" />
            <div className="h-2 bg-green-300 rounded w-3/4" />
          </motion.div>
        </div>
      </motion.div>

      {/* Flow arrows */}
      <motion.div className="relative h-12">
        {/* Upload → Middle */}
        <motion.div
          className="absolute inset-0 flex items-center justify-between px-4"
          variants={itemVariants}
        >
          <div className="flex-1 h-0.5 bg-gradient-to-r from-transparent via-indigo-400 to-transparent" />
          <ArrowRight size={20} className="text-indigo-600 -mx-2" />
          <div className="flex-1 h-0.5 bg-gradient-to-r from-transparent via-indigo-400 to-transparent" />
        </motion.div>
      </motion.div>

      {/* Data flow description */}
      <motion.div
        variants={itemVariants}
        className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 text-sm text-indigo-900"
      >
        <p className="font-medium mb-2">🔄 Kako radi:</p>
        <ol className="space-y-1 text-xs">
          <li>1. Učitajte Excel datoteku s troškovnikom</li>
          <li>2. Odaberite stavku iz srednje ploče</li>
          <li>3. AI analizira stavku (ljevostrana ploča)</li>
          <li>4. Traži sličnu stavku u povijesti (lijevo-donja ploča)</li>
          <li>5. Predlaže cijenu (desna ploča)</li>
          <li>6. Vi prihvatite ili odbijete sugestiju</li>
        </ol>
      </motion.div>

      {/* Call to action */}
      <motion.div variants={itemVariants} className="text-center">
        <p className="text-gray-600 text-sm">
          Sada ćemo proći kroz svaki korak detaljno.
        </p>
      </motion.div>
    </motion.div>
  );
}
