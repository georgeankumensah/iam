import type { AuthMessage, AuthMessageType } from "./types";

export class BroadcastService {
  private channel: BroadcastChannel;
  private listeners: Set<(msg: AuthMessage) => void> = new Set();
  readonly tab_id: string;

  constructor(channel_name = "clet:oidc:auth") {
    this.tab_id = crypto.randomUUID();
    this.channel = new BroadcastChannel(channel_name);
    this.channel.onmessage = (event: MessageEvent<AuthMessage>) => {
      if (event.data.tabId !== this.tab_id) {
        this.listeners.forEach((fn) => fn(event.data));
      }
    };
  }

  send(type: AuthMessageType, payload?: unknown): void {
    const msg: AuthMessage = {
      type,
      payload,
      tabId: this.tab_id,
      timestamp: Date.now(),
    };
    this.channel.postMessage(msg);
  }

  subscribe(callback: (msg: AuthMessage) => void): () => void {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  destroy(): void {
    this.channel.close();
    this.listeners.clear();
  }
}
