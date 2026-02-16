import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface JourneyState {
  // Core state
  isActive: boolean;
  showWelcome: boolean;
  showCelebration: boolean;
  currentChapter: number;
  currentStep: number;
  hasCompletedJourney: boolean;

  // Action detection flags (for Chapters 2, 4, 6)
  hasUploadedFile: boolean;
  hasSelectedUnit: boolean;
  hasAcceptedOrRejected: boolean;

  // Pause state (for mid-journey upload edge case)
  isPaused: boolean;
  pauseReason: string | null;

  // Actions
  startJourney: () => void;
  nextStep: () => void;
  prevStep: () => void;
  skipJourney: () => void;
  completeJourney: () => void;
  pauseJourney: (reason: string) => void;
  resumeJourney: () => void;
  restartJourney: () => void;

  // Detection setters (called by useJourneyDetection hook)
  setHasUploadedFile: (value: boolean) => void;
  setHasSelectedUnit: (value: boolean) => void;
  setHasAcceptedOrRejected: (value: boolean) => void;
}

export const useJourneyStore = create<JourneyState>()(
  persist(
    (set, get) => ({
      // Initial state
      isActive: false,
      showWelcome: true,
      showCelebration: false,
      currentChapter: 0,
      currentStep: 0,
      hasCompletedJourney: false,
      hasUploadedFile: false,
      hasSelectedUnit: false,
      hasAcceptedOrRejected: false,
      isPaused: false,
      pauseReason: null,

      // Actions
      startJourney: () =>
        set({
          isActive: true,
          showWelcome: false,
          currentChapter: 0,
          currentStep: 0,
        }),

      nextStep: () => {
        set((state) => ({
          currentStep: state.currentStep + 1,
        }));
      },

      prevStep: () => {
        const { currentStep } = get();
        if (currentStep > 0) {
          set({ currentStep: currentStep - 1 });
        }
      },

      skipJourney: () => {
        set({
          isActive: false,
          showWelcome: false,
          hasCompletedJourney: false,
        });
      },

      completeJourney: () => {
        set({
          isActive: false,
          showCelebration: true,
          hasCompletedJourney: true,
        });
      },

      pauseJourney: (reason: string) => {
        set({
          isPaused: true,
          pauseReason: reason,
        });
      },

      resumeJourney: () => {
        set({
          isPaused: false,
          pauseReason: null,
        });
      },

      restartJourney: () => {
        set({
          isActive: true,
          showWelcome: false,
          showCelebration: false,
          currentChapter: 0,
          currentStep: 0,
          hasUploadedFile: false,
          hasSelectedUnit: false,
          hasAcceptedOrRejected: false,
          isPaused: false,
          pauseReason: null,
          hasCompletedJourney: false,
        });
      },

      // Detection setters
      setHasUploadedFile: (value: boolean) => {
        set({ hasUploadedFile: value });
      },

      setHasSelectedUnit: (value: boolean) => {
        set({ hasSelectedUnit: value });
      },

      setHasAcceptedOrRejected: (value: boolean) => {
        set({ hasAcceptedOrRejected: value });
      },
    }),
    {
      name: 'boq-journey-state',
      partialize: (state) => ({
        hasCompletedJourney: state.hasCompletedJourney,
        currentChapter: state.currentChapter,
        currentStep: state.currentStep,
      }),
    }
  )
);
