/**
 * Jurisiva AI - Background Sync Manager
 * Coordinates offline mutations with service worker background sync
 */

import { offlineDB, processSyncQueue, SyncQueueItem } from './offline-db';

export interface SyncStatus {
  isOnline: boolean;
  isSyncing: boolean;
  pendingCount: number;
  lastSyncTime: number | null;
  lastSyncResult: { success: number; failed: number } | null;
  nextRetryTime: number | null;
}

type SyncStatusListener = (status: SyncStatus) => void;

class BackgroundSyncManager {
  private status: SyncStatus = {
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isSyncing: false,
    pendingCount: 0,
    lastSyncTime: null,
    lastSyncResult: null,
    nextRetryTime: null,
  };
  private listeners: Set<SyncStatusListener> = new Set();
  private syncInterval: ReturnType<typeof setInterval> | null = null;
  private retryTimeout: ReturnType<typeof setTimeout> | null = null;
  private readonly SYNC_INTERVAL = 30000; // 30 seconds
  private readonly MAX_RETRY_DELAY = 5 * 60 * 1000; // 5 minutes

  constructor() {
    if (typeof window !== 'undefined') {
      this.setupEventListeners();
      this.startPeriodicSync();
      this.updatePendingCount();
    }
  }

  private setupEventListeners(): void {
    // Online/offline events
    window.addEventListener('online', () => this.handleOnline());
    window.addEventListener('offline', () => this.handleOffline());

    // Service worker messages
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', (event) => {
        this.handleServiceWorkerMessage(event);
      });
    }

    // Page visibility - sync when tab becomes visible
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && this.status.isOnline) {
        this.triggerSync();
      }
    });

    // Focus - sync when window gains focus
    window.addEventListener('focus', () => {
      if (this.status.isOnline) {
        this.triggerSync();
      }
    });
  }

  private handleOnline(): void {
    this.status.isOnline = true;
    this.notifyListeners();
    this.triggerSync();
  }

  private handleOffline(): void {
    this.status.isOnline = false;
    this.notifyListeners();
  }

  private handleServiceWorkerMessage(event: MessageEvent): void {
    const { type, payload } = event.data || {};

    switch (type) {
      case 'SYNC_SUCCESS':
        this.onSyncSuccess(payload?.url);
        break;
      case 'PREFETCH_COMPLETE':
        this.onPrefetchComplete(payload?.caseId);
        break;
      case 'PERIODIC_SYNC_COMPLETE':
        this.onPeriodicSyncComplete(payload?.timestamp);
        break;
      case 'SW_UPDATED':
        this.onServiceWorkerUpdated();
        break;
    }
  }

  private onSyncSuccess(url: string): void {
    // Update pending count
    this.updatePendingCount();
    this.status.lastSyncTime = Date.now();
    this.notifyListeners();
  }

  private onPrefetchComplete(caseId: string): void {
    console.log(`[BackgroundSync] Prefetch complete for case: ${caseId}`);
    this.notifyListeners();
  }

  private onPeriodicSyncComplete(timestamp: number): void {
    this.status.lastSyncTime = timestamp;
    this.notifyListeners();
  }

  private onServiceWorkerUpdated(): void {
    // Reload to get latest version
    if (confirm('A new version of Jurisiva AI is available. Reload to update?')) {
      window.location.reload();
    }
  }

  private startPeriodicSync(): void {
    // Initial sync
    this.triggerSync();

    // Periodic sync
    this.syncInterval = setInterval(() => {
      if (this.status.isOnline && !this.status.isSyncing) {
        this.triggerSync();
      }
    }, this.SYNC_INTERVAL);
  }

  private async updatePendingCount(): Promise<void> {
    try {
      const queue = await offlineDB.getSyncQueue();
      this.status.pendingCount = queue.length;
      this.notifyListeners();
    } catch {
      this.status.pendingCount = 0;
    }
  }

  async triggerSync(): Promise<{ success: number; failed: number } | null> {
    if (!this.status.isOnline || this.status.isSyncing) {
      return null;
    }

    this.status.isSyncing = true;
    this.notifyListeners();

    try {
      const result = await processSyncQueue((processed, total) => {
        this.status.nextRetryTime = Date.now() + (total - processed) * 1000;
        this.notifyListeners();
      });

      this.status.lastSyncTime = Date.now();
      this.status.lastSyncResult = result;
      this.status.isSyncing = false;
      this.status.nextRetryTime = null;

      await this.updatePendingCount();
      this.notifyListeners();

      return result;
    } catch (error) {
      console.error('[BackgroundSync] Sync failed:', error);
      this.status.isSyncing = false;
      this.status.nextRetryTime = Date.now() + Math.min(
        1000 * Math.pow(2, (this.status.lastSyncResult?.failed || 0)),
        this.MAX_RETRY_DELAY
      );
      this.notifyListeners();
      return null;
    }
  }

  async forceSyncNow(): Promise<{ success: number; failed: number } | null> {
    return this.triggerSync();
  }

  async queueMutation(
    method: SyncQueueItem['method'],
    url: string,
    body?: any,
    caseId?: string
  ): Promise<string> {
    const id = await offlineDB.enqueueSync({ method, url, body, caseId });
    await this.updatePendingCount();
    this.notifyListeners();

    // Try immediate sync if online
    if (this.status.isOnline) {
      this.triggerSync();
    }

    return id;
  }

  getStatus(): SyncStatus {
    return { ...this.status };
  }

  subscribe(listener: SyncStatusListener): () => void {
    this.listeners.add(listener);
    // Immediately notify with current status
    listener(this.getStatus());
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(): void {
    const status = this.getStatus();
    this.listeners.forEach((listener) => listener(status));
  }

  destroy(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }
    this.listeners.clear();
  }
}

// Singleton instance
export const backgroundSync = new BackgroundSyncManager();

// React hook
import { useState, useEffect } from 'react';

export function useSyncStatus(): SyncStatus {
  const [status, setStatus] = useState<SyncStatus>(backgroundSync.getStatus());

  useEffect(() => {
    return backgroundSync.subscribe(setStatus);
  }, []);

  return status;
}

export function useBackgroundSync() {
  return {
    triggerSync: () => backgroundSync.triggerSync(),
    forceSyncNow: () => backgroundSync.forceSyncNow(),
    queueMutation: (
      method: SyncQueueItem['method'],
      url: string,
      body?: any,
      caseId?: string
    ) => backgroundSync.queueMutation(method, url, body, caseId),
    getStatus: () => backgroundSync.getStatus(),
  };
}