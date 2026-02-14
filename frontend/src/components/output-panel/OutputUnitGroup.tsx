import { motion } from 'framer-motion';
import type { LogicalUnit, OutputLineState } from '../../api/types';
import { useBoQStore } from '../../stores/boqStore';
import { TypewriterCell } from './TypewriterCell';

interface Props {
  unit: LogicalUnit;
  outputLines: OutputLineState[];
  isFocused: boolean;
}

export function OutputUnitGroup({ unit, outputLines, isFocused }: Props) {
  const updateOutputLine = useBoQStore((s) => s.updateOutputLine);

  const handleAccept = (itemNumber: string, price: number) => {
    updateOutputLine(unit.id, itemNumber, {
      userAccepted: true,
      userEditedPrice: price,
    });
  };

  const handleReject = (itemNumber: string) => {
    updateOutputLine(unit.id, itemNumber, {
      userAccepted: false,
      suggestedPrice: null,
    });
  };

  return (
    <motion.div
      animate={{
        scale: isFocused ? 1 : 0.97,
        opacity: isFocused ? 1 : 0.5,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="rounded-lg p-3"
      style={{
        background: isFocused ? 'var(--accent-dim)' : 'transparent',
        border: `1px solid ${isFocused ? 'var(--accent)' : 'var(--panel-border)'}`,
      }}
    >
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-[10px] font-mono" style={{ color: 'var(--accent)' }}>
          {unit.item_number}
        </span>
        <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          {unit.title}
        </span>
      </div>

      {outputLines.length > 0 ? (
        <table className="w-full text-[10px]">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className="text-left font-normal pb-1">Br.</th>
              <th className="text-right font-normal pb-1">Jed.</th>
              <th className="text-right font-normal pb-1">Kol.</th>
              <th className="text-right font-normal pb-1">Cijena</th>
              <th className="text-right font-normal pb-1 w-16"></th>
            </tr>
          </thead>
          <tbody>
            {outputLines.map((line) => {
              const displayPrice =
                line.userEditedPrice != null
                  ? line.userEditedPrice
                  : line.suggestedPrice;
              const isAISuggested = line.suggestedPrice != null && line.userAccepted == null;

              return (
                <tr key={line.original.item_number} style={{ color: 'var(--text-secondary)' }}>
                  <td className="py-0.5 font-mono">
                    {line.original.item_number.split('.').pop()?.replace('.', '')}
                  </td>
                  <td className="py-0.5 text-right">{line.original.unit}</td>
                  <td className="py-0.5 text-right">{line.original.quantity.toFixed(2)}</td>
                  <td className="py-0.5 text-right">
                    {isAISuggested ? (
                      <TypewriterCell
                        value={`${line.suggestedPrice!.toFixed(2)}`}
                        isAnimating={true}
                      />
                    ) : displayPrice != null ? (
                      <span
                        style={{
                          color: line.userAccepted
                            ? 'var(--success)'
                            : line.userAccepted === false
                            ? 'var(--danger)'
                            : 'var(--text-secondary)',
                        }}
                      >
                        {displayPrice.toFixed(2)}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>—</span>
                    )}
                  </td>
                  <td className="py-0.5 text-right">
                    {isAISuggested && (
                      <div className="flex gap-1 justify-end">
                        <button
                          onClick={() => handleAccept(line.original.item_number, line.suggestedPrice!)}
                          className="w-5 h-5 rounded text-[10px] flex items-center justify-center"
                          style={{ background: 'rgba(34, 197, 94, 0.15)', color: 'var(--success)' }}
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => handleReject(line.original.item_number)}
                          className="w-5 h-5 rounded text-[10px] flex items-center justify-center"
                          style={{ background: 'rgba(239, 68, 68, 0.15)', color: 'var(--danger)' }}
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        // Show original data when no output yet
        <table className="w-full text-[10px]">
          <tbody>
            {unit.priced_lines.map((pl) => (
              <tr key={pl.item_number} style={{ color: 'var(--text-muted)' }}>
                <td className="py-0.5 font-mono">
                  {pl.item_number.split('.').pop()?.replace('.', '')}
                </td>
                <td className="py-0.5 text-right">{pl.unit}</td>
                <td className="py-0.5 text-right">{pl.quantity.toFixed(2)}</td>
                <td className="py-0.5 text-right">
                  {pl.unit_price != null ? pl.unit_price.toFixed(2) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </motion.div>
  );
}
