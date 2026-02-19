import { useCallback, useEffect, useRef, useState } from "react";
import { suggestCompletion } from "@/lib/api";

interface CompletionContext {
  item_number: string | null;
  description: string;
}

interface UseAutoCompleteOptions {
  debounceMs?: number;
  context?: CompletionContext[];
}

export function useAutoComplete({ debounceMs = 500, context = [] }: UseAutoCompleteOptions = {}) {
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const prefixRef = useRef<string>("");
  // Store context as a ref so the request callback doesn't depend on it
  const contextRef = useRef<CompletionContext[]>(context);
  contextRef.current = context;

  // Cleanup on unmount: cancel pending timers and in-flight requests
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (controllerRef.current) controllerRef.current.abort();
    };
  }, []);

  const request = useCallback(
    (prefix: string) => {
      prefixRef.current = prefix;

      // Clear existing timer
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      // Cancel in-flight request
      if (controllerRef.current) {
        controllerRef.current.abort();
        controllerRef.current = null;
      }

      // Clear suggestion while typing
      setSuggestion(null);

      // Don't request for very short prefixes
      if (prefix.trim().length < 3) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);

      timerRef.current = setTimeout(async () => {
        const controller = new AbortController();
        controllerRef.current = controller;

        try {
          const result = await suggestCompletion(prefix, contextRef.current, controller.signal);
          // Guard against stale responses
          if (prefixRef.current === prefix && result.suggestion) {
            setSuggestion(result.suggestion);
          }
        } catch (err) {
          // Ignore abort errors
          if (err instanceof DOMException && err.name === "AbortError") return;
          // Ignore other errors silently — autocomplete is non-critical
        } finally {
          if (prefixRef.current === prefix) {
            setIsLoading(false);
          }
        }
      }, debounceMs);
    },
    [debounceMs],
  );

  const accept = useCallback((): string | null => {
    const s = suggestion;
    setSuggestion(null);
    return s;
  }, [suggestion]);

  const dismiss = useCallback(() => {
    setSuggestion(null);
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
  }, []);

  return { suggestion, isLoading, request, accept, dismiss };
}
