/**
 * Admin API client for admin dashboard endpoints.
 * 
 * Provides API functions for fetching admin analytics data including
 * user metrics, feature usage, system performance, and scraper status.
 * 
 * Validates: Requirements 38.1, 38.2, 38.3, 38.4
 */

import { apiClient } from "./client";

// ============================================================================
// User Metrics Types - Validates: Requirements 38.1
// ============================================================================

export interface UserGrowthDataPoint {
  date: string;
  total_users: number;
  new_users: number;
}

export interface UserMetrics {
  total_users: number;
  active_users_24h: number;
  active_users_7d: number;
  active_users_30d: number;
  new_users_today: number;
  new_users_7d: number;
  new_users_30d: number;
  verified_phone_users: number;
  oauth_users: number;
  growth_trend: UserGrowthDataPoint[];
}

// ============================================================================
// Feature Usage Types - Validates: Requirements 38.2
// ============================================================================

export interface ModuleUsageStats {
  module_name: string;
  total_records: number;
  active_users: number;
  records_created_7d: number;
  records_created_30d: number;
}

export interface FeatureUsage {
  modules: ModuleUsageStats[];
  most_active_module: string | null;
  least_active_module: string | null;
}

// ============================================================================
// System Performance Types - Validates: Requirements 38.3
// ============================================================================

export interface EndpointPerformance {
  endpoint: string;
  method: string;
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
  request_count: number;
  error_count: number;
  error_rate: number;
}

export interface SystemPerformance {
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
  total_requests_24h: number;
  total_errors_24h: number;
  error_rate_24h: number;
  slowest_endpoints: EndpointPerformance[];
  highest_error_endpoints: EndpointPerformance[];
  database_connection_pool_size: number;
  redis_connected: boolean;
}

// ============================================================================
// Scraper Status Types - Validates: Requirements 38.4
// ============================================================================

export interface ScraperJobStatus {
  source: string;
  last_run_at: string | null;
  last_run_success: boolean;
  exams_found: number;
  exams_created: number;
  exams_updated: number;
  error_message: string | null;
  next_scheduled_run: string | null;
}

export interface ScraperStatus {
  scrapers: ScraperJobStatus[];
  total_exams_scraped: number;
  last_successful_scrape: string | null;
  scraper_health: "healthy" | "degraded" | "unhealthy";
}

// ============================================================================
// Admin API Functions
// ============================================================================

export const adminApi = {
  /**
   * Get user metrics including counts and growth trends.
   * Validates: Requirements 38.1
   */
  getUserMetrics: async (): Promise<UserMetrics> => {
    return apiClient.get<UserMetrics>("/api/v1/admin/users");
  },

  /**
   * Get feature usage statistics by module.
   * Validates: Requirements 38.2
   */
  getFeatureUsage: async (): Promise<FeatureUsage> => {
    return apiClient.get<FeatureUsage>("/api/v1/admin/features");
  },

  /**
   * Get system performance metrics.
   * Validates: Requirements 38.3
   */
  getSystemPerformance: async (): Promise<SystemPerformance> => {
    return apiClient.get<SystemPerformance>("/api/v1/admin/performance");
  },

  /**
   * Get scraper job status.
   * Validates: Requirements 38.4
   */
  getScraperStatus: async (): Promise<ScraperStatus> => {
    return apiClient.get<ScraperStatus>("/api/v1/admin/scrapers");
  },
};
