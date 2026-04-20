import { apiClient } from "./client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================================
// Enums
// ============================================================================

export type ProficiencyLevel = "beginner" | "intermediate" | "advanced" | "expert";

export type SkillCategory =
  | "programming"
  | "framework"
  | "database"
  | "devops"
  | "cloud"
  | "soft_skill"
  | "language"
  | "design"
  | "data_science"
  | "other";

export type ApplicationStatus =
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export type ApplicationSource =
  | "linkedin"
  | "indeed"
  | "company_website"
  | "referral"
  | "recruiter"
  | "job_board"
  | "networking"
  | "other";

export type ResumeTemplate =
  | "classic"
  | "modern"
  | "minimal"
  | "professional"
  | "creative";

// ============================================================================
// Skill Types
// ============================================================================

export interface Skill {
  id: string;
  user_id: string;
  name: string;
  category: SkillCategory;
  proficiency: ProficiencyLevel;
  created_at: string;
  updated_at: string;
}

export interface SkillProficiencyHistory {
  id: string;
  skill_id: string;
  previous_level: ProficiencyLevel | null;
  new_level: ProficiencyLevel;
  changed_at: string;
}

export interface SkillWithHistory extends Skill {
  proficiency_history: SkillProficiencyHistory[];
}

export interface SkillSuggestion {
  name: string;
  category: string;
  reason: string;
}

export interface SkillsByCategory {
  category: SkillCategory;
  skills: Skill[];
}

export interface SkillsGroupedResponse {
  groups: SkillsByCategory[];
  total_skills: number;
}

export interface SkillSuggestionsResponse {
  suggestions: SkillSuggestion[];
  based_on_roles: string[];
}

// ============================================================================
// Course Types
// ============================================================================

export interface Course {
  id: string;
  user_id: string;
  title: string;
  platform: string | null;
  url: string | null;
  total_hours: number;
  completed_hours: number;
  completion_percentage: number;
  is_completed: boolean;
  last_activity_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearningSession {
  id: string;
  course_id: string;
  session_date: string;
  duration_minutes: number;
  notes: string | null;
  created_at: string;
}

export interface CourseWithSessions extends Course {
  learning_sessions: LearningSession[];
}

export interface LearningStats {
  total_courses: number;
  completed_courses: number;
  in_progress_courses: number;
  total_hours_invested: number;
  current_streak_days: number;
  longest_streak_days: number;
}

export interface InactiveCourse {
  course_id: string;
  title: string;
  platform: string | null;
  days_inactive: number;
  last_activity_at: string | null;
  completion_percentage: number;
}

// ============================================================================
// Job Application Types
// ============================================================================

export interface JobApplication {
  id: string;
  user_id: string;
  company: string;
  role: string;
  url: string | null;
  source: ApplicationSource;
  status: ApplicationStatus;
  salary_min: number | null;
  salary_max: number | null;
  applied_date: string;
  notes: string | null;
  location: string | null;
  is_remote: boolean;
  last_status_update: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationStatusHistory {
  id: string;
  application_id: string;
  previous_status: ApplicationStatus | null;
  new_status: ApplicationStatus;
  changed_at: string;
  notes: string | null;
}

export interface FollowUpReminder {
  id: string;
  application_id: string;
  reminder_date: string;
  is_sent: boolean;
  sent_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface JobApplicationWithHistory extends JobApplication {
  status_history: ApplicationStatusHistory[];
  follow_up_reminders: FollowUpReminder[];
}

export interface KanbanColumn {
  status: ApplicationStatus;
  applications: JobApplication[];
  count: number;
}

export interface KanbanBoardResponse {
  columns: KanbanColumn[];
  total_applications: number;
}

export interface ApplicationStatistics {
  total_applications: number;
  by_status: Record<string, number>;
  response_rate: number;
  average_days_to_response: number | null;
  applications_this_month: number;
  applications_this_week: number;
  offer_rate: number;
  rejection_rate: number;
}

export interface StaleApplication {
  application_id: string;
  company: string;
  role: string;
  status: ApplicationStatus;
  days_since_update: number;
  last_status_update: string;
  applied_date: string;
}

// ============================================================================
// Resume Types
// ============================================================================

export interface PersonalInfo {
  full_name: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  gpa?: string;
  description?: string;
}

export interface ExperienceEntry {
  company: string;
  role: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
  highlights: string[];
}

export interface SkillEntry {
  name: string;
  category?: string;
  proficiency?: string;
}

export interface AchievementEntry {
  title: string;
  description?: string;
  achieved_date?: string;
  category?: string;
}

export interface ResumeContent {
  personal_info?: PersonalInfo;
  summary?: string;
  education: EducationEntry[];
  experience: ExperienceEntry[];
  skills: SkillEntry[];
  achievements: AchievementEntry[];
  certifications: { name: string; issuer?: string; issue_date?: string }[];
  projects: { name: string; description?: string; technologies: string[] }[];
  custom_sections: { title: string; content: string }[];
}

export interface Resume {
  id: string;
  user_id: string;
  name: string;
  template: ResumeTemplate;
  content: ResumeContent;
  pdf_url: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ResumeSummary {
  id: string;
  name: string;
  template: ResumeTemplate;
  version: number;
  pdf_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResumeVersion {
  id: string;
  resume_id: string;
  version_number: number;
  content: ResumeContent;
  pdf_url: string | null;
  created_at: string;
}

export interface ResumeTemplateInfo {
  id: ResumeTemplate;
  name: string;
  description: string;
  preview_url: string | null;
}

export interface ResumeTemplatesResponse {
  templates: ResumeTemplateInfo[];
}

// ============================================================================
// Paginated Response
// ============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================================
// API Functions
// ============================================================================

export const careerApi = {
  // Skills
  getSkills: async (params?: {
    category?: SkillCategory;
    proficiency?: ProficiencyLevel;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Skill>> => {
    const queryParams: Record<string, string> = {};
    if (params?.category) queryParams.category = params.category;
    if (params?.proficiency) queryParams.proficiency = params.proficiency;
    if (params?.page) queryParams.page = String(params.page);
    if (params?.page_size) queryParams.page_size = String(params.page_size);
    return apiClient.get<PaginatedResponse<Skill>>("/api/v1/career/skills", { params: queryParams });
  },

  getSkillsGrouped: async (): Promise<SkillsGroupedResponse> => {
    return apiClient.get<SkillsGroupedResponse>("/api/v1/career/skills/grouped");
  },

  getSkillSuggestions: async (roles?: string[]): Promise<SkillSuggestionsResponse> => {
    const params: Record<string, string> = {};
    if (roles?.length) params.roles = roles.join(",");
    return apiClient.get<SkillSuggestionsResponse>("/api/v1/career/skills/suggestions", { params });
  },

  getSkill: async (skillId: string): Promise<SkillWithHistory> => {
    return apiClient.get<SkillWithHistory>(`/api/v1/career/skills/${skillId}`);
  },

  createSkill: async (data: {
    name: string;
    category?: SkillCategory;
    proficiency?: ProficiencyLevel;
  }): Promise<Skill> => {
    return apiClient.post<Skill>("/api/v1/career/skills", data);
  },

  updateSkill: async (
    skillId: string,
    data: Partial<{ name: string; category: SkillCategory; proficiency: ProficiencyLevel }>
  ): Promise<Skill> => {
    return apiClient.put<Skill>(`/api/v1/career/skills/${skillId}`, data);
  },

  deleteSkill: async (skillId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/career/skills/${skillId}`);
  },

  // Courses
  getCourses: async (params?: {
    is_completed?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Course>> => {
    const queryParams: Record<string, string> = {};
    if (params?.is_completed !== undefined) queryParams.is_completed = String(params.is_completed);
    if (params?.page) queryParams.page = String(params.page);
    if (params?.page_size) queryParams.page_size = String(params.page_size);
    return apiClient.get<PaginatedResponse<Course>>("/api/v1/career/courses", { params: queryParams });
  },

  getCourse: async (courseId: string): Promise<CourseWithSessions> => {
    return apiClient.get<CourseWithSessions>(`/api/v1/career/courses/${courseId}`);
  },

  getLearningStats: async (): Promise<LearningStats> => {
    return apiClient.get<LearningStats>("/api/v1/career/courses/stats");
  },

  getInactiveCourses: async (days?: number): Promise<InactiveCourse[]> => {
    const params: Record<string, string> = {};
    if (days) params.days = String(days);
    return apiClient.get<InactiveCourse[]>("/api/v1/career/courses/inactive", { params });
  },

  createCourse: async (data: {
    title: string;
    platform?: string;
    url?: string;
    total_hours?: number;
  }): Promise<Course> => {
    return apiClient.post<Course>("/api/v1/career/courses", data);
  },

  updateCourse: async (
    courseId: string,
    data: Partial<{ title: string; platform: string; url: string; total_hours: number }>
  ): Promise<Course> => {
    return apiClient.put<Course>(`/api/v1/career/courses/${courseId}`, data);
  },

  deleteCourse: async (courseId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/career/courses/${courseId}`);
  },

  logLearningSession: async (
    courseId: string,
    data: { session_date?: string; duration_minutes: number; notes?: string }
  ): Promise<LearningSession> => {
    return apiClient.post<LearningSession>(`/api/v1/career/courses/${courseId}/sessions`, data);
  },

  updateCourseProgress: async (
    courseId: string,
    completion_percentage: number
  ): Promise<Course> => {
    return apiClient.put<Course>(`/api/v1/career/courses/${courseId}/progress`, { completion_percentage });
  },

  markCourseComplete: async (courseId: string): Promise<Course> => {
    return apiClient.post<Course>(`/api/v1/career/courses/${courseId}/complete`);
  },

  // Job Applications
  getApplications: async (params?: {
    status?: ApplicationStatus;
    source?: ApplicationSource;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<JobApplication>> => {
    const queryParams: Record<string, string> = {};
    if (params?.status) queryParams.status = params.status;
    if (params?.source) queryParams.source = params.source;
    if (params?.page) queryParams.page = String(params.page);
    if (params?.page_size) queryParams.page_size = String(params.page_size);
    return apiClient.get<PaginatedResponse<JobApplication>>("/api/v1/career/job-applications", {
      params: queryParams,
    });
  },

  getKanbanBoard: async (): Promise<KanbanBoardResponse> => {
    return apiClient.get<KanbanBoardResponse>("/api/v1/career/job-applications/kanban");
  },

  getApplicationStatistics: async (): Promise<ApplicationStatistics> => {
    return apiClient.get<ApplicationStatistics>("/api/v1/career/job-applications/statistics");
  },

  getStaleApplications: async (days?: number): Promise<StaleApplication[]> => {
    const params: Record<string, string> = {};
    if (days) params.days = String(days);
    return apiClient.get<StaleApplication[]>("/api/v1/career/job-applications/stale", { params });
  },

  getApplication: async (applicationId: string): Promise<JobApplicationWithHistory> => {
    return apiClient.get<JobApplicationWithHistory>(`/api/v1/career/job-applications/${applicationId}`);
  },

  createApplication: async (data: {
    company: string;
    role: string;
    url?: string;
    source?: ApplicationSource;
    status?: ApplicationStatus;
    salary_min?: number;
    salary_max?: number;
    applied_date?: string;
    notes?: string;
    location?: string;
    is_remote?: boolean;
  }): Promise<JobApplication> => {
    return apiClient.post<JobApplication>("/api/v1/career/job-applications", data);
  },

  updateApplication: async (
    applicationId: string,
    data: Partial<{
      company: string;
      role: string;
      url: string;
      source: ApplicationSource;
      salary_min: number;
      salary_max: number;
      applied_date: string;
      notes: string;
      location: string;
      is_remote: boolean;
    }>
  ): Promise<JobApplication> => {
    return apiClient.put<JobApplication>(`/api/v1/career/job-applications/${applicationId}`, data);
  },

  updateApplicationStatus: async (
    applicationId: string,
    status: ApplicationStatus,
    notes?: string
  ): Promise<JobApplication> => {
    return apiClient.put<JobApplication>(`/api/v1/career/job-applications/${applicationId}/status`, {
      status,
      notes,
    });
  },

  deleteApplication: async (applicationId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/career/job-applications/${applicationId}`);
  },

  addFollowUpReminder: async (
    applicationId: string,
    data: { reminder_date: string; notes?: string }
  ): Promise<FollowUpReminder> => {
    return apiClient.post<FollowUpReminder>(
      `/api/v1/career/job-applications/${applicationId}/reminders`,
      data
    );
  },

  // Resumes
  getTemplates: async (): Promise<ResumeTemplatesResponse> => {
    return apiClient.get<ResumeTemplatesResponse>("/api/v1/career/resumes/templates");
  },

  getResumes: async (params?: {
    template?: ResumeTemplate;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<ResumeSummary>> => {
    const queryParams: Record<string, string> = {};
    if (params?.template) queryParams.template = params.template;
    if (params?.page) queryParams.page = String(params.page);
    if (params?.page_size) queryParams.page_size = String(params.page_size);
    return apiClient.get<PaginatedResponse<ResumeSummary>>("/api/v1/career/resumes", {
      params: queryParams,
    });
  },

  getResume: async (resumeId: string): Promise<Resume> => {
    return apiClient.get<Resume>(`/api/v1/career/resumes/${resumeId}`);
  },

  createResume: async (data: {
    name: string;
    template?: ResumeTemplate;
    content?: Partial<ResumeContent>;
    populate_from_profile?: boolean;
  }): Promise<Resume> => {
    return apiClient.post<Resume>("/api/v1/career/resumes", data);
  },

  updateResume: async (
    resumeId: string,
    data: Partial<{ name: string; template: ResumeTemplate; content: ResumeContent }>
  ): Promise<Resume> => {
    return apiClient.put<Resume>(`/api/v1/career/resumes/${resumeId}`, data);
  },

  deleteResume: async (resumeId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/career/resumes/${resumeId}`);
  },

  populateResume: async (
    resumeId: string,
    options: {
      include_education?: boolean;
      include_skills?: boolean;
      include_achievements?: boolean;
      include_experience?: boolean;
      max_achievements?: number;
      max_skills?: number;
    }
  ): Promise<Resume> => {
    return apiClient.post<Resume>(`/api/v1/career/resumes/${resumeId}/populate`, options);
  },

  getResumeVersions: async (resumeId: string): Promise<ResumeVersion[]> => {
    return apiClient.get<ResumeVersion[]>(`/api/v1/career/resumes/${resumeId}/versions`);
  },

  exportResumePdf: async (resumeId: string): Promise<Blob> => {
    const headers: HeadersInit = {};
    if (typeof window !== "undefined") {
      const authData = localStorage.getItem("lifepilot-auth");
      if (authData) {
        try {
          const { state } = JSON.parse(authData);
          if (state?.accessToken) {
            headers["Authorization"] = `Bearer ${state.accessToken}`;
          }
        } catch {
          // Ignore parse errors
        }
      }
    }

    const response = await fetch(
      `${API_BASE_URL}/api/v1/career/resumes/${resumeId}/pdf`,
      { headers }
    );

    if (!response.ok) {
      throw new Error("Failed to export PDF");
    }

    return response.blob();
  },
};

// ============================================================================
// Constants
// ============================================================================

export const PROFICIENCY_LEVELS: { value: ProficiencyLevel; label: string; color: string }[] = [
  { value: "beginner", label: "Beginner", color: "bg-gray-400" },
  { value: "intermediate", label: "Intermediate", color: "bg-blue-400" },
  { value: "advanced", label: "Advanced", color: "bg-green-500" },
  { value: "expert", label: "Expert", color: "bg-purple-500" },
];

export const SKILL_CATEGORIES: { value: SkillCategory; label: string }[] = [
  { value: "programming", label: "Programming" },
  { value: "framework", label: "Framework" },
  { value: "database", label: "Database" },
  { value: "devops", label: "DevOps" },
  { value: "cloud", label: "Cloud" },
  { value: "soft_skill", label: "Soft Skills" },
  { value: "language", label: "Language" },
  { value: "design", label: "Design" },
  { value: "data_science", label: "Data Science" },
  { value: "other", label: "Other" },
];

export const APPLICATION_STATUSES: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "applied", label: "Applied", color: "bg-blue-500" },
  { value: "screening", label: "Screening", color: "bg-yellow-500" },
  { value: "interview", label: "Interview", color: "bg-purple-500" },
  { value: "offer", label: "Offer", color: "bg-green-500" },
  { value: "rejected", label: "Rejected", color: "bg-red-500" },
  { value: "withdrawn", label: "Withdrawn", color: "bg-gray-500" },
];

export const APPLICATION_SOURCES: { value: ApplicationSource; label: string }[] = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "indeed", label: "Indeed" },
  { value: "company_website", label: "Company Website" },
  { value: "referral", label: "Referral" },
  { value: "recruiter", label: "Recruiter" },
  { value: "job_board", label: "Job Board" },
  { value: "networking", label: "Networking" },
  { value: "other", label: "Other" },
];

export const RESUME_TEMPLATES: { value: ResumeTemplate; label: string; description: string }[] = [
  { value: "classic", label: "Classic", description: "Traditional professional layout" },
  { value: "modern", label: "Modern", description: "Clean and contemporary design" },
  { value: "minimal", label: "Minimal", description: "Simple and elegant" },
  { value: "professional", label: "Professional", description: "Corporate-focused layout" },
  { value: "creative", label: "Creative", description: "Unique and eye-catching" },
];
