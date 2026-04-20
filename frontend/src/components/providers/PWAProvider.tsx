"use client";

import { useEffect, ReactNode } from "react";
import { OfflineIndicator } from "@/components/ui/offline-indicator";
import { useOnlineStatus } from "@/lib/hooks/useOnlineStatus";

interface PWAProviderProps {
  children: ReactNode;
}

/**
 * PWA Provider component
 * Handles service worker registration and provides offline status indicator
 */
export function PWAProvider({ children }: PWAProviderProps) {
  // Initialize online status tracking
  useOnlineStatus();

  useEffect(() => {
    // Register service worker
    if (
      typeof window !== "undefined" &&
      "serviceWorker" in navigator &&
      process.env.NODE_ENV === "production"
    ) {
      navigator.serviceWorker
        .register("/sw.js")
        .then((registration) => {
          console.log("Service Worker registered with scope:", registration.scope);

          // Handle updates
          registration.addEventListener("updatefound", () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener("statechange", () => {
                if (
                  newWorker.state === "installed" &&
                  navigator.serviceWorker.controller
                ) {
                  // New content is available, notify user
                  console.log("New content available, please refresh.");
                }
              });
            }
          });
        })
        .catch((error) => {
          console.error("Service Worker registration failed:", error);
        });

      // Handle controller change (when new SW takes over)
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        console.log("Service Worker controller changed");
      });
    }
  }, []);

  return (
    <>
      <OfflineIndicator />
      {children}
    </>
  );
}

export default PWAProvider;
