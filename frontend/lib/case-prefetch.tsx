/**
 * Jurisiva AI - Case Prefetching for Offline Access
 * Hooks and utilities to prefetch case data for offline use
 */

import { useEffect, useState, useCallback } from 'react';
import { prefetchCaseForOffline } from '@/lib/offline-db';
import { useSyncStatus } from '@/lib/background-sync';

export interface PrefetchStatus {
  isPrefetching: boolean;
  progress: number;
  total: number;
  error: string | null;
  completed: boolean;
}

type PrefetchListener = (event: {
  caseId: string;
  status: PrefetchStatus;
}) => void;

class CasePrefetchManager {
  private pendingPrefetches: Map<string, PrefetchStatus> = new Map();
  private listeners: Set<PrefetchListener> = new Set();

  async prefetchCase(caseId: string): Promise<PrefetchStatus> {
    const status: PrefetchStatus = {
      isPrefetching: true,
      progress: 0,
      total: 6, // Number of API endpoints to prefetch
      error: null,
      completed: false,
    };

    this.pendingPrefetches.set(caseId, status);
    this.notifyListeners(caseId, status);

    try {
      // Use service worker to prefetch
      await prefetchCaseForOffline(caseId);

      status.isPrefetching = false;
      status.progress = status.total;
      status.completed = true;
      this.notifyListeners(caseId, status);
    } catch (error) {
      status.isPrefetching = false;
      status.error = error instanceof Error ? error.message : 'Prefetch failed';
      this.notifyListeners(caseId, status);
    }

    return status;
  }

  getStatus(caseId: string): PrefetchStatus | null {
    return this.pendingPrefetches.get(caseId) || null;
  }

  subscribe(listener: PrefetchListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notifyListeners(caseId: string, status: PrefetchStatus): void {
    this.listeners.forEach((listener) => listener({ caseId, status }));
  }
}

export const casePrefetchManager = new CasePrefetchManager();

/**
 * Hook to prefetch a case for offline access
 */
export function useCasePrefetch(caseId: string | null) {
  const [status, setStatus] = useState<PrefetchStatus | null>(null);
  const syncStatus = useSyncStatus();

  const prefetch = useCallback(async () => {
    if (!caseId) return;
    const result = await casePrefetchManager.prefetchCase(caseId);
    setStatus(result);
  }, [caseId]);

  useEffect(() => {
    if (!caseId) return;

    // Check existing status
    const existing = casePrefetchManager.getStatus(caseId);
    if (existing) {
      setStatus(existing);
    }

    // Subscribe to updates
    return casePrefetchManager.subscribe((update) => {
      if (update.caseId === caseId) {
        setStatus(update.status);
      }
    });
  }, [caseId]);

  // Auto-prefetch when online and case is loaded
  useEffect(() => {
    if (caseId && syncStatus.isOnline && !status?.completed && !status?.isPrefetching) {
      prefetch();
    }
  }, [caseId, syncStatus.isOnline, status, prefetch]);

  return {
    status,
    prefetch,
    isPrefetching: status?.isPrefetching || false,
    isCompleted: status?.completed || false,
    error: status?.error || null,
  };
}

/**
 * Hook to prefetch multiple cases (e.g., recent cases on dashboard)
 */
export function useMultiCasePrefetch(caseIds: string[]) {
  const [statuses, setStatuses] = useState<Map<string, PrefetchStatus>>(new Map());
  const syncStatus = useSyncStatus();

  const prefetchAll = useCallback(async () => {
    if (caseIds.length === 0) return;

    for (const caseId of caseIds) {
      const existing = casePrefetchManager.getStatus(caseId);
      if (existing?.completed || existing?.isPrefetching) continue;

      try {
        await casePrefetchManager.prefetchCase(caseId);
      } catch (error) {
        console.error(`Failed to prefetch case ${caseId}:`, error);
      }
    }
  }, [caseIds]);

  useEffect(() => {
    // Subscribe to all case updates
    return casePrefetchManager.subscribe((update) => {
      if (caseIds.includes(update.caseId)) {
        setStatuses((prev) => {
          const next = new Map(prev);
          next.set(update.caseId, update.status);
          return next;
        });
      }
    });
  }, [caseIds]);

  // Auto-prefetch when online
  useEffect(() => {
    if (syncStatus.isOnline && caseIds.length > 0) {
      prefetchAll();
    }
  }, [syncStatus.isOnline, caseIds, prefetchAll]);

  const getStatus = useCallback((caseId: string) => statuses.get(caseId), [statuses]);

  return {
    statuses,
    getStatus,
    prefetchAll,
    allCompleted: caseIds.every((id) => statuses.get(id)?.completed),
    anyPrefetching: caseIds.some((id) => statuses.get(id)?.isPrefetching),
  };
}

/**
 * Component to show offline availability for a case
 */
export function OfflineAvailabilityBadge({ caseId }: { caseId: string }) {
  const { status } = useCasePrefetch(caseId);
  const { isOnline } = require('@/lib/pwa').usePWA();

  if (!status?.completed) return null;

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-500/15 text-green-400 border border-green-500/30">
      <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
      Offline Ready
    </span>
  );
}

/**
 * Prefetch trigger for case links
 * Add to case cards/links to prefetch on hover/focus
 */
export function usePrefetchOnHover(caseId: string) {
  const { prefetch } = useCasePrefetch(caseId);

  const handleMouseEnter = useCallback(() => {
    // Prefetch on hover with small delay to avoid excessive requests
    const timeout = setTimeout(() => {
      prefetch();
    }, 200);
    return () => clearTimeout(timeout);
  }, [prefetch]);

  const handleFocus = useCallback(() => {
    prefetch();
  }, [prefetch]);

  return {
    onMouseEnter: handleMouseEnter,
    onFocus: handleFocus,
  };
}