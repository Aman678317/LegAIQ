/**
 * Jurisiva AI - IndexedDB Offline Storage Layer
 * Provides offline-first data persistence with background sync
 */

export interface OfflineRecord {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  synced: boolean;
  retryCount: number;
}

export interface SyncQueueItem {
  id: string;
  method: 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  body?: any;
  headers?: Record<string, string>;
  timestamp: number;
  retryCount: number;
  caseId?: string;
}

const DB_NAME = 'jurisiva-offline';
const DB_VERSION = 1;
const STORES = {
  records: 'records',
  syncQueue: 'syncQueue',
  caseCache: 'caseCache',
  userPreferences: 'userPreferences',
} as const;

class OfflineDB {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<IDBDatabase> | null = null;

  async init(): Promise<IDBDatabase> {
    if (this.db) return this.db;
    if (this.initPromise) return this.initPromise;

    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const database = (event.target as IDBOpenDBRequest).result;

        // Records store - for cached API responses
        if (!database.objectStoreNames.contains(STORES.records)) {
          const recordStore = database.createObjectStore(STORES.records, { keyPath: 'id' });
          recordStore.createIndex('type', 'type', { unique: false });
          recordStore.createIndex('timestamp', 'timestamp', { unique: false });
          recordStore.createIndex('synced', 'synced', { unique: false });
        }

        // Sync queue - for pending mutations
        if (!database.objectStoreNames.contains(STORES.syncQueue)) {
          const syncStore = database.createObjectStore(STORES.syncQueue, { keyPath: 'id' });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
          syncStore.createIndex('caseId', 'caseId', { unique: false });
        }

        // Case cache - for full case data
        if (!database.objectStoreNames.contains(STORES.caseCache)) {
          const caseStore = database.createObjectStore(STORES.caseCache, { keyPath: 'caseId' });
          caseStore.createIndex('timestamp', 'timestamp', { unique: false });
        }

        // User preferences
        if (!database.objectStoreNames.contains(STORES.userPreferences)) {
          database.createObjectStore(STORES.userPreferences, { keyPath: 'key' });
        }
      };
    });

    return this.initPromise;
  }

  // === Records (cached API responses) ===

  async putRecord(type: string, id: string, data: any): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.records, 'readwrite');
      const store = tx.objectStore(STORES.records);
      store.put({
        id,
        type,
        data,
        timestamp: Date.now(),
        synced: true,
        retryCount: 0,
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async getRecord(type: string, id: string): Promise<OfflineRecord | null> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.records, 'readonly');
      const store = tx.objectStore(STORES.records);
      const request = store.get(id);
      request.onsuccess = () => {
        const record = request.result;
        resolve(record && record.type === type ? record : null);
      };
      request.onerror = () => reject(request.error);
    });
  }

  async getRecordsByType(type: string): Promise<OfflineRecord[]> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.records, 'readonly');
      const store = tx.objectStore(STORES.records);
      const index = store.index('type');
      const request = index.getAll(type);
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  async deleteRecord(id: string): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.records, 'readwrite');
      const store = tx.objectStore(STORES.records);
      store.delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async markRecordSynced(id: string): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.records, 'readwrite');
      const store = tx.objectStore(STORES.records);
      const request = store.get(id);
      request.onsuccess = () => {
        const record = request.result;
        if (record) {
          record.synced = true;
          store.put(record);
        }
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      };
      request.onerror = () => reject(request.error);
    });
  }

  // === Sync Queue (pending mutations) ===

  async enqueueSync(item: Omit<SyncQueueItem, 'id' | 'timestamp' | 'retryCount'>): Promise<string> {
    const db = await this.init();
    const id = `${item.method}-${item.url}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    const queueItem: SyncQueueItem = {
      ...item,
      id,
      timestamp: Date.now(),
      retryCount: 0,
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.syncQueue, 'readwrite');
      const store = tx.objectStore(STORES.syncQueue);
      store.put(queueItem);
      tx.oncomplete = () => resolve(id);
      tx.onerror = () => reject(tx.error);
    });
  }

  async getSyncQueue(): Promise<SyncQueueItem[]> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.syncQueue, 'readonly');
      const store = tx.objectStore(STORES.syncQueue);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  async removeFromSyncQueue(id: string): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.syncQueue, 'readwrite');
      const store = tx.objectStore(STORES.syncQueue);
      store.delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async incrementRetryCount(id: string): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.syncQueue, 'readwrite');
      const store = tx.objectStore(STORES.syncQueue);
      const request = store.get(id);
      request.onsuccess = () => {
        const item = request.result;
        if (item) {
          item.retryCount += 1;
          store.put(item);
        }
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      };
      request.onerror = () => reject(request.error);
    });
  }

  // === Case Cache ===

  async cacheCase(caseId: string, data: any): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.caseCache, 'readwrite');
      const store = tx.objectStore(STORES.caseCache);
      store.put({
        caseId,
        data,
        timestamp: Date.now(),
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async getCachedCase(caseId: string): Promise<any | null> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.caseCache, 'readonly');
      const store = tx.objectStore(STORES.caseCache);
      const request = store.get(caseId);
      request.onsuccess = () => resolve(request.result?.data || null);
      request.onerror = () => reject(request.error);
    });
  }

  async getAllCachedCases(): Promise<Array<{ caseId: string; data: any; timestamp: number }>> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.caseCache, 'readonly');
      const store = tx.objectStore(STORES.caseCache);
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  // === User Preferences ===

  async setPreference(key: string, value: any): Promise<void> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.userPreferences, 'readwrite');
      const store = tx.objectStore(STORES.userPreferences);
      store.put({ key, value });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async getPreference(key: string): Promise<any> {
    const db = await this.init();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORES.userPreferences, 'readonly');
      const store = tx.objectStore(STORES.userPreferences);
      const request = store.get(key);
      request.onsuccess = () => resolve(request.result?.value);
      request.onerror = () => reject(request.error);
    });
  }

  // === Utility ===

  async clearAll(): Promise<void> {
    const db = await this.init();
    const storeNames = Object.values(STORES);
    return new Promise((resolve, reject) => {
      const tx = db.transaction(storeNames, 'readwrite');
      let completed = 0;
      storeNames.forEach((storeName) => {
        const store = tx.objectStore(storeName);
        const request = store.clear();
        request.onsuccess = () => {
          completed++;
          if (completed === storeNames.length) resolve();
        };
        request.onerror = () => reject(request.error);
      });
    });
  }

  async getStorageEstimate(): Promise<{ usage: number; quota: number }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return { usage: estimate.usage || 0, quota: estimate.quota || 0 };
    }
    return { usage: 0, quota: 0 };
  }
}

// Singleton instance
export const offlineDB = new OfflineDB();

// React hook for offline DB
export function useOfflineDB() {
  return offlineDB;
}

// Helper functions for common operations

export async function cacheApiResponse(type: string, url: string, data: any): Promise<void> {
  const id = `${type}:${url}`;
  await offlineDB.putRecord(type, id, data);
}

export async function getCachedApiResponse<T>(type: string, url: string): Promise<T | null> {
  const id = `${type}:${url}`;
  const record = await offlineDB.getRecord(type, id);
  return record?.data as T || null;
}

export async function queueMutation(
  method: SyncQueueItem['method'],
  url: string,
  body?: any,
  caseId?: string
): Promise<string> {
  return offlineDB.enqueueSync({ method, url, body, caseId });
}

export async function processSyncQueue(
  onProgress?: (processed: number, total: number) => void
): Promise<{ success: number; failed: number }> {
  const queue = await offlineDB.getSyncQueue();
  let success = 0;
  let failed = 0;

  for (let i = 0; i < queue.length; i++) {
    const item = queue[i];
    if (item.retryCount >= 5) {
      // Max retries reached, remove from queue
      await offlineDB.removeFromSyncQueue(item.id);
      failed++;
      continue;
    }

    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: {
          'Content-Type': 'application/json',
          ...item.headers,
        },
        body: item.body ? JSON.stringify(item.body) : undefined,
        credentials: 'include',
      });

      if (response.ok) {
        await offlineDB.removeFromSyncQueue(item.id);
        success++;
      } else {
        await offlineDB.incrementRetryCount(item.id);
        failed++;
      }
    } catch {
      await offlineDB.incrementRetryCount(item.id);
      failed++;
    }

    onProgress?.(i + 1, queue.length);
  }

  return { success, failed };
}

export async function prefetchCaseForOffline(caseId: string): Promise<void> {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    registration.active?.postMessage({
      type: 'PREFETCH_CASE',
      payload: { caseId },
    });
  }
}