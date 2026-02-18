/**
 * Request queue to serialize API calls and prevent overwhelming the server.
 * Requests are queued and executed one at a time with timeout protection.
 */

interface QueuedRequest {
  id: string;
  execute: () => Promise<void>;
  timeout: number; // in milliseconds
  addedAt: number; // timestamp when request was queued
}

/**
 * TimeoutError - thrown when a request exceeds its timeout
 */
class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TimeoutError";
  }
}

class RequestQueue {
  private queue: QueuedRequest[] = [];
  private isProcessing = false;
  private maxConcurrent = 2; // Allow up to 2 concurrent requests
  private defaultTimeout = 30000; // 30 seconds default timeout

  /**
   * Enqueue a request with optional timeout
   * @param id - Unique request identifier
   * @param execute - Function that returns a promise to execute
   * @param timeout - Request timeout in milliseconds (default: 30000ms)
   */
  async enqueue(
    id: string,
    execute: () => Promise<void>,
    timeout: number = this.defaultTimeout
  ): Promise<void> {
    this.queue.push({
      id,
      execute,
      timeout,
      addedAt: Date.now(),
    });
    this.process();
  }

  /**
   * Execute a promise with a timeout
   */
  private executeWithTimeout(
    promise: Promise<void>,
    timeoutMs: number,
    requestId: string
  ): Promise<void> {
    return Promise.race([
      promise,
      new Promise<void>((_, reject) =>
        setTimeout(
          () => reject(new TimeoutError(`Request ${requestId} exceeded timeout of ${timeoutMs}ms`)),
          timeoutMs
        )
      ),
    ]);
  }

  private async process(): Promise<void> {
    if (this.isProcessing) return;
    this.isProcessing = true;

    while (this.queue.length > 0) {
      const batch = this.queue.splice(0, this.maxConcurrent);

      try {
        // Execute up to maxConcurrent requests in parallel with timeout protection
        await Promise.all(
          batch.map(async (req) => {
            const queueWaitTime = Date.now() - req.addedAt;
            const remainingTimeout = Math.max(1000, req.timeout - queueWaitTime);

            try {
              await this.executeWithTimeout(
                req.execute(),
                remainingTimeout,
                req.id
              );
            } catch (err) {
              if (err instanceof TimeoutError) {
                console.error(`Request ${req.id} timed out:`, err.message);
              } else {
                console.error(`Request ${req.id} failed:`, err);
              }
              // Continue with next request instead of failing the whole batch
            }
          })
        );
      } catch (err) {
        console.error("Queue processing error:", err);
      }

      // Small delay between batches to prevent API spikes
      if (this.queue.length > 0) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }

    this.isProcessing = false;
  }

  getQueueSize(): number {
    return this.queue.length;
  }

  /**
   * Clear all pending requests from the queue
   */
  clear(): void {
    this.queue = [];
  }

  /**
   * Set the default timeout for new requests
   */
  setDefaultTimeout(timeoutMs: number): void {
    this.defaultTimeout = timeoutMs;
  }
}

export const requestQueue = new RequestQueue();
