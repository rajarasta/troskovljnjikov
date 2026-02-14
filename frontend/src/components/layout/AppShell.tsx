import { useScrollSync } from '../../hooks/useScrollSync';
import { useUIStore } from '../../stores/uiStore';
import { PanelLeftAI } from '../ai-panel/PanelLeftAI';
import { PanelLeftHistoric } from '../historic-panel/PanelLeftHistoric';
import { PanelMiddle } from './PanelMiddle';
import { PanelRight } from './PanelRight';
import { ToolBar } from '../common/ToolBar';

export function AppShell() {
  const scrollLocked = useUIStore((s) => s.scrollLocked);

  const leftAIRef = useScrollSync('left', true);
  const leftHistRef = useScrollSync('left', true);
  const middleRef = useScrollSync('middle-right', scrollLocked);
  const rightRef = useScrollSync('middle-right', scrollLocked);

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--glass-bg)', backdropFilter: 'blur(20px)', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
      <ToolBar />
      <div className="flex flex-1 min-h-0 gap-px">
        {/* Left AI panel */}
        <div
          ref={leftAIRef}
          data-scroll-group="left"
          className="w-[180px] overflow-y-auto shrink-0"
          style={{ background: 'var(--panel-bg)', borderRight: '1px solid var(--panel-border)' }}
        >
          <PanelLeftAI />
        </div>

        {/* Left Historic panel */}
        <div
          ref={leftHistRef}
          data-scroll-group="left"
          className="w-[220px] overflow-y-auto shrink-0"
          style={{ background: 'var(--panel-bg)', borderRight: '1px solid var(--panel-border)' }}
        >
          <PanelLeftHistoric />
        </div>

        {/* Middle carousel */}
        <div
          ref={middleRef}
          data-scroll-group="middle-right"
          className="flex-1 overflow-y-auto"
          style={{ background: 'var(--panel-bg)', borderRight: '1px solid var(--panel-border)' }}
        >
          <PanelMiddle />
        </div>

        {/* Right output */}
        <div
          ref={rightRef}
          data-scroll-group="middle-right"
          className="flex-1 overflow-y-auto"
          style={{ background: 'var(--panel-bg)' }}
        >
          <PanelRight />
        </div>
      </div>
    </div>
  );
}
