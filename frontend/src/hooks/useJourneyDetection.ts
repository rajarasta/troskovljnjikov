import { useEffect, useRef } from 'react';
import { useJourneyStore } from '../stores/journeyStore';
import { useBoQStore } from '../stores/boqStore';
import { useAgentStore } from '../stores/agentStore';
import { getCurrentStep } from '../components/onboarding/journeyConfig';

/**
 * Hook that detects user actions for journey action steps.
 * Watches store changes and automatically advances journey when actions are detected.
 */
export function useJourneyDetection() {
  const isActive = useJourneyStore((s) => s.isActive);
  const currentChapter = useJourneyStore((s) => s.currentChapter);
  const currentStep = useJourneyStore((s) => s.currentStep);
  const nextStep = useJourneyStore((s) => s.nextStep);
  const setHasUploadedFile = useJourneyStore((s) => s.setHasUploadedFile);
  const setHasSelectedUnit = useJourneyStore((s) => s.setHasSelectedUnit);
  const setHasAcceptedOrRejected = useJourneyStore((s) => s.setHasAcceptedOrRejected);

  const step = getCurrentStep(currentChapter, currentStep);

  // Track previous boq state to detect new file uploads
  const prevBoqRef = useRef<string | null>(null);

  // Detect file upload (Chapter 2)
  useEffect(() => {
    if (!isActive || step?.type !== 'action' || step?.id !== 'upload-action') return;

    const { selectedFileId, items } = useBoQStore.getState();
    if (selectedFileId !== null && items.length > 0) {
      setHasUploadedFile(true);
      nextStep();
    }
  }, [isActive, step?.id, step?.type, nextStep, setHasUploadedFile]);

  // Detect unit selection (Chapter 4)
  useEffect(() => {
    if (!isActive || step?.type !== 'action' || step?.id !== 'request-ai-action') return;

    const { selectedRow } = useBoQStore.getState();
    const { events } = useAgentStore.getState();

    // Check if user has selected a row and there are agent events
    if (selectedRow !== null && events.length > 0) {
      setHasSelectedUnit(true);
      nextStep();
    }
  }, [isActive, step?.id, step?.type, nextStep, setHasSelectedUnit]);

  // Detect accept/reject action (Chapter 6)
  useEffect(() => {
    if (!isActive || step?.type !== 'action' || step?.id !== 'accept-edit-action') return;

    const { workingItems, items } = useBoQStore.getState();
    // Check if any working items have been modified (different from original)
    const hasChanges = workingItems.some((wItem, idx) => {
      const original = items[idx];
      return original && (
        wItem.quantity !== original.quantity ||
        wItem.unit_price !== original.unit_price ||
        wItem.total !== original.total
      );
    });

    if (hasChanges) {
      setHasAcceptedOrRejected(true);
      nextStep();
    }
  }, [isActive, step?.id, step?.type, nextStep, setHasAcceptedOrRejected]);

  // Detect mid-journey file upload (pause and ask user)
  useEffect(() => {
    if (!isActive || currentChapter < 3) return; // Only check after upload chapter

    const { selectedFileId } = useBoQStore.getState();

    if (prevBoqRef.current && selectedFileId && prevBoqRef.current !== selectedFileId) {
      // New file uploaded mid-journey
      // In a real app, we'd show a modal here. For now, just log it.
      console.log('New file uploaded mid-journey - TODO: show pause modal');
    }

    prevBoqRef.current = selectedFileId;
  }, [isActive, currentChapter]);
}
