import { apiClient } from "./client";

// ============================================================================
// Enums
// ============================================================================

export type ExamType =
  | "campus_placement"
  | "off_campus"
  | "internship"
  | "higher_education"
  | "government"
  | "scholarship";

export type ApplicationStatus =
  | "interested"
  | "applied"
  | "appeared"
  | "result_pending"
  | "selected"
  | "not_selected";

// ============================================================================
// Exam Types
// ============================================================================

export interface Exam {
  id: string;
  name: string;
  organization: string;
  exam_type: ExamType;
  description: string | null;
  registration_start: string | null;
  registration_end: string | null;
  exam_date: string | null;
  min_cgpa: number | null;
  max_backlogs: number | null;
  eligible_degrees: string[] | null;
  eligible_branches: string[] | null;
  graduation_year_min: number | null;
  graduation_year_max: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExamDetail extends Exam {
  syllabus: string | null;
  cutoffs: Record<string, unknown> | null;
  resources: Array<{ title: string; url: string }> | null;
  source_url: string | null;
  is_bookmarked: boolean;
  is_applied: boolean;
  application_status: ApplicationStatus | null;
}

export interface ExamFilters {
  exam_type?: ExamType;
  degree?: string;
  branch?: string;
  graduation_year?: number;
  cgpa?: number;
  backlogs?: number;
  search?: string;
  upcoming_only?: boolean;
}

// ============================================================================
// Bookmark Types
// ============================================================================

export interface ExamBookmark {
  id: string;
  user_id: string;
  exam_id: string;
  created_at: string;
  exam?: Exam;
}

// ============================================================================
// Application Types
// ============================================================================

export interface ExamApplication {
  id: string;
  user_id: string;
  exam_id: string;
  status: ApplicationStatus;
  applied_date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
  exam?: Exam;
}

// ============================================================================
// Calendar Types
// ============================================================================

export interface CalendarAuthURL {
  auth_url: string;
}

export interface CalendarStatus {
  is_connected: boolean;
  email: string | null;
  connected_at: string | null;
}

export interface CalendarSyncStatus {
  is_synced: boolean;
  google_event_id: string | null;
  synced_at: string | null;
}

export interface CalendarEvent {
  id: string;
  google_event_id: string;
  exam_id: string;
  synced_at: string;
}

// ============================================================================
// Response Types
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExamsByType {
  exam_type: ExamType;
  exams: Exam[];
  count: number;
}

export interface ExamFeedGroupedResponse {
  groups: ExamsByType[];
  total_exams: number;
}

// ============================================================================
// API Functions
// ============================================================================

export const examApi = {
  // Exam Feed
  getFeed: async (
    filters?: ExamFilters,
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<Exam>> => {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
    };
    if (filters?.exam_type) params.exam_type = filters.exam_type;
    if (filters?.degree) params.degree = filters.degree;
    if (filters?.branch) params.branch = filters.branch;
    if (filters?.graduation_year) params.graduation_year = String(filters.graduation_year);
    if (filters?.cgpa !== undefined) params.cgpa = String(filters.cgpa);
    if (filters?.backlogs !== undefined) params.backlogs = String(filters.backlogs);
    if (filters?.search) params.search = filters.search;
    if (filters?.upcoming_only !== undefined) params.upcoming_only = String(filters.upcoming_only);
    return apiClient.get<PaginatedResponse<Exam>>("/api/v1/exams/feed", { params });
  },

  getFeedGrouped: async (filters?: ExamFilters): Promise<ExamFeedGroupedResponse> => {
    const params: Record<string, string> = {};
    if (filters?.degree) params.degree = filters.degree;
    if (filters?.branch) params.branch = filters.branch;
    if (filters?.graduation_year) params.graduation_year = String(filters.graduation_year);
    if (filters?.cgpa !== undefined) params.cgpa = String(filters.cgpa);
    if (filters?.backlogs !== undefined) params.backlogs = String(filters.backlogs);
    return apiClient.get<ExamFeedGroupedResponse>("/api/v1/exams/feed/grouped", { params });
  },

  getExamDetails: async (examId: string): Promise<ExamDetail> => {
    return apiClient.get<ExamDetail>(`/api/v1/exams/${examId}`);
  },

  // Bookmarks
  bookmarkExam: async (examId: string): Promise<ExamBookmark> => {
    return apiClient.post<ExamBookmark>("/api/v1/exams/bookmarks", { exam_id: examId });
  },

  removeBookmark: async (examId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/exams/bookmarks/${examId}`);
  },

  getBookmarks: async (
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<ExamBookmark>> => {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
    };
    return apiClient.get<PaginatedResponse<ExamBookmark>>("/api/v1/exams/bookmarks", { params });
  },

  // Applications
  markApplied: async (
    examId: string,
    appliedDate?: string,
    notes?: string
  ): Promise<ExamApplication> => {
    return apiClient.post<ExamApplication>("/api/v1/exams/applications", {
      exam_id: examId,
      applied_date: appliedDate,
      notes,
    });
  },

  updateApplication: async (
    applicationId: string,
    data: { status?: ApplicationStatus; notes?: string }
  ): Promise<ExamApplication> => {
    return apiClient.put<ExamApplication>(`/api/v1/exams/applications/${applicationId}`, data);
  },

  deleteApplication: async (applicationId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/exams/applications/${applicationId}`);
  },

  getApplications: async (
    status?: ApplicationStatus,
    page: number = 1,
    pageSize: number = 20
  ): Promise<PaginatedResponse<ExamApplication>> => {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
    };
    if (status) params.status = status;
    return apiClient.get<PaginatedResponse<ExamApplication>>("/api/v1/exams/applications", {
      params,
    });
  },

  // Calendar Integration
  getCalendarAuthUrl: async (): Promise<CalendarAuthURL> => {
    return apiClient.get<CalendarAuthURL>("/api/v1/exams/calendar/auth");
  },

  handleCalendarCallback: async (code: string): Promise<{ success: boolean }> => {
    return apiClient.post<{ success: boolean }>("/api/v1/exams/calendar/callback", { code });
  },

  getCalendarStatus: async (): Promise<CalendarStatus> => {
    return apiClient.get<CalendarStatus>("/api/v1/exams/calendar/status");
  },

  disconnectCalendar: async (): Promise<void> => {
    return apiClient.delete("/api/v1/exams/calendar/disconnect");
  },

  syncToCalendar: async (examId: string): Promise<CalendarEvent> => {
    return apiClient.post<CalendarEvent>(`/api/v1/exams/calendar/sync/${examId}`);
  },

  updateCalendarEvent: async (examId: string): Promise<CalendarEvent> => {
    return apiClient.put<CalendarEvent>(`/api/v1/exams/calendar/sync/${examId}`);
  },

  removeFromCalendar: async (examId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/exams/calendar/sync/${examId}`);
  },

  getCalendarSyncStatus: async (examId: string): Promise<CalendarSyncStatus> => {
    return apiClient.get<CalendarSyncStatus>(`/api/v1/exams/calendar/sync/${examId}`);
  },
};

// ============================================================================
// Constants
// ============================================================================

export const EXAM_TYPES: { value: ExamType; label: string; color: string }[] = [
  { value: "campus_placement", label: "Campus Placement", color: "bg-blue-500" },
  { value: "off_campus", label: "Off-Campus", color: "bg-purple-500" },
  { value: "internship", label: "Internship", color: "bg-green-500" },
  { value: "higher_education", label: "Higher Education", color: "bg-orange-500" },
  { value: "government", label: "Government", color: "bg-red-500" },
  { value: "scholarship", label: "Scholarship", color: "bg-yellow-500" },
];

export const APPLICATION_STATUSES: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "interested", label: "Interested", color: "bg-gray-500" },
  { value: "applied", label: "Applied", color: "bg-blue-500" },
  { value: "appeared", label: "Appeared", color: "bg-purple-500" },
  { value: "result_pending", label: "Result Pending", color: "bg-yellow-500" },
  { value: "selected", label: "Selected", color: "bg-green-500" },
  { value: "not_selected", label: "Not Selected", color: "bg-red-500" },
];

export const COMMON_DEGREES = [
  "B.Tech",
  "B.E.",
  "B.Sc",
  "BCA",
  "M.Tech",
  "M.E.",
  "M.Sc",
  "MCA",
  "MBA",
  "Ph.D",
];

export const COMMON_BRANCHES = [
  "Computer Science",
  "Information Technology",
  "Electronics",
  "Electrical",
  "Mechanical",
  "Civil",
  "Chemical",
  "Biotechnology",
];
