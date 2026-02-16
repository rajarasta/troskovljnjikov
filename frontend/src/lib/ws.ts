import type { AgentEvent } from "./types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

type MessageHandler = (event: AgentEvent) => void;

class WSClient {
  private socket: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private retryCount = 0;
  private maxRetries = 5;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  get isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) return;
    if (this.socket?.readyState === WebSocket.CONNECTING) return;

    this.intentionalClose = false;

    try {
      this.socket = new WebSocket(WS_URL);

      this.socket.onopen = () => {
        this.retryCount = 0;
        console.log("[WS] Connected to", WS_URL);
      };

      this.socket.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as AgentEvent;
          this.handlers.forEach((handler) => handler(data));
        } catch (err) {
          console.warn("[WS] Failed to parse message:", err);
        }
      };

      this.socket.onclose = () => {
        console.log("[WS] Connection closed");
        if (!this.intentionalClose) {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (err) => {
        console.error("[WS] Error:", err);
        this.socket?.close();
      };
    } catch (err) {
      console.error("[WS] Failed to create WebSocket:", err);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.intentionalClose = true;
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    this.retryCount = 0;
    this.socket?.close();
    this.socket = null;
  }

  onMessage(handler: MessageHandler): void {
    this.handlers.add(handler);
  }

  offMessage(handler: MessageHandler): void {
    this.handlers.delete(handler);
  }

  private scheduleReconnect(): void {
    if (this.retryCount >= this.maxRetries) {
      console.warn(
        `[WS] Max retries (${this.maxRetries}) reached. Giving up.`
      );
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
    this.retryCount++;

    console.log(
      `[WS] Reconnecting in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})...`
    );

    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      this.connect();
    }, delay);
  }
}

export const wsClient = new WSClient();
