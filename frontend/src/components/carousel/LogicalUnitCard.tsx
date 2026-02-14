import type { LogicalUnit } from '../../api/types';

interface Props {
  unit: LogicalUnit;
  isFocused: boolean;
}

export function LogicalUnitCard({ unit, isFocused }: Props) {
  return (
    <div
      className="rounded-lg p-3 transition-colors"
      style={{
        background: isFocused ? 'var(--accent-dim)' : 'transparent',
        border: `1px solid ${isFocused ? 'var(--accent)' : 'var(--panel-border)'}`,
      }}
    >
      {/* Header: item number + title */}
      <div className="flex items-baseline gap-2 mb-1">
        <span className="text-[10px] font-mono shrink-0" style={{ color: 'var(--accent)' }}>
          {unit.item_number}
        </span>
        <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          {unit.title}
        </span>
      </div>

      {/* Description (collapsed when not focused) */}
      {isFocused && unit.description && (
        <p
          className="text-xs leading-relaxed mt-2 mb-2 max-h-32 overflow-y-auto"
          style={{ color: 'var(--text-secondary)' }}
        >
          {unit.description}
        </p>
      )}

      {/* Priced lines table */}
      {unit.priced_lines.length > 0 && (
        <table className="w-full text-[10px] mt-2">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className="text-left font-normal pb-1">Br.</th>
              <th className="text-left font-normal pb-1">Opis</th>
              <th className="text-right font-normal pb-1">Jed.</th>
              <th className="text-right font-normal pb-1">Kol.</th>
              <th className="text-right font-normal pb-1">Cijena</th>
            </tr>
          </thead>
          <tbody>
            {unit.priced_lines.map((pl) => (
              <tr key={pl.item_number} style={{ color: 'var(--text-secondary)' }}>
                <td className="py-0.5 font-mono">{pl.item_number.split('.').pop()?.replace('.', '') || pl.item_number}</td>
                <td className="py-0.5 truncate max-w-[120px]">{pl.description || '—'}</td>
                <td className="py-0.5 text-right">{pl.unit}</td>
                <td className="py-0.5 text-right">{pl.quantity.toFixed(2)}</td>
                <td className="py-0.5 text-right">
                  {pl.unit_price != null ? `${pl.unit_price.toFixed(2)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
