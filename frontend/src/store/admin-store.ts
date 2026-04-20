/**
 * Admin store for managing admin dashboard state.
 * 
 * Provides state management for admin analytics data including
 * user metrics, feature usage, system performance, and scraper status.
 * 
 * Validates: Requirements 38.1, 38.2, 38.3, 38.4
 */

import { create } from "zustand";
import {
  adminApi,
  type UserMetrics,
  type FeatureUsage,
  type SystemPerformance,
  type ScraperStatus,
} from "@/lib/api/admin";

interface AdminState {
  // Data
  userMetrics: UserMetrics | null;
  featureUsage: FeatureUsage | null;
  systemPerformance: SystemPerformance | null;
  scraperStatus: ScraperStatus | null;

  // UI State
  isLoading: boolean;
  error: string | null;
  lastRefreshed: Date | null;
}

interface AdminActions {
  // Fetch actions
  fetchUserMetrics: () => Promise<void>;
  fetchFeatureUsage: () => Promise<void>;
  fetchSystemPerformance: () => Promise<void>;
  fetchScraperStatus: () => Promise<void>;
  fetchAllAdminData: () => Promise<void>;

  // Utility
  clearError: () => void;
  reset: () => void;
}

type AdminStore = AdminState & AdminActions;

const initialState: AdminState = {
  userMetrics: null,
  featureUsage: null,
  systemPerformance: null,
  scraperStatus: null,
  isLoading: false,
  error: null,
  lastRefreshed: null,
};

export const useAdminStore = create<AdminStore>((set) => ({
  ...initialState,

  fetchUserMetrics: async () => {
    set({ isLoading: true, error: null });
    try {
      const userMetrics = await adminApi.getUserMetrics();
      set({ userMetrics, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch user metrics",
        isLoading: false,
      });
    }
  },

  fetchFeatureUsage: async () => {
    set({ isLoading: true, error: null });
    try {
      const featureUsage = await adminApi.getFeatureUsage();
      set({ featureUsage, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch feature usage",
        isLoading: false,
      });
    }
  },

  fetchSystemPerformance: async () => {
    set({ isLoading: true, error: null });
    try {
      const systemPerformance = await adminApi.getSystemPerformance();
      set({ systemPerformance, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch system performance",
        isLoading: false,
      });
    }
  },

  fetchScraperStatus: async () => {
    set({ isLoading: true, error: null });
    try {
      const scraperStatus = await adminApi.getScraperStatus();
      set({ scraperStatus, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch scraper status",
        isLoading: false,
      });
    }
  },

  fetchAllAdminData: async () => {
    set({ isLoading: true, error: null });
    try {
      const [userMetrics, featureUsage, systemPerformance, scraperStatus] =
        await Promise.all([
          adminApi.getUserMetrics(),
          adminApi.getFeatureUsage(),
          adminApi.getSystemPerformance(),
          adminApi.getScraperStatus(),
        ]);
      set({
        userMetrics,
        featureUsage,
        systemPerformance,
        scraperStatus,
        isLoading: false,
        lastRefreshed: new Date(),
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch admin data",
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}));
