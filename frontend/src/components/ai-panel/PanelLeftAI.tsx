import { useAgentStore } from '../../stores/agentStore';

export function PanelLeftAI() {
  const reasoning = useAgentStore((s) => s.reasoning);
  const isProcessing = useAgentStore((s) => s.isProcessing);

  return (
    <div className="p-3">
      <h3 className="text-xs font-semibold mb-2 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        AI Analiza
      </h3>
      {isProcessing && (
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: 'var(--accent)' }} />
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Analiziram...</span>
        </div>
      )}
      {reasoning ? (
        <pre className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {reasoning}
        </pre>
      ) : (
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Odaberite stavku za AI analizu
        </p>
      )}
    </div>
  );
}
