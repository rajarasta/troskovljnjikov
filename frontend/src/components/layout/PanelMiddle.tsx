import { motion } from 'framer-motion';
import { useBoQStore } from '../../stores/boqStore';
import { useAgent } from '../../hooks/useAgent';
import { LogicalUnitCard } from '../carousel/LogicalUnitCard';

export function PanelMiddle() {
  const parsedBoQ = useBoQStore((s) => s.parsedBoQ);
  const currentIndex = useBoQStore((s) => s.currentUnitIndex);
  const setCurrentUnit = useBoQStore((s) => s.setCurrentUnit);
  const initOutputForUnit = useBoQStore((s) => s.initOutputForUnit);
  const { requestSuggestion } = useAgent();

  if (!parsedBoQ) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Učitajte Excel datoteku
        </p>
      </div>
    );
  }

  const units = parsedBoQ.units;

  const handleSelect = (index: number) => {
    setCurrentUnit(index);
    const unit = units[index];
    initOutputForUnit(unit);
    requestSuggestion(unit.id);
  };

  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold mb-3 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        Stavke — {parsedBoQ.chapter_title}
      </h3>
      <div className="space-y-2">
        {units.map((unit, i) => (
          <motion.div
            key={unit.id}
            animate={{
              scale: i === currentIndex ? 1 : 0.97,
              opacity: i === currentIndex ? 1 : 0.5,
            }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            onClick={() => handleSelect(i)}
            className="cursor-pointer"
          >
            <LogicalUnitCard unit={unit} isFocused={i === currentIndex} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
