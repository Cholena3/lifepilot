import { apiClient } from "./client";

// Types
export interface LifeScore {
  id: string;
  user_id: string;
  total_score: number;
  module_scores: ModuleScores;
  score_date: string;
}

export interface ModuleScores {
  exam: number;
  document: number;
  money: number;
  health: number;
  wardrobe: number;
  career: number;
}

export interface LifeScoreTrend {
  date: string;
  score: number;
}

export interface LifeScoreBreakdown {
  total_score: number;
  module_scores: ModuleScores;
  module_weights: ModuleScores;
}

export interface Badge {
  id: string;
  user_id: string;
  badge_type: string;
  name: string;
  description: string;
  icon: string;
  earned_at: string;
}

export interface BadgeDefinition {
  badge_type: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  earned: boolean;
  earned_at: string | null;
}

export interface WeeklySummary {
  id: string;
  user_id: string;
  week_start: string;
  week_end: string;
  metrics: WeeklySummaryMetrics;
  comparisons: WeeklySummaryComparisons;
  generated_at: string;
}

export interface WeeklySummaryMetrics {
  expenses_total: number;
  expenses_count: number;
  documents_added: number;
  health_records_logged: number;
  medicines_taken: number;
  medicines_missed: number;
  wardrobe_items_worn: number;
  skills_updated: number;
  courses_progress: number;
  applications_submitted: number;
  exams_bookmarked: number;
}

export interface WeeklySummaryComparisons {
  expenses_change: number;
  documents_change: number;
  health_records_change: number;
  medicine_adherence_change: number;
  wardrobe_activity_change: number;
  career_activity_change: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// API Functions
export const analyticsApi = {
  // Life Score
  getCurrentLifeScore: async (): Promise<LifeScore> => {
    return apiClient.get<LifeScore>("/api/v1/life-score/current");
  },

  getLifeScoreTrend: async (days: number = 30): Promise<LifeScoreTrend[]> => {
    return apiClient.get<LifeScoreTrend[]>("/api/v1/life-score/trends", {
      params: { days: String(days) },
    });
  },

  getLifeScoreBreakdown: async (): Promise<LifeScoreBreakdown> => {
    return apiClient.get<LifeScoreBreakdown>("/api/v1/life-score/breakdown");
  },

  // Badges
  getEarnedBadges: async (): Promise<Badge[]> => {
    return apiClient.get<Badge[]>("/api/v1/badges");
  },

  getAllBadges: async (): Promise<BadgeDefinition[]> => {
    return apiClient.get<BadgeDefinition[]>("/api/v1/badges/all");
  },

  // Weekly Summaries
  getWeeklySummaries: async (
    page: number = 1,
    pageSize: number = 10
  ): Promise<PaginatedResponse<WeeklySummary>> => {
    return apiClient.get<PaginatedResponse<WeeklySummary>>(
      "/api/v1/weekly-summaries",
      {
        params: {
          page: String(page),
          page_size: String(pageSize),
        },
      }
    );
  },

  getLatestWeeklySummary: async (): Promise<WeeklySummary | null> => {
    return apiClient.get<WeeklySummary | null>("/api/v1/weekly-summaries/latest");
  },
};
