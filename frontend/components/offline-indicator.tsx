"use client";

import { useState, useEffect } from "react";
import { WifiOff, Wifi, RotateCcw, Download, CheckCircle, AlertCircle, Info, X } from "lucide-react";
import { useSyncStatus } from "@/lib/background-sync";
import { usePWA, formatSyncStatus, getSyncStatusColor } from "@/lib/pwa";
import { cn } from "@/lib/utils";

/**
 * Offline Indicator Component
 * Shows network status and sync state
 */
export function OfflineIndicator({ compact = false }: { compact?: boolean }) {
  const syncStatus = useSyncStatus();
  const { isOnline, installable, updateAvailable, offlineReady, promptInstall, applyUpdate } = usePWA();
  const [showDetails, setShowDetails] = useState(false);

  const statusText = formatSyncStatus(syncStatus);
  const statusColor = getSyncStatusColor(syncStatus);

  if (compact) {
    return (
      <div className="flex items-center gap-1.5">
        <div
          className={cn(
            "w-2 h-2 rounded-full transition-colors",
            isOnline ? "bg-green-400" : "bg-amber-400"
          )}
        />
        {!isOnline && (
          <span className="text-[11px] text-text-muted">Offline</span>
        )}
        {syncStatus.pendingCount > 0 && (
          <span className="text-[11px] text-amber-400">
            {syncStatus.pendingCount} pending
          </span>
        )}
        {syncStatus.isSyncing && (
          <RotateCcw className="w-3 h-3 text-blue-400 animate-spin" />
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={cn(
          "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-colors",
          "hover:bg-bg-elevated"
        )}
        aria-label="Network and sync status"
      >
        <div className="flex items-center gap-1.5">
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              isOnline ? "bg-green-400" : "bg-amber-400 animate-pulse"
            )}
          />
          <span className={cn("font-medium", statusColor)}>
            {isOnline ? "Online" : "Offline"}
          </span>
          {syncStatus.isSyncing && (
            <RotateCcw className="w-4 h-4 text-blue-400 animate-spin" />
          )}
          {syncStatus.pendingCount > 0 && !syncStatus.isSyncing && (
            <span className="text-amber-400 font-medium">
              {syncStatus.pendingCount}
            </span>
          )}
        </div>
      </button>

      {showDetails && (
        <div className="absolute right-0 top-full mt-2 w-72 rounded-xl border border-border bg-bg-surface p-3 shadow-xl z-50 animate-fade-in">
          <div className="space-y-3">
            {/* Network Status */}
            <div className="flex items-center gap-2 p-2 rounded-lg bg-bg-elevated">
              <div
                className={cn(
                  "w-3 h-3 rounded-full flex-shrink-0",
                  isOnline ? "bg-green-400" : "bg-amber-400"
                )}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white">
                  {isOnline ? "Connected" : "Offline Mode"}
                </p>
                <p className="text-[11px] text-text-muted truncate">
                  {isOnline
                    ? "All features available"
                    : "Changes will sync when online"}
                </p>
              </div>
              {isOnline && syncStatus.pendingCount > 0 && (
                <button
                  onClick={() => backgroundSync.forceSyncNow()}
                  disabled={syncStatus.isSyncing}
                  className="flex-shrink-0 px-2 py-1 text-[11px] font-medium rounded bg-primary/20 text-primary hover:bg-primary/30 disabled:opacity-50"
                >
                  {syncStatus.isSyncing ? "Syncing..." : "Sync Now"}
                </button>
              )}
            </div>

            {/* Sync Status */}
            <div className="border-t border-border pt-2 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">Last Sync</span>
                <span className="font-medium text-white">
                  {syncStatus.lastSyncTime
                    ? new Date(syncStatus.lastSyncTime).toLocaleTimeString()
                    : "Never"}
                </span>
              </div>
              {syncStatus.lastSyncResult && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-text-secondary">Last Result</span>
                  <span className="font-medium text-white">
                    {syncStatus.lastSyncResult.success} succeeded
                    {syncStatus.lastSyncResult.failed > 0 && (
                      <span className="ml-2 text-red-400">
                        , {syncStatus.lastSyncResult.failed} failed
                      </span>
                    )}
                  </span>
                </div>
              )}
              {syncStatus.nextRetryTime && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-text-secondary">Next Retry</span>
                  <span className="font-medium text-amber-400">
                    in {Math.ceil((syncStatus.nextRetryTime - Date.now()) / 1000)}s
                  </span>
                </div>
              )}
            </div>

            {/* PWA Actions */}
            {(installable || updateAvailable || offlineReady) && (
              <div className="border-t border-border pt-2 space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                  App Actions
                </p>
                {installable && (
                  <button
                    onClick={promptInstall}
                    className="flex w-full items-center gap-2 px-2 py-1.5 text-sm text-white rounded-lg bg-primary/20 hover:bg-primary/30 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    Install App
                  </button>
                )}
                {updateAvailable && (
                  <button
                    onClick={applyUpdate}
                    className="flex w-full items-center gap-2 px-2 py-1.5 text-sm text-white rounded-lg bg-blue-500/20 hover:bg-blue-500/30 transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Update Available
                  </button>
                )}
                {offlineReady && !installable && !updateAvailable && (
                  <div className="flex items-center gap-2 px-2 py-1.5 text-sm text-green-400 rounded-lg bg-green-500/10">
                    <CheckCircle className="w-4 h-4" />
                    Ready for Offline
                  </div>
                )}
              </div>
            )}

            {/* Storage Info */}
            <div className="border-t border-border pt-2">
              <StorageInfo />
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      <div
        className={showDetails ? "fixed inset-0 z-40" : "hidden"}
        onClick={() => setShowDetails(false)}
        aria-hidden="true"
      />
    </div>
  );
}

/**
 * Storage Info Component
 * Shows IndexedDB storage usage
 */
function StorageInfo() {
  const [storage, setStorage] = useState<{ usage: number; quota: number } | null>(null);

  useEffect(() => {
    async function loadStorage() {
      const estimate = await navigator.storage?.estimate();
      if (estimate) {
        setStorage({ usage: estimate.usage || 0, quota: estimate.quota || 0 });
      }
    }
    loadStorage();
  }, []);

  if (!storage) return null;

  const usagePercent = storage.quota > 0 ? (storage.usage / storage.quota) * 100 : 0;
  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-text-muted">Storage</span>
        <span className="text-text-secondary">
          {formatBytes(storage.usage)} / {formatBytes(storage.quota)}
        </span>
      </div>
      <div className="h-1.5 bg-bg-elevated rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${Math.min(usagePercent, 100)}%` }}
        />
      </div>
      <p className="text-[10px] text-text-muted">
        {usagePercent.toFixed(1)}% used
      </p>
    </div>
  );
}

/**
 * Sync Status Badge
 * Small indicator for use in headers/toolbars
 */
export function SyncStatusBadge() {
  const syncStatus = useSyncStatus();
  const { isOnline } = usePWA();

  if (isOnline && syncStatus.pendingCount === 0 && !syncStatus.isSyncing) {
    return (
      <div className="flex items-center gap-1.5 text-green-400" title="All synced">
        <Wifi className="w-4 h-4" />
        <span className="text-[11px] font-medium hidden sm:inline">Synced</span>
      </div>
    );
  }

  if (!isOnline) {
    return (
      <div className="flex items-center gap-1.5 text-amber-400" title="Offline mode">
        <WifiOff className="w-4 h-4" />
        <span className="text-[11px] font-medium hidden sm:inline">Offline</span>
      </div>
    );
  }

  if (syncStatus.isSyncing) {
    return (
      <div className="flex items-center gap-1.5 text-blue-400" title="Syncing...">
        <RotateCcw className="w-4 h-4 animate-spin" />
        <span className="text-[11px] font-medium hidden sm:inline">Syncing</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-amber-400" title={`${syncStatus.pendingCount} pending changes`}>
      <RotateCcw className="w-4 h-4" />
      <span className="text-[11px] font-medium hidden sm:inline">
        {syncStatus.pendingCount} pending
      </span>
    </div>
  );
}

/**
 * PWA Install Prompt
 * Banner prompting user to install the app
 */
export function PWAInstallPrompt({ onDismiss }: { onDismiss?: () => void }) {
  const { installable, installed, promptInstall } = usePWA();
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (installed) setDismissed(true);
  }, [installed]);

  if (!installable || installed || dismissed) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-50 animate-slide-up">
      <div className="rounded-xl border border-border bg-bg-surface p-4 shadow-xl">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20 text-primary">
            <Download className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white">Install Jurisiva AI</h3>
            <p className="mt-1 text-sm text-text-secondary">
              Add to home screen for offline access and faster loading
            </p>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="flex-shrink-0 text-text-muted hover:text-white"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            onClick={promptInstall}
            className="flex-1 py-2 px-3 text-sm font-medium text-white rounded-lg bg-primary hover:bg-primary/90 transition-colors"
          >
            Install
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="flex-1 py-2 px-3 text-sm font-medium text-text-secondary rounded-lg bg-bg-elevated hover:bg-bg-hover transition-colors"
          >
            Later
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Update Available Banner
 * Shows when a new version of the app is available
 */
export function UpdateAvailableBanner({ onApply }: { onApply?: () => void }) {
  const { updateAvailable, applyUpdate } = usePWA();
  const [dismissed, setDismissed] = useState(false);

  if (!updateAvailable || dismissed) return null;

  const handleApply = async () => {
    await applyUpdate();
    onApply?.();
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-slide-down border-b border-blue-500/50 bg-blue-500/10 backdrop-blur-sm">
      <div className="mx-auto max-w-4xl px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-blue-300">
          <Info className="w-5 h-5" />
          <span className="text-sm font-medium">Update Available</span>
          <span className="text-[11px] text-blue-400/80">New version ready</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleApply}
            className="px-3 py-1 text-sm font-medium text-white rounded bg-blue-500 hover:bg-blue-600 transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={() => setDismissed(true)}
            className="text-blue-400 hover:text-blue-300"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Offline Banner
 * Shows when the app is offline
 */
export function OfflineBanner() {
  const { isOnline } = usePWA();

  if (isOnline) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 animate-slide-down border-b border-amber-500/50 bg-amber-500/10 backdrop-blur-sm">
      <div className="mx-auto max-w-4xl px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-amber-300">
          <WifiOff className="w-5 h-5" />
          <span className="text-sm font-medium">You're Offline</span>
          <span className="text-[11px] text-amber-400/80">Changes will sync when reconnected</span>
        </div>
        <AlertCircle className="w-5 h-5 text-amber-400" />
      </div>
    </div>
  );
}

// Need to import backgroundSync for the forceSyncNow call
import { backgroundSync } from "@/lib/background-sync";