"use client";

import { useOnlineStatus } from "@/lib/hooks/useOnlineStatus";
import { WifiOff, Wifi } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface OfflineIndicatorProps {
  className?: string;
  showOnlineNotification?: boolean;
}

/**
 * Offline status indicator component
 * Displays a banner when the user is offline
 * Optionally shows a brief notification when coming back online
 */
export function OfflineIndicator({
  className,
  showOnlineNotification = true,
}: OfflineIndicatorProps) {
  const { isOffline, lastOnlineAt } = useOnlineStatus();
  const [showOnlineBanner, setShowOnlineBanner] = useState(false);
  const [wasOffline, setWasOffline] = useState(false);

  // Track when user comes back online to show notification
  useEffect(() => {
    if (isOffline) {
      setWasOffline(true);
    } else if (wasOffline && showOnlineNotification) {
      setShowOnlineBanner(true);
      const timer = setTimeout(() => {
        setShowOnlineBanner(false);
        setWasOffline(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [isOffline, wasOffline, showOnlineNotification]);

  // Format time since last online
  const getTimeSinceOnline = () => {
    if (!lastOnlineAt) return "";
    const now = new Date();
    const diffMs = now.getTime() - lastOnlineAt.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return "just now";
    if (diffMins === 1) return "1 minute ago";
    if (diffMins < 60) return `${diffMins} minutes ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours === 1) return "1 hour ago";
    return `${diffHours} hours ago`;
  };

  if (!isOffline && !showOnlineBanner) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-300",
        isOffline
          ? "bg-amber-500 text-amber-950"
          : "bg-green-500 text-green-950",
        className
      )}
    >
      {isOffline ? (
        <>
          <WifiOff className="h-4 w-4" aria-hidden="true" />
          <span>
            You&apos;re offline. Some features may be limited.
            {lastOnlineAt && (
              <span className="ml-1 opacity-80">
                (Last online: {getTimeSinceOnline()})
              </span>
            )}
          </span>
        </>
      ) : (
        <>
          <Wifi className="h-4 w-4" aria-hidden="true" />
          <span>You&apos;re back online!</span>
        </>
      )}
    </div>
  );
}

/**
 * Compact offline indicator for use in headers/navbars
 */
export function OfflineIndicatorCompact({ className }: { className?: string }) {
  const { isOffline } = useOnlineStatus();

  if (!isOffline) {
    return null;
  }

  return (
    <div
      role="status"
      aria-label="Offline"
      className={cn(
        "flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800",
        className
      )}
    >
      <WifiOff className="h-3 w-3" aria-hidden="true" />
      <span>Offline</span>
    </div>
  );
}

export default OfflineIndicator;
