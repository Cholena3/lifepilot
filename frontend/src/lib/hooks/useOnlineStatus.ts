"use client";

import { useEffect, useState, useCallback } from "react";
import { useUIStore } from "@/store/ui-store";

/**
 * Hook to detect and track online/offline status
 * Updates the global UI store and provides local state
 * 
 * @returns Object containing:
 *   - isOnline: boolean indicating current connection status
 *   - isOffline: boolean (inverse of isOnline for convenience)
 *   - lastOnlineAt: Date when the user was last online (null if always online)
 */
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [lastOnlineAt, setLastOnlineAt] = useState<Date | null>(null);
  const setOffline = useUIStore((state) => state.setOffline);

  const handleOnline = useCallback(() => {
    setIsOnline(true);
    setOffline(false);
  }, [setOffline]);

  const handleOffline = useCallback(() => {
    setIsOnline(false);
    setOffline(true);
    setLastOnlineAt(new Date());
  }, [setOffline]);

  useEffect(() => {
    // Check initial status
    if (typeof window !== "undefined") {
      const online = navigator.onLine;
      setIsOnline(online);
      setOffline(!online);
      if (!online) {
        setLastOnlineAt(new Date());
      }
    }

    // Add event listeners
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [handleOnline, handleOffline, setOffline]);

  return {
    isOnline,
    isOffline: !isOnline,
    lastOnlineAt,
  };
}

export default useOnlineStatus;
