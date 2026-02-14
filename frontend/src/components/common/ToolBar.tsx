import { useRef } from 'react';
import { useBoQStore } from '../../stores/boqStore';
import { useUIStore } from '../../stores/uiStore';
import { uploadExcel, importHistoric } from '../../api/client';

export function ToolBar() {
  const setParsedBoQ = useBoQStore((s) => s.setParsedBoQ);
  const scrollLocked = useUIStore((s) => s.scrollLocked);
  const toggleScrollLock = useUIStore((s) => s.toggleScrollLock);
  const uploadRef = useRef<HTMLInputElement>(null);
  const importRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const boq = await uploadExcel(file);
    setParsedBoQ(boq);
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const result = await importHistoric(file);
    alert(`Imported ${result.imported_count} items to historic database`);
  };

  return (
    <div
      className="flex items-center gap-3 px-4 py-2 shrink-0"
      style={{ borderBottom: '1px solid var(--panel-border)' }}
    >
      <span className="text-sm font-semibold tracking-wide" style={{ color: 'var(--accent)' }}>
        Troskovljnjikov
      </span>

      <div className="flex-1" />

      <button
        onClick={() => uploadRef.current?.click()}
        className="px-3 py-1 text-xs rounded-md transition-colors"
        style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
      >
        Upload Excel
      </button>
      <input ref={uploadRef} type="file" accept=".xlsx" className="hidden" onChange={handleUpload} />

      <button
        onClick={() => importRef.current?.click()}
        className="px-3 py-1 text-xs rounded-md transition-colors"
        style={{ background: 'var(--accent-dim)', color: 'var(--text-secondary)' }}
      >
        Import Historic
      </button>
      <input ref={importRef} type="file" accept=".xlsx" className="hidden" onChange={handleImport} />

      <button
        onClick={toggleScrollLock}
        className="px-3 py-1 text-xs rounded-md"
        style={{
          background: scrollLocked ? 'var(--accent-dim)' : 'transparent',
          color: scrollLocked ? 'var(--accent)' : 'var(--text-muted)',
          border: scrollLocked ? 'none' : '1px solid var(--panel-border)',
        }}
      >
        {scrollLocked ? 'Scroll Linked' : 'Scroll Free'}
      </button>
    </div>
  );
}
