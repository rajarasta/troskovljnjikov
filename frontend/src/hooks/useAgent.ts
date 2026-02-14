import { useCallback } from 'react';
import { useAgentStore } from '../stores/agentStore';
import { useBoQStore } from '../stores/boqStore';
import type { HistoricMatchEvent, LineSuggestion } from '../api/types';

export function useAgent() {
  const agentStore = useAgentStore();
  const updateOutputLine = useBoQStore((s) => s.updateOutputLine);

  const requestSuggestion = useCallback(
    async (unitId: string) => {
      agentStore.startProcessing(unitId);

      const res = await fetch('/api/agent/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit_id: unitId }),
      });

      if (!res.ok || !res.body) {
        agentStore.finishProcessing();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop()!;

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            switch (currentEvent) {
              case 'reasoning':
                agentStore.appendReasoning(data.text);
                break;
              case 'historic_match':
                agentStore.addHistoricMatch(data as HistoricMatchEvent);
                break;
              case 'suggestion': {
                const s = data as LineSuggestion;
                agentStore.addSuggestion(s);
                updateOutputLine(unitId, s.item_number, {
                  suggestedPrice: s.suggested_price,
                  confidence: s.confidence,
                  agentReasoning: s.reasoning,
                });
                break;
              }
              case 'complete':
                agentStore.finishProcessing();
                break;
            }
          }
        }
      }
    },
    [agentStore, updateOutputLine]
  );

  return { requestSuggestion };
}
