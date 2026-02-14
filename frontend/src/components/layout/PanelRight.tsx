import { useBoQStore } from '../../stores/boqStore';
import { OutputUnitGroup } from '../output-panel/OutputUnitGroup';

export function PanelRight() {
  const parsedBoQ = useBoQStore((s) => s.parsedBoQ);
  const currentIndex = useBoQStore((s) => s.currentUnitIndex);
  const outputData = useBoQStore((s) => s.outputData);

  if (!parsedBoQ) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Output
        </p>
      </div>
    );
  }

  const units = parsedBoQ.units;

  return (
    <div className="p-4">
      <h3 className="text-xs font-semibold mb-3 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        Output — Uređeni podaci
      </h3>
      <div className="space-y-2">
        {units.map((unit, i) => (
          <OutputUnitGroup
            key={unit.id}
            unit={unit}
            outputLines={outputData.get(unit.id) || []}
            isFocused={i === currentIndex}
          />
        ))}
      </div>
    </div>
  );
}
