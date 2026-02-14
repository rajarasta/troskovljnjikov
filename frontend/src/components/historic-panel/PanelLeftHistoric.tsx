import { useAgentStore } from '../../stores/agentStore';

export function PanelLeftHistoric() {
  const matches = useAgentStore((s) => s.historicMatches);

  return (
    <div className="p-3">
      <h3 className="text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        Historijski podaci
      </h3>
      {matches.length === 0 ? (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Nema pronađenih historijskih stavki
        </p>
      ) : (
        <div className="space-y-3">
          {matches.map((match, i) => (
            <div
              key={i}
              className="rounded-lg p-2"
              style={{ background: 'var(--accent-dim)', border: '1px solid var(--panel-border)' }}
            >
              <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                {match.title}
              </p>
              <p className="text-[10px] mb-2" style={{ color: 'var(--text-muted)' }}>
                {match.project_name} — {match.item_number}
              </p>
              {match.priced_lines.map((pl, j) => (
                <div key={j} className="flex justify-between text-[10px] py-0.5">
                  <span style={{ color: 'var(--text-secondary)' }}>
                    {pl.unit_of_measure}
                  </span>
                  <span style={{ color: pl.unit_price ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {pl.unit_price != null ? `${pl.unit_price.toFixed(2)} EUR` : '—'}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
