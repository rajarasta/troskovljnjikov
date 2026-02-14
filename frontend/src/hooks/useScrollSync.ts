import { useRef, useEffect } from 'react';

/**
 * Synchronize scroll position between two (or more) elements in the same group.
 * Returns a ref to attach to the scrollable element.
 */
export function useScrollSync(groupId: string, enabled: boolean) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isSyncing = useRef(false);

  useEffect(() => {
    const el = scrollRef.current;
    if (!enabled || !el) return;

    const handler = () => {
      if (isSyncing.current) return;
      isSyncing.current = true;

      requestAnimationFrame(() => {
        document
          .querySelectorAll<HTMLDivElement>(`[data-scroll-group="${groupId}"]`)
          .forEach((peer) => {
            if (peer !== el) {
              peer.scrollTop = el.scrollTop;
            }
          });
        isSyncing.current = false;
      });
    };

    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  }, [groupId, enabled]);

  return scrollRef;
}
