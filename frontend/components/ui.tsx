"use client";

import Link from "next/link";
import React, { createContext, useContext, useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";

export function Button({
  children,
  variant = "primary",
  size = "md",
  className,
  href,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  href?: string;
}) {
  const styles = cn(
    "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 disabled:opacity-50 disabled:pointer-events-none",
    {
      primary:
        "bg-primary text-white hover:bg-primary-hover shadow-[0_0_20px_rgba(37,99,235,0.25)] hover:shadow-[0_0_28px_rgba(37,99,235,0.35)]",
      secondary:
        "border border-border-light bg-bg-elevated text-white hover:border-primary/50 hover:bg-bg-surface",
      ghost: "text-text-secondary hover:text-white hover:bg-bg-elevated",
      danger: "bg-danger text-white hover:bg-red-600",
    }[variant],
    {
      sm: "h-8 px-3 text-xs",
      md: "h-10 px-4 text-sm",
      lg: "h-12 px-6 text-base",
    }[size],
    className
  );

  if (href) {
    return (
      <Link href={href} className={styles}>
        {children}
      </Link>
    );
  }

  return (
    <button className={styles} {...props}>
      {children}
    </button>
  );
}

export function Card({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-bg-surface/80 backdrop-blur-sm",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        className || "bg-primary/15 text-blue-400 border-primary/30"
      )}
    >
      {children}
    </span>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  center = true,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  center?: boolean;
}) {
  return (
    <div className={cn("max-w-3xl", center && "mx-auto text-center")}>
      {eyebrow && (
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">
          {eyebrow}
        </p>
      )}
      <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-base leading-relaxed text-text-secondary">
          {description}
        </p>
      )}
    </div>
  );
}

interface TabsContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const context = useContext(TabsContext);
  if (!context) {
    throw new Error("Tabs components must be used within a Tabs provider");
  }
  return context;
}

export function Tabs({
  children,
  className,
  value,
  onValueChange,
  defaultValue,
}: {
  children: React.ReactNode;
  className?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  defaultValue?: string;
}) {
  const [internalValue, setInternalValue] = useState(defaultValue || "");
  const controlled = value !== undefined;
  const currentValue = controlled ? value : internalValue;
  
  const handleValueChange = useCallback((newValue: string) => {
    if (!controlled) {
      setInternalValue(newValue);
    }
    onValueChange?.(newValue);
  }, [controlled, onValueChange]);

  const contextValue = useMemo(
    () => ({ value: currentValue, onValueChange: handleValueChange }),
    [currentValue, handleValueChange]
  );

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-lg bg-bg-elevated p-1",
        className
      )}
      role="tablist"
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  children,
  value,
  className,
}: {
  children: React.ReactNode;
  value: string;
  className?: string;
}) {
  const { value: currentValue, onValueChange } = useTabsContext();
  const isActive = currentValue === value;

  return (
    <button
      role="tab"
      aria-selected={isActive}
      className={cn(
        "flex h-full items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 disabled:pointer-events-none disabled:opacity-50",
        isActive ? "bg-bg-surface text-white shadow-sm" : "text-text-secondary hover:text-white hover:bg-bg-surface/50",
        className
      )}
      onClick={() => onValueChange(value)}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  children,
  value,
  className,
}: {
  children: React.ReactNode;
  value: string;
  className?: string;
}) {
  const { value: currentValue } = useTabsContext();
  const isActive = currentValue === value;

  if (!isActive) return null;

  return <div className={cn("mt-2", className)}>{children}</div>;
}

// Error Boundary for catching React errors
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode; onError?: (error: Error) => void },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="rounded-full bg-red-500/10 p-3 mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">Something went wrong</h3>
          <p className="text-sm text-text-secondary mb-4">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-2 text-sm text-primary hover:bg-primary/20 transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Loading skeleton components
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-gradient-to-r from-bg-elevated via-bg-surface to-bg-elevated bg-[length:200%_100%]",
        className
      )}
    />
  );
}

export function CardSkeleton() {
  return (
    <Card className="p-6">
      <div className="space-y-4">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </Card>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }) {
  return (
    <Card className="p-6">
      <div className="space-y-3">
        {/* Header */}
        <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-3/4" />
          ))}
        </div>
        {/* Rows */}
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <div key={rowIdx} className="grid gap-4 border-t border-border pt-3" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {Array.from({ length: cols }).map((_, colIdx) => (
              <Skeleton key={colIdx} className="h-4 w-3/4" />
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}

export function PageSkeleton() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-4 w-1/2" />
      </div>
      <CardSkeleton />
      <CardSkeleton />
      <CardSkeleton />
    </div>
  );
}

// Loading state wrapper
export function LoadingState({ message = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
      <div className="relative">
        <div className="h-10 w-10 animate-spin rounded-full border-3 border-border border-t-primary" />
      </div>
      <p className="text-sm text-text-secondary">{message}</p>
    </div>
  );
}

// Empty state
export function EmptyState({ 
  icon, 
  title, 
  description, 
  action 
}: { 
  icon: React.ReactNode; 
  title: string; 
  description: string; 
  action?: React.ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center p-12 text-center">
      <div className="mb-3 text-text-muted">{icon}</div>
      <h3 className="text-base font-semibold text-white">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-text-secondary">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </Card>
  );
}

// Toast/notification component
interface ToastProps {
  message: string;
  type?: "success" | "error" | "warning" | "info";
  onClose: () => void;
}

export function Toast({ message, type = "info", onClose }: ToastProps) {
  const icons = {
    success: (
      <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
    error: (
      <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
    warning: (
      <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    info: (
      <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  };

  const styles = {
    success: "border-emerald-500/30 bg-emerald-500/10",
    error: "border-red-500/30 bg-red-500/10",
    warning: "border-amber-500/30 bg-amber-500/10",
    info: "border-blue-500/30 bg-blue-500/10",
  };

  return (
    <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${styles[type]}`}>
      {icons[type]}
      <span className="flex-1 text-sm text-white">{message}</span>
      <button onClick={onClose} className="text-text-muted hover:text-white transition-colors">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}
