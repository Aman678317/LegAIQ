/**
 * Jurisiva AI - PWA Registration & Offline Utilities
 * Handles service worker registration, updates, and PWA installation
 */

export interface PWAInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

type PWAEventType = 'installable' | 'installed' | 'update-available' | 'offline-ready' | 'sync-complete';

type PWAEventListener = (event: {
  type: PWAEventType;
  payload?: any;
}) => void;

class PWAManager {
  private registration: ServiceWorkerRegistration | null = null;
  private deferredPrompt: PWAInstallPromptEvent | null = null;
  private listeners: Set<PWAEventListener> = new Set();
  private updateCheckInterval: ReturnType<typeof setInterval> | null = null;

  async initialize(): Promise<ServiceWorkerRegistration | null> {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return null;
    }

    // In local development, unregister any active SW so offline caching does not block dev
    const isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (isDev) {
      try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const registration of registrations) {
          await registration.unregister();
        }
        const cacheKeys = await caches.keys();
        await Promise.all(cacheKeys.map((key) => caches.delete(key)));
      } catch {
        // ignore
      }
      return null;
    }

    try {
      // Register service worker in production
      this.registration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/',
      });

      console.log('[PWA] Service Worker registered:', this.registration.scope);

      // Handle updates
      this.registration.addEventListener('updatefound', () => {
        this.handleUpdateFound();
      });

      // Check for waiting service worker (update available)
      if (this.registration.waiting) {
        this.notifyListeners({ type: 'update-available' });
      }

      // Listen for controller change (new SW activated)
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        this.notifyListeners({ type: 'offline-ready' });
      });

      // Setup install prompt
      this.setupInstallPrompt();

      // Periodic update checks
      this.startUpdateChecks();

      return this.registration;
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
      return null;
    }
  }

  private handleUpdateFound(): void {
    if (!this.registration) return;

    const newWorker = this.registration.installing;
    if (!newWorker) return;

    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // New version available
        this.notifyListeners({ type: 'update-available' });
      } else if (newWorker.state === 'activated') {
        this.notifyListeners({ type: 'offline-ready' });
      }
    });
  }

  private setupInstallPrompt(): void {
    window.addEventListener('beforeinstallprompt', (event) => {
      // Prevent default browser prompt
      event.preventDefault();
      this.deferredPrompt = event as PWAInstallPromptEvent;
      this.notifyListeners({ type: 'installable' });
    });

    window.addEventListener('appinstalled', () => {
      this.deferredPrompt = null;
      this.notifyListeners({ type: 'installed' });
    });
  }

  private startUpdateChecks(): void {
    // Check for updates every hour
    this.updateCheckInterval = setInterval(() => {
      this.registration?.update();
    }, 60 * 60 * 1000);
  }

  async promptInstall(): Promise<boolean> {
    if (!this.deferredPrompt) return false;

    try {
      await this.deferredPrompt.prompt();
      const choice = await this.deferredPrompt.userChoice;
      this.deferredPrompt = null;
      return choice.outcome === 'accepted';
    } catch {
      return false;
    }
  }

  async skipWaiting(): Promise<void> {
    if (this.registration?.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  }

  async checkForUpdates(): Promise<boolean> {
    if (!this.registration) return false;
    await this.registration.update();
    return !!this.registration.waiting;
  }

  async getCacheStatus(): Promise<any> {
    const active = this.registration?.active;
    if (!active) return null;

    return new Promise((resolve) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = (event) => resolve(event.data);
      active.postMessage(
        { type: 'GET_CACHE_STATUS' },
        [channel.port2]
      );
    });
  }

  async clearCache(): Promise<void> {
    const active = this.registration?.active;
    if (!active) return;

    return new Promise((resolve) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = () => resolve();
      active.postMessage(
        { type: 'CLEAR_CACHE' },
        [channel.port2]
      );
    });
  }

  isInstallable(): boolean {
    return !!this.deferredPrompt;
  }

  isInstalled(): boolean {
    // Check if running as PWA
    return window.matchMedia('(display-mode: standalone)').matches ||
           (window.navigator as any).standalone === true;
  }

  getRegistration(): ServiceWorkerRegistration | null {
    return this.registration;
  }

  subscribe(listener: PWAEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(event: { type: PWAEventType; payload?: any }): void {
    this.listeners.forEach((listener) => listener(event));
  }

  destroy(): void {
    if (this.updateCheckInterval) {
      clearInterval(this.updateCheckInterval);
      this.updateCheckInterval = null;
    }
    this.listeners.clear();
  }
}

// Singleton instance
export const pwaManager = new PWAManager();

// React hooks
import { useState, useEffect } from 'react';

export function usePWA() {
  const [installable, setInstallable] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [offlineReady, setOfflineReady] = useState(false);

  useEffect(() => {
    // Check if already installed
    setInstalled(pwaManager.isInstalled());

    const unsubscribe = pwaManager.subscribe((event) => {
      switch (event.type) {
        case 'installable':
          setInstallable(true);
          break;
        case 'installed':
          setInstallable(false);
          setInstalled(true);
          break;
        case 'update-available':
          setUpdateAvailable(true);
          break;
        case 'offline-ready':
          setOfflineReady(true);
          break;
      }
    });

    // Initialize PWA
    pwaManager.initialize();

    return unsubscribe;
  }, []);

  const promptInstall = async () => {
    const result = await pwaManager.promptInstall();
    if (result) {
      setInstallable(false);
      setInstalled(true);
    }
    return result;
  };

  const applyUpdate = async () => {
    await pwaManager.skipWaiting();
    setUpdateAvailable(false);
  };

  return {
    installable,
    installed,
    updateAvailable,
    offlineReady,
    promptInstall,
    applyUpdate,
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  };
}

// Utility functions
export function formatSyncStatus(status: any): string {
  if (!navigator.onLine) return 'Offline';
  if (status.isSyncing) return 'Syncing...';
  if (status.pendingCount > 0) return `${status.pendingCount} pending`;
  if (status.lastSyncTime) {
    const mins = Math.floor((Date.now() - status.lastSyncTime) / 60000);
    if (mins < 1) return 'Just synced';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }
  return 'Never synced';
}

export function getSyncStatusColor(status: any): string {
  if (!navigator.onLine) return 'text-amber-400';
  if (status.isSyncing) return 'text-blue-400';
  if (status.pendingCount > 0) return 'text-amber-400';
  if (status.lastSyncResult?.failed && status.lastSyncResult.failed > 0) return 'text-red-400';
  return 'text-green-400';
}