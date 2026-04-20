import { create } from "zustand";
import {
  examApi,
  Exam,
  ExamDetail,
  ExamFilters,
  ExamBookmark,
  ExamApplication,
  ApplicationStatus,
  CalendarStatus,
  CalendarSyncStatus,
  ExamFeedGroupedResponse,
} from "@/lib/api/exam";

interface ExamState {
  // Feed
  exams: Exam[];
  examsGrouped: ExamFeedGroupedResponse | null;
  selectedExam: ExamDetail | null;
  examsTotal: number;
  examsPage: number;
  examsLoading: boolean;
  examsError: string | null;
  filters: ExamFilters;

  // Bookmarks
  bookmarks: ExamBookmark[];
  bookmarksTotal: number;
  bookmarksLoading: boolean;

  // Applications
  applications: ExamApplication[];
  applicationsTotal: number;
  applicationsLoading: boolean;

  // Calendar
  calendarStatus: CalendarStatus | null;
  calendarSyncStatuses: Record<string, CalendarSyncStatus>;
  calendarLoading: boolean;

  // Feed Actions
  fetchExams: (filters?: ExamFilters, page?: number) => Promise<void>;
  fetchExamsGrouped: (filters?: ExamFilters) => Promise<void>;
  fetchExamDetails: (examId: string) => Promise<void>;
  setFilters: (filters: ExamFilters) => void;
  clearFilters: () => void;

  // Bookmark Actions
  fetchBookmarks: (page?: number) => Promise<void>;
  bookmarkExam: (examId: string) => Promise<void>;
  removeBookmark: (examId: string) => Promise<void>;
  toggleBookmark: (examId: string, isBookmarked: boolean) => Promise<void>;

  // Application Actions
  fetchApplications: (status?: ApplicationStatus, page?: number) => Promise<void>;
  markApplied: (examId: string, appliedDate?: string, notes?: string) => Promise<void>;
  updateApplication: (
    applicationId: string,
    data: { status?: ApplicationStatus; notes?: string }
  ) => Promise<void>;
  deleteApplication: (applicationId: string) => Promise<void>;

  // Calendar Actions
  fetchCalendarStatus: () => Promise<void>;
  getCalendarAuthUrl: () => Promise<string>;
  handleCalendarCallback: (code: string) => Promise<void>;
  disconnectCalendar: () => Promise<void>;
  syncToCalendar: (examId: string) => Promise<void>;
  removeFromCalendar: (examId: string) => Promise<void>;
  fetchCalendarSyncStatus: (examId: string) => Promise<void>;

  // Clear
  clearSelection: () => void;
}

export const useExamStore = create<ExamState>((set, get) => ({
  // Initial state
  exams: [],
  examsGrouped: null,
  selectedExam: null,
  examsTotal: 0,
  examsPage: 1,
  examsLoading: false,
  examsError: null,
  filters: { upcoming_only: true },

  bookmarks: [],
  bookmarksTotal: 0,
  bookmarksLoading: false,

  applications: [],
  applicationsTotal: 0,
  applicationsLoading: false,

  calendarStatus: null,
  calendarSyncStatuses: {},
  calendarLoading: false,

  // Feed Actions
  fetchExams: async (filters, page = 1) => {
    set({ examsLoading: true, examsError: null });
    try {
      const currentFilters = filters ?? get().filters;
      const response = await examApi.getFeed(currentFilters, page);
      set({
        exams: response.items,
        examsTotal: response.total,
        examsPage: page,
        examsLoading: false,
        filters: currentFilters,
      });
    } catch (error) {
      set({
        examsError: error instanceof Error ? error.message : "Failed to fetch exams",
        examsLoading: false,
      });
    }
  },

  fetchExamsGrouped: async (filters) => {
    set({ examsLoading: true, examsError: null });
    try {
      const currentFilters = filters ?? get().filters;
      const response = await examApi.getFeedGrouped(currentFilters);
      set({
        examsGrouped: response,
        examsLoading: false,
        filters: currentFilters,
      });
    } catch (error) {
      set({
        examsError: error instanceof Error ? error.message : "Failed to fetch exams",
        examsLoading: false,
      });
    }
  },

  fetchExamDetails: async (examId) => {
    try {
      const exam = await examApi.getExamDetails(examId);
      set({ selectedExam: exam });
    } catch (error) {
      console.error("Failed to fetch exam details:", error);
    }
  },

  setFilters: (filters) => {
    set({ filters: { ...get().filters, ...filters } });
  },

  clearFilters: () => {
    set({ filters: { upcoming_only: true } });
  },

  // Bookmark Actions
  fetchBookmarks: async (page = 1) => {
    set({ bookmarksLoading: true });
    try {
      const response = await examApi.getBookmarks(page);
      set({
        bookmarks: response.items,
        bookmarksTotal: response.total,
        bookmarksLoading: false,
      });
    } catch (error) {
      console.error("Failed to fetch bookmarks:", error);
      set({ bookmarksLoading: false });
    }
  },

  bookmarkExam: async (examId) => {
    try {
      const bookmark = await examApi.bookmarkExam(examId);
      set((state) => ({
        bookmarks: [bookmark, ...state.bookmarks],
        bookmarksTotal: state.bookmarksTotal + 1,
      }));
      // Update selected exam if viewing
      const { selectedExam } = get();
      if (selectedExam?.id === examId) {
        set({ selectedExam: { ...selectedExam, is_bookmarked: true } });
      }
    } catch (error) {
      console.error("Failed to bookmark exam:", error);
      throw error;
    }
  },

  removeBookmark: async (examId) => {
    try {
      await examApi.removeBookmark(examId);
      set((state) => ({
        bookmarks: state.bookmarks.filter((b) => b.exam_id !== examId),
        bookmarksTotal: Math.max(0, state.bookmarksTotal - 1),
      }));
      // Update selected exam if viewing
      const { selectedExam } = get();
      if (selectedExam?.id === examId) {
        set({ selectedExam: { ...selectedExam, is_bookmarked: false } });
      }
    } catch (error) {
      console.error("Failed to remove bookmark:", error);
      throw error;
    }
  },

  toggleBookmark: async (examId, isBookmarked) => {
    if (isBookmarked) {
      await get().removeBookmark(examId);
    } else {
      await get().bookmarkExam(examId);
    }
  },

  // Application Actions
  fetchApplications: async (status, page = 1) => {
    set({ applicationsLoading: true });
    try {
      const response = await examApi.getApplications(status, page);
      set({
        applications: response.items,
        applicationsTotal: response.total,
        applicationsLoading: false,
      });
    } catch (error) {
      console.error("Failed to fetch applications:", error);
      set({ applicationsLoading: false });
    }
  },

  markApplied: async (examId, appliedDate, notes) => {
    try {
      const application = await examApi.markApplied(examId, appliedDate, notes);
      set((state) => ({
        applications: [application, ...state.applications],
        applicationsTotal: state.applicationsTotal + 1,
      }));
      // Update selected exam if viewing
      const { selectedExam } = get();
      if (selectedExam?.id === examId) {
        set({
          selectedExam: {
            ...selectedExam,
            is_applied: true,
            application_status: application.status,
          },
        });
      }
    } catch (error) {
      console.error("Failed to mark as applied:", error);
      throw error;
    }
  },

  updateApplication: async (applicationId, data) => {
    try {
      const updated = await examApi.updateApplication(applicationId, data);
      set((state) => ({
        applications: state.applications.map((a) =>
          a.id === applicationId ? updated : a
        ),
      }));
    } catch (error) {
      console.error("Failed to update application:", error);
      throw error;
    }
  },

  deleteApplication: async (applicationId) => {
    try {
      await examApi.deleteApplication(applicationId);
      set((state) => ({
        applications: state.applications.filter((a) => a.id !== applicationId),
        applicationsTotal: Math.max(0, state.applicationsTotal - 1),
      }));
    } catch (error) {
      console.error("Failed to delete application:", error);
      throw error;
    }
  },

  // Calendar Actions
  fetchCalendarStatus: async () => {
    set({ calendarLoading: true });
    try {
      const status = await examApi.getCalendarStatus();
      set({ calendarStatus: status, calendarLoading: false });
    } catch (error) {
      console.error("Failed to fetch calendar status:", error);
      set({ calendarLoading: false });
    }
  },

  getCalendarAuthUrl: async () => {
    const response = await examApi.getCalendarAuthUrl();
    return response.auth_url;
  },

  handleCalendarCallback: async (code) => {
    try {
      await examApi.handleCalendarCallback(code);
      await get().fetchCalendarStatus();
    } catch (error) {
      console.error("Failed to handle calendar callback:", error);
      throw error;
    }
  },

  disconnectCalendar: async () => {
    try {
      await examApi.disconnectCalendar();
      set({ calendarStatus: { is_connected: false, email: null, connected_at: null } });
    } catch (error) {
      console.error("Failed to disconnect calendar:", error);
      throw error;
    }
  },

  syncToCalendar: async (examId) => {
    try {
      await examApi.syncToCalendar(examId);
      await get().fetchCalendarSyncStatus(examId);
    } catch (error) {
      console.error("Failed to sync to calendar:", error);
      throw error;
    }
  },

  removeFromCalendar: async (examId) => {
    try {
      await examApi.removeFromCalendar(examId);
      set((state) => {
        const newStatuses = { ...state.calendarSyncStatuses };
        delete newStatuses[examId];
        return { calendarSyncStatuses: newStatuses };
      });
    } catch (error) {
      console.error("Failed to remove from calendar:", error);
      throw error;
    }
  },

  fetchCalendarSyncStatus: async (examId) => {
    try {
      const status = await examApi.getCalendarSyncStatus(examId);
      set((state) => ({
        calendarSyncStatuses: {
          ...state.calendarSyncStatuses,
          [examId]: status,
        },
      }));
    } catch (error) {
      console.error("Failed to fetch calendar sync status:", error);
    }
  },

  clearSelection: () => {
    set({ selectedExam: null });
  },
}));
