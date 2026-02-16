import { lazy } from 'react';

export type JourneyStepType = 'schematic' | 'spotlight' | 'action' | 'navigate';
export type TooltipPosition = 'top' | 'bottom' | 'left' | 'right' | 'auto';

export interface JourneyStep {
  id: string;
  type: JourneyStepType;
  title?: string;
  description?: string;

  // For spotlight/action steps
  targetSelector?: string;
  tooltipContent?: string;
  tooltipPosition?: TooltipPosition;
  padding?: number;
  borderRadius?: number;

  // For action detection
  actionType?: 'click' | 'detect';
  skipAfterMs?: number; // Auto-skip if action not detected within N ms

  // For auto-advance spotlight steps
  autoAdvanceAfterMs?: number;

  // For schematic steps
  schematicComponent?: React.LazyExoticComponent<React.ComponentType<unknown>>;
  schematicDuration?: number;
}

export interface JourneyChapter {
  id: string;
  title: string;
  icon: string; // lucide-react icon name
  steps: JourneyStep[];
}

// Lazy load schematics to keep bundle size down
const ArchitectureSchematic = lazy(() =>
  import('./schematics/ArchitectureSchematic').then((m) => ({ default: m.ArchitectureSchematic }))
);
const WorkflowSchematic = lazy(() =>
  import('./schematics/WorkflowSchematic').then((m) => ({ default: m.WorkflowSchematic }))
);

export const JOURNEY_CHAPTERS: JourneyChapter[] = [
  {
    id: 'welcome',
    title: 'Dobrodošlica',
    icon: 'Home',
    steps: [
      {
        id: 'welcome-schematic',
        type: 'schematic',
        title: 'Arhitektura aplikacije',
        description: 'Pogledajte kako aplikacija funkcionira',
        schematicComponent: ArchitectureSchematic,
        schematicDuration: 15000,
      },
    ],
  },

  {
    id: 'upload',
    title: 'Učitavanje',
    icon: 'Upload',
    steps: [
      {
        id: 'upload-button-spotlight',
        type: 'spotlight',
        title: 'Učitajte Excel datoteku',
        targetSelector: '[data-tour="upload-button"]',
        tooltipContent: 'Kliknite ovdje da učitate Excel datoteku s troškovnikom',
        tooltipPosition: 'bottom',
        padding: 8,
      },
      {
        id: 'upload-action',
        type: 'action',
        title: 'Čekam učitavanje datoteke',
        actionType: 'detect',
        skipAfterMs: 60000, // 60 seconds timeout
      },
      {
        id: 'upload-carousel-spotlight',
        type: 'spotlight',
        title: 'Vaš troškovnik je učitan',
        targetSelector: '[data-tour="panel-middle"]',
        tooltipContent: 'Vaš troškovnik je učitan! Ovo su logičke jedinice - stavke s podstavkama (a, b, c...).',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
    ],
  },

  {
    id: 'interface',
    title: 'Sučelje',
    icon: 'Layout',
    steps: [
      {
        id: 'interface-unit-card',
        type: 'spotlight',
        title: 'Logička jedinica',
        targetSelector: '[data-tour="unit-card"][data-tour-index="0"]',
        tooltipContent: 'Svaka kartica predstavlja logičku jedinicu - stavku s naslovom, opisom i podstavkama (a, b, c...).',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 4000,
        padding: 8,
      },
      {
        id: 'interface-ai-panel',
        type: 'spotlight',
        title: 'AI analiza',
        targetSelector: '[data-tour="panel-ai"]',
        tooltipContent: 'Ovdje će se prikazati AI analiza stavke i obrazloženje predloženih cijena.',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
      {
        id: 'interface-historic-panel',
        type: 'spotlight',
        title: 'Historijski podaci',
        targetSelector: '[data-tour="panel-historic"]',
        tooltipContent: 'Ovdje će se prikazati pronađeni historijski podaci sličnih stavki iz prošlih projekata.',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
      {
        id: 'interface-output-panel',
        type: 'spotlight',
        title: 'Predložene cijene',
        targetSelector: '[data-tour="panel-output"]',
        tooltipContent: 'Ovdje ćete vidjeti predložene cijene na temelju historijskih podataka.',
        tooltipPosition: 'left',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
    ],
  },

  {
    id: 'request-ai',
    title: 'AI analiza',
    icon: 'Zap',
    steps: [
      {
        id: 'request-ai-spotlight',
        type: 'spotlight',
        title: 'Odaberite stavku',
        targetSelector: '[data-tour="unit-card"][data-tour-index="0"]',
        tooltipContent: 'Kliknite na stavku da zatražite AI analizu cijena.',
        tooltipPosition: 'right',
        padding: 8,
      },
      {
        id: 'request-ai-action',
        type: 'action',
        title: 'Čekam odabir stavke',
        actionType: 'detect',
        skipAfterMs: 60000,
      },
    ],
  },

  {
    id: 'watch-ai',
    title: 'AI u akciji',
    icon: 'Zap',
    steps: [
      {
        id: 'watch-ai-reasoning',
        type: 'spotlight',
        title: 'Analiza stavke',
        targetSelector: '[data-tour="panel-ai-reasoning"]',
        tooltipContent: 'AI analizira stavku i obrazlaže svoje odluke u realnom vremenu. Primijetite stream teksta koji se pojavljuje.',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
      {
        id: 'watch-ai-historic',
        type: 'spotlight',
        title: 'Pronađeni historijski podaci',
        targetSelector: '[data-tour="panel-historic-matches"]',
        tooltipContent: 'Pronađeni su historijski podaci sličnih stavki iz baze. Svaki redak pokazuje cijenu iz prošlog projekta.',
        tooltipPosition: 'right',
        autoAdvanceAfterMs: 2000,
        padding: 8,
      },
      {
        id: 'watch-ai-output',
        type: 'spotlight',
        title: 'Predložene cijene',
        targetSelector: '[data-tour="output-table"]',
        tooltipContent: 'AI predlaže cijene na temelju pronađenih historijskih podataka. Primijetite animaciju koja pokazuje sugestiju.',
        tooltipPosition: 'left',
        autoAdvanceAfterMs: 2000,
        padding: 8,
      },
    ],
  },

  {
    id: 'accept-edit',
    title: 'Prihvaćanje cijena',
    icon: 'CheckCircle',
    steps: [
      {
        id: 'accept-button-spotlight',
        type: 'spotlight',
        title: 'Prihvati sugestiju',
        targetSelector: '[data-tour="accept-button"]',
        tooltipContent: 'Kliknite ✓ da prihvatite predloženu cijenu.',
        tooltipPosition: 'top',
        autoAdvanceAfterMs: 2000,
        padding: 8,
      },
      {
        id: 'reject-button-spotlight',
        type: 'spotlight',
        title: 'Odbij sugestiju',
        targetSelector: '[data-tour="reject-button"]',
        tooltipContent: 'Kliknite ✕ da odbijete sugestiju.',
        tooltipPosition: 'top',
        autoAdvanceAfterMs: 2000,
        padding: 8,
      },
      {
        id: 'accept-edit-action',
        type: 'action',
        title: 'Čekam da prihvatite ili odbijete cijenu',
        actionType: 'detect',
        skipAfterMs: 60000,
      },
    ],
  },

  {
    id: 'next-steps',
    title: 'Završetak',
    icon: 'CheckCircle',
    steps: [
      {
        id: 'next-steps-schematic',
        type: 'schematic',
        title: 'Sažetak rada',
        description: 'Pogledajte što ste naučili',
        schematicComponent: WorkflowSchematic,
        schematicDuration: 8000,
      },
      {
        id: 'next-steps-scroll-lock',
        type: 'spotlight',
        title: 'Sinkronizacija skrolanja',
        targetSelector: '[data-tour="scroll-lock-toggle"]',
        tooltipContent: 'Koristite ovu opciju za sinkronizaciju skrolanja između srednje i desne ploče. Olakšava uspoređivanje stavaka sa rezultatima.',
        tooltipPosition: 'bottom',
        autoAdvanceAfterMs: 3000,
        padding: 8,
      },
      {
        id: 'next-steps-complete',
        type: 'navigate',
        title: 'Završetak',
      },
    ],
  },
];

// Helper function to get total step count for a chapter
export function getChapterStepCount(chapterId: string): number {
  const chapter = JOURNEY_CHAPTERS.find((c) => c.id === chapterId);
  return chapter?.steps.length ?? 0;
}

// Helper function to get current chapter
export function getCurrentChapter(chapterIndex: number): JourneyChapter | null {
  return JOURNEY_CHAPTERS[chapterIndex] ?? null;
}

// Helper function to get current step
export function getCurrentStep(chapterIndex: number, stepIndex: number): JourneyStep | null {
  const chapter = getCurrentChapter(chapterIndex);
  return chapter?.steps[stepIndex] ?? null;
}

// Calculate global step index from chapter and step
export function getGlobalStepIndex(chapterIndex: number, stepIndex: number): number {
  let globalIndex = 0;
  for (let i = 0; i < chapterIndex; i++) {
    globalIndex += JOURNEY_CHAPTERS[i].steps.length;
  }
  return globalIndex + stepIndex;
}

// Get chapter and step from global step index
export function getChapterAndStepFromGlobal(globalIndex: number): { chapter: number; step: number } {
  let currentIndex = 0;
  for (let chapter = 0; chapter < JOURNEY_CHAPTERS.length; chapter++) {
    const stepCount = JOURNEY_CHAPTERS[chapter].steps.length;
    if (currentIndex + stepCount > globalIndex) {
      return { chapter, step: globalIndex - currentIndex };
    }
    currentIndex += stepCount;
  }
  // Default to last step
  return { chapter: JOURNEY_CHAPTERS.length - 1, step: JOURNEY_CHAPTERS[JOURNEY_CHAPTERS.length - 1].steps.length - 1 };
}
