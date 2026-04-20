import { create } from "zustand";
import {
  careerApi,
  Skill,
  SkillWithHistory,
  SkillsGroupedResponse,
  SkillSuggestionsResponse,
  SkillCategory,
  ProficiencyLevel,
  Course,
  CourseWithSessions,
  LearningStats,
  InactiveCourse,
  JobApplication,
  JobApplicationWithHistory,
  KanbanBoardResponse,
  ApplicationStatistics,
  StaleApplication,
  ApplicationStatus,
  ApplicationSource,
  Resume,
  ResumeSummary,
  ResumeTemplatesResponse,
  ResumeVersion,
  ResumeTemplate,
} from "@/lib/api/career";

interface CareerState {
  // Skills
  skills: Skill[];
  skillsGrouped: SkillsGroupedResponse | null;
  selectedSkill: SkillWithHistory | null;
  skillSuggestions: SkillSuggestionsResponse | null;
  skillsTotal: number;
  skillsLoading: boolean;
  skillsError: string | null;

  // Courses
  courses: Course[];
  selectedCourse: CourseWithSessions | null;
  learningStats: LearningStats | null;
  inactiveCourses: InactiveCourse[];
  coursesTotal: number;
  coursesLoading: boolean;
  coursesError: string | null;

  // Job Applications
  applications: JobApplication[];
  selectedApplication: JobApplicationWithHistory | null;
  kanbanBoard: KanbanBoardResponse | null;
  applicationStats: ApplicationStatistics | null;
  staleApplications: StaleApplication[];
  applicationsTotal: number;
  applicationsLoading: boolean;
  applicationsError: string | null;

  // Resumes
  resumes: ResumeSummary[];
  selectedResume: Resume | null;
  resumeTemplates: ResumeTemplatesResponse | null;
  resumeVersions: ResumeVersion[];
  resumesTotal: number;
  resumesLoading: boolean;
  resumesError: string | null;

  // Skill Actions
  fetchSkills: (params?: {
    category?: SkillCategory;
    proficiency?: ProficiencyLevel;
    page?: number;
  }) => Promise<void>;
  fetchSkillsGrouped: () => Promise<void>;
  fetchSkillSuggestions: (roles?: string[]) => Promise<void>;
  fetchSkill: (skillId: string) => Promise<void>;
  createSkill: (data: {
    name: string;
    category?: SkillCategory;
    proficiency?: ProficiencyLevel;
  }) => Promise<Skill>;
  updateSkill: (
    skillId: string,
    data: Partial<{ name: string; category: SkillCategory; proficiency: ProficiencyLevel }>
  ) => Promise<void>;
  deleteSkill: (skillId: string) => Promise<void>;

  // Course Actions
  fetchCourses: (params?: { is_completed?: boolean; page?: number }) => Promise<void>;
  fetchCourse: (courseId: string) => Promise<void>;
  fetchLearningStats: () => Promise<void>;
  fetchInactiveCourses: (days?: number) => Promise<void>;
  createCourse: (data: {
    title: string;
    platform?: string;
    url?: string;
    total_hours?: number;
  }) => Promise<Course>;
  updateCourse: (
    courseId: string,
    data: Partial<{ title: string; platform: string; url: string; total_hours: number }>
  ) => Promise<void>;
  deleteCourse: (courseId: string) => Promise<void>;
  logLearningSession: (
    courseId: string,
    data: { duration_minutes: number; notes?: string }
  ) => Promise<void>;
  updateCourseProgress: (courseId: string, percentage: number) => Promise<void>;
  markCourseComplete: (courseId: string) => Promise<void>;

  // Job Application Actions
  fetchApplications: (params?: {
    status?: ApplicationStatus;
    source?: ApplicationSource;
    page?: number;
  }) => Promise<void>;
  fetchKanbanBoard: () => Promise<void>;
  fetchApplicationStats: () => Promise<void>;
  fetchStaleApplications: (days?: number) => Promise<void>;
  fetchApplication: (applicationId: string) => Promise<void>;
  createApplication: (data: {
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
  }) => Promise<JobApplication>;
  updateApplication: (
    applicationId: string,
    data: Partial<{
      company: string;
      role: string;
      url: string;
      source: ApplicationSource;
      salary_min: number;
      salary_max: number;
      notes: string;
      location: string;
      is_remote: boolean;
    }>
  ) => Promise<void>;
  updateApplicationStatus: (
    applicationId: string,
    status: ApplicationStatus,
    notes?: string
  ) => Promise<void>;
  deleteApplication: (applicationId: string) => Promise<void>;

  // Resume Actions
  fetchTemplates: () => Promise<void>;
  fetchResumes: (params?: { template?: ResumeTemplate; page?: number }) => Promise<void>;
  fetchResume: (resumeId: string) => Promise<void>;
  createResume: (data: {
    name: string;
    template?: ResumeTemplate;
    populate_from_profile?: boolean;
  }) => Promise<Resume>;
  updateResume: (
    resumeId: string,
    data: Partial<{ name: string; template: ResumeTemplate; content: Resume["content"] }>
  ) => Promise<void>;
  deleteResume: (resumeId: string) => Promise<void>;
  populateResume: (resumeId: string) => Promise<void>;
  fetchResumeVersions: (resumeId: string) => Promise<void>;
  exportResumePdf: (resumeId: string) => Promise<void>;

  // Clear selections
  clearSelection: () => void;
}

export const useCareerStore = create<CareerState>((set, get) => ({
  // Initial state
  skills: [],
  skillsGrouped: null,
  selectedSkill: null,
  skillSuggestions: null,
  skillsTotal: 0,
  skillsLoading: false,
  skillsError: null,

  courses: [],
  selectedCourse: null,
  learningStats: null,
  inactiveCourses: [],
  coursesTotal: 0,
  coursesLoading: false,
  coursesError: null,

  applications: [],
  selectedApplication: null,
  kanbanBoard: null,
  applicationStats: null,
  staleApplications: [],
  applicationsTotal: 0,
  applicationsLoading: false,
  applicationsError: null,

  resumes: [],
  selectedResume: null,
  resumeTemplates: null,
  resumeVersions: [],
  resumesTotal: 0,
  resumesLoading: false,
  resumesError: null,

  // Skill Actions
  fetchSkills: async (params) => {
    set({ skillsLoading: true, skillsError: null });
    try {
      const response = await careerApi.getSkills(params);
      set({ skills: response.items, skillsTotal: response.total, skillsLoading: false });
    } catch (error) {
      set({
        skillsError: error instanceof Error ? error.message : "Failed to fetch skills",
        skillsLoading: false,
      });
    }
  },

  fetchSkillsGrouped: async () => {
    set({ skillsLoading: true, skillsError: null });
    try {
      const response = await careerApi.getSkillsGrouped();
      set({ skillsGrouped: response, skillsLoading: false });
    } catch (error) {
      set({
        skillsError: error instanceof Error ? error.message : "Failed to fetch skills",
        skillsLoading: false,
      });
    }
  },

  fetchSkillSuggestions: async (roles) => {
    try {
      const response = await careerApi.getSkillSuggestions(roles);
      set({ skillSuggestions: response });
    } catch (error) {
      console.error("Failed to fetch skill suggestions:", error);
    }
  },

  fetchSkill: async (skillId) => {
    try {
      const skill = await careerApi.getSkill(skillId);
      set({ selectedSkill: skill });
    } catch (error) {
      console.error("Failed to fetch skill:", error);
    }
  },

  createSkill: async (data) => {
    const skill = await careerApi.createSkill(data);
    set((state) => ({ skills: [skill, ...state.skills] }));
    // Refresh grouped view
    get().fetchSkillsGrouped();
    return skill;
  },

  updateSkill: async (skillId, data) => {
    const updated = await careerApi.updateSkill(skillId, data);
    set((state) => ({
      skills: state.skills.map((s) => (s.id === skillId ? updated : s)),
      selectedSkill: state.selectedSkill?.id === skillId ? { ...state.selectedSkill, ...updated } : state.selectedSkill,
    }));
    // Refresh grouped view
    get().fetchSkillsGrouped();
  },

  deleteSkill: async (skillId) => {
    await careerApi.deleteSkill(skillId);
    set((state) => ({
      skills: state.skills.filter((s) => s.id !== skillId),
      selectedSkill: state.selectedSkill?.id === skillId ? null : state.selectedSkill,
    }));
    // Refresh grouped view
    get().fetchSkillsGrouped();
  },

  // Course Actions
  fetchCourses: async (params) => {
    set({ coursesLoading: true, coursesError: null });
    try {
      const response = await careerApi.getCourses(params);
      set({ courses: response.items, coursesTotal: response.total, coursesLoading: false });
    } catch (error) {
      set({
        coursesError: error instanceof Error ? error.message : "Failed to fetch courses",
        coursesLoading: false,
      });
    }
  },

  fetchCourse: async (courseId) => {
    try {
      const course = await careerApi.getCourse(courseId);
      set({ selectedCourse: course });
    } catch (error) {
      console.error("Failed to fetch course:", error);
    }
  },

  fetchLearningStats: async () => {
    try {
      const stats = await careerApi.getLearningStats();
      set({ learningStats: stats });
    } catch (error) {
      console.error("Failed to fetch learning stats:", error);
    }
  },

  fetchInactiveCourses: async (days) => {
    try {
      const courses = await careerApi.getInactiveCourses(days);
      set({ inactiveCourses: courses });
    } catch (error) {
      console.error("Failed to fetch inactive courses:", error);
    }
  },

  createCourse: async (data) => {
    const course = await careerApi.createCourse(data);
    set((state) => ({ courses: [course, ...state.courses] }));
    get().fetchLearningStats();
    return course;
  },

  updateCourse: async (courseId, data) => {
    const updated = await careerApi.updateCourse(courseId, data);
    set((state) => ({
      courses: state.courses.map((c) => (c.id === courseId ? updated : c)),
      selectedCourse: state.selectedCourse?.id === courseId ? { ...state.selectedCourse, ...updated } : state.selectedCourse,
    }));
  },

  deleteCourse: async (courseId) => {
    await careerApi.deleteCourse(courseId);
    set((state) => ({
      courses: state.courses.filter((c) => c.id !== courseId),
      selectedCourse: state.selectedCourse?.id === courseId ? null : state.selectedCourse,
    }));
    get().fetchLearningStats();
  },

  logLearningSession: async (courseId, data) => {
    await careerApi.logLearningSession(courseId, data);
    // Refresh course and stats
    const updated = await careerApi.getCourse(courseId);
    set((state) => ({
      courses: state.courses.map((c) => (c.id === courseId ? { ...c, ...updated } : c)),
      selectedCourse: state.selectedCourse?.id === courseId ? updated : state.selectedCourse,
    }));
    get().fetchLearningStats();
  },

  updateCourseProgress: async (courseId, percentage) => {
    const updated = await careerApi.updateCourseProgress(courseId, percentage);
    set((state) => ({
      courses: state.courses.map((c) => (c.id === courseId ? updated : c)),
      selectedCourse: state.selectedCourse?.id === courseId ? { ...state.selectedCourse, ...updated } : state.selectedCourse,
    }));
  },

  markCourseComplete: async (courseId) => {
    const updated = await careerApi.markCourseComplete(courseId);
    set((state) => ({
      courses: state.courses.map((c) => (c.id === courseId ? updated : c)),
      selectedCourse: state.selectedCourse?.id === courseId ? { ...state.selectedCourse, ...updated } : state.selectedCourse,
    }));
    get().fetchLearningStats();
  },

  // Job Application Actions
  fetchApplications: async (params) => {
    set({ applicationsLoading: true, applicationsError: null });
    try {
      const response = await careerApi.getApplications(params);
      set({
        applications: response.items,
        applicationsTotal: response.total,
        applicationsLoading: false,
      });
    } catch (error) {
      set({
        applicationsError: error instanceof Error ? error.message : "Failed to fetch applications",
        applicationsLoading: false,
      });
    }
  },

  fetchKanbanBoard: async () => {
    set({ applicationsLoading: true, applicationsError: null });
    try {
      const board = await careerApi.getKanbanBoard();
      set({ kanbanBoard: board, applicationsLoading: false });
    } catch (error) {
      set({
        applicationsError: error instanceof Error ? error.message : "Failed to fetch kanban board",
        applicationsLoading: false,
      });
    }
  },

  fetchApplicationStats: async () => {
    try {
      const stats = await careerApi.getApplicationStatistics();
      set({ applicationStats: stats });
    } catch (error) {
      console.error("Failed to fetch application stats:", error);
    }
  },

  fetchStaleApplications: async (days) => {
    try {
      const applications = await careerApi.getStaleApplications(days);
      set({ staleApplications: applications });
    } catch (error) {
      console.error("Failed to fetch stale applications:", error);
    }
  },

  fetchApplication: async (applicationId) => {
    try {
      const application = await careerApi.getApplication(applicationId);
      set({ selectedApplication: application });
    } catch (error) {
      console.error("Failed to fetch application:", error);
    }
  },

  createApplication: async (data) => {
    const application = await careerApi.createApplication(data);
    set((state) => ({ applications: [application, ...state.applications] }));
    // Refresh kanban and stats
    get().fetchKanbanBoard();
    get().fetchApplicationStats();
    return application;
  },

  updateApplication: async (applicationId, data) => {
    const updated = await careerApi.updateApplication(applicationId, data);
    set((state) => ({
      applications: state.applications.map((a) => (a.id === applicationId ? updated : a)),
      selectedApplication:
        state.selectedApplication?.id === applicationId
          ? { ...state.selectedApplication, ...updated }
          : state.selectedApplication,
    }));
    get().fetchKanbanBoard();
  },

  updateApplicationStatus: async (applicationId, status, notes) => {
    const updated = await careerApi.updateApplicationStatus(applicationId, status, notes);
    set((state) => ({
      applications: state.applications.map((a) => (a.id === applicationId ? updated : a)),
      selectedApplication:
        state.selectedApplication?.id === applicationId
          ? { ...state.selectedApplication, ...updated }
          : state.selectedApplication,
    }));
    // Refresh kanban and stats
    get().fetchKanbanBoard();
    get().fetchApplicationStats();
  },

  deleteApplication: async (applicationId) => {
    await careerApi.deleteApplication(applicationId);
    set((state) => ({
      applications: state.applications.filter((a) => a.id !== applicationId),
      selectedApplication:
        state.selectedApplication?.id === applicationId ? null : state.selectedApplication,
    }));
    get().fetchKanbanBoard();
    get().fetchApplicationStats();
  },

  // Resume Actions
  fetchTemplates: async () => {
    try {
      const templates = await careerApi.getTemplates();
      set({ resumeTemplates: templates });
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    }
  },

  fetchResumes: async (params) => {
    set({ resumesLoading: true, resumesError: null });
    try {
      const response = await careerApi.getResumes(params);
      set({ resumes: response.items, resumesTotal: response.total, resumesLoading: false });
    } catch (error) {
      set({
        resumesError: error instanceof Error ? error.message : "Failed to fetch resumes",
        resumesLoading: false,
      });
    }
  },

  fetchResume: async (resumeId) => {
    try {
      const resume = await careerApi.getResume(resumeId);
      set({ selectedResume: resume });
    } catch (error) {
      console.error("Failed to fetch resume:", error);
    }
  },

  createResume: async (data) => {
    const resume = await careerApi.createResume(data);
    set((state) => ({
      resumes: [
        {
          id: resume.id,
          name: resume.name,
          template: resume.template,
          version: resume.version,
          pdf_url: resume.pdf_url,
          created_at: resume.created_at,
          updated_at: resume.updated_at,
        },
        ...state.resumes,
      ],
    }));
    return resume;
  },

  updateResume: async (resumeId, data) => {
    const updated = await careerApi.updateResume(resumeId, data);
    set((state) => ({
      resumes: state.resumes.map((r) =>
        r.id === resumeId
          ? {
              ...r,
              name: updated.name,
              template: updated.template,
              version: updated.version,
              updated_at: updated.updated_at,
            }
          : r
      ),
      selectedResume: state.selectedResume?.id === resumeId ? updated : state.selectedResume,
    }));
  },

  deleteResume: async (resumeId) => {
    await careerApi.deleteResume(resumeId);
    set((state) => ({
      resumes: state.resumes.filter((r) => r.id !== resumeId),
      selectedResume: state.selectedResume?.id === resumeId ? null : state.selectedResume,
    }));
  },

  populateResume: async (resumeId) => {
    const updated = await careerApi.populateResume(resumeId, {});
    set((state) => ({
      selectedResume: state.selectedResume?.id === resumeId ? updated : state.selectedResume,
    }));
  },

  fetchResumeVersions: async (resumeId) => {
    try {
      const versions = await careerApi.getResumeVersions(resumeId);
      set({ resumeVersions: versions });
    } catch (error) {
      console.error("Failed to fetch resume versions:", error);
    }
  },

  exportResumePdf: async (resumeId) => {
    const blob = await careerApi.exportResumePdf(resumeId);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume.pdf";
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  clearSelection: () => {
    set({
      selectedSkill: null,
      selectedCourse: null,
      selectedApplication: null,
      selectedResume: null,
    });
  },
}));
