import { create } from "zustand";
import {
  analyticsApi,
  type LifeScore,
  type LifeScoreTrend,
  type LifeScoreBreakdown,
  type Badge,
  type BadgeDefinition,
  type WeeklySummary,
} from "@/lib/api/analytics";

interface AnalyticsState {
  // Life Score
  currentScore: LifeScore | null;
  scoreTrend: LifeScoreTrend[];
  scoreBreakdown: LifeScoreBreakdown | null;

  // Badges
  earnedBadges: Badge[];
  allBadges: BadgeDefinition[];

  // Weekly Summaries
  weeklySummaries: WeeklySummary[];
  latestSummary: WeeklySummary | null;
  summariesPage: number;
  summariesTotalPages: number;

  // UI State
  isLoading: boolean;
  error: string | null;
  trendDays: number;
}

interface AnalyticsActions {
  // Life Score
  fetchCurrentScore: () => Promise<void>;
  fetchScoreTrend: (days?: number) => Promise<void>;
  fetchScoreBreakdown: () => Promise<void>;
  setTrendDays: (days: number) => void;

  // Badges
  fetchEarnedBadges: () => Promise<void>;
  fetchAllBadges: () => Promise<void>;

  // Weekly Summaries
  fetchWeeklySummaries: (page?: number) => Promise<void>;
  fetchLatestSummary: () => Promise<void>;

  // Utility
  fetchAllAnalytics: () => Promise<void>;
  clearError: () => void;
}

type AnalyticsStore = AnalyticsState & AnalyticsActions;

export const useAnalyticsStore = create<AnalyticsStore>((set, get) => ({
  // Initial State
  currentScore: null,
  scoreTrend: [],
  scoreBreakdown: null,
  earnedBadges: [],
  allBadges: [],
  weeklySummaries: [],
  latestSummary: null,
  summariesPage: 1,
  summariesTotalPages: 1,
  isLoading: false,
  error: null,
  trendDays: 30,

  // Actions
  fetchCurrentScore: async () => {
    set({ isLoading: true, error: null });
    try {
      const currentScore = await analyticsApi.getCurrentLifeScore();
      set({ currentScore, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch life score",
        isLoading: false,
      });
    }
  },

  fetchScoreTrend: async (days?: number) => {
    const trendDays = days || get().trendDays;
    set({ isLoading: true, error: null });
    try {
      const scoreTrend = await analyticsApi.getLifeScoreTrend(trendDays);
      set({ scoreTrend, trendDays, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch score trend",
        isLoading: false,
      });
    }
  },

  fetchScoreBreakdown: async () => {
    set({ isLoading: true, error: null });
    try {
      const scoreBreakdown = await analyticsApi.getLifeScoreBreakdown();
      set({ scoreBreakdown, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch score breakdown",
        isLoading: false,
      });
    }
  },

  setTrendDays: (days: number) => {
    set({ trendDays: days });
    get().fetchScoreTrend(days);
  },

  fetchEarnedBadges: async () => {
    set({ isLoading: true, error: null });
    try {
      const earnedBadges = await analyticsApi.getEarnedBadges();
      set({ earnedBadges, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch badges",
        isLoading: false,
      });
    }
  },

  fetchAllBadges: async () => {
    set({ isLoading: true, error: null });
    try {
      const allBadges = await analyticsApi.getAllBadges();
      set({ allBadges, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch all badges",
        isLoading: false,
      });
    }
  },

  fetchWeeklySummaries: async (page?: number) => {
    const currentPage = page || get().summariesPage;
    set({ isLoading: true, error: null });
    try {
      const response = await analyticsApi.getWeeklySummaries(currentPage, 10);
      set({
        weeklySummaries: response.items,
        summariesPage: response.page,
        summariesTotalPages: response.total_pages,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch weekly summaries",
        isLoading: false,
      });
    }
  },

  fetchLatestSummary: async () => {
    set({ isLoading: true, error: null });
    try {
      const latestSummary = await analyticsApi.getLatestWeeklySummary();
      set({ latestSummary, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch latest summary",
        isLoading: false,
      });
    }
  },

  fetchAllAnalytics: async () => {
    set({ isLoading: true, error: null });
    try {
      await Promise.all([
        get().fetchCurrentScore(),
        get().fetchScoreTrend(),
        get().fetchScoreBreakdown(),
        get().fetchAllBadges(),
        get().fetchLatestSummary(),
      ]);
      set({ isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch analytics",
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
