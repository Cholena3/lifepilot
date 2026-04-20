import { create } from "zustand";
import {
  documentsApi,
  type Document,
  type ShareLink,
  type ShareLinkCreateResponse,
  type DocumentFilters,
  type PaginatedResponse,
} from "@/lib/api/documents";
import type { DocumentCategory } from "@/lib/validations/documents";

export interface DocumentState {
  documents: Document[];
  selectedDocument: Document | null;
  shareLinks: ShareLink[];
  currentShareLinkResponse: ShareLinkCreateResponse | null;
  isLoading: boolean;
  isUploading: boolean;
  error: string | null;
  filters: DocumentFilters;
  pagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
  searchQuery: string;
  searchResults: Document[];
  isSearching: boolean;
}

export interface DocumentActions {
  // Document CRUD
  fetchDocuments: (filters?: DocumentFilters) => Promise<void>;
  uploadDocument: (
    file: File,
    metadata: { title: string; category: DocumentCategory; expiry_date?: string | null }
  ) => Promise<Document>;
  uploadCameraCapture: (
    imageData: string,
    metadata: { title: string; category: DocumentCategory; expiry_date?: string | null }
  ) => Promise<Document>;
  deleteDocument: (documentId: string) => Promise<void>;
  selectDocument: (document: Document | null) => void;

  // Search
  searchDocuments: (query: string) => Promise<void>;
  clearSearch: () => void;

  // Filters
  setFilters: (filters: DocumentFilters) => void;
  setCategoryFilter: (category: DocumentCategory | undefined) => void;
  setPage: (page: number) => void;

  // Share links
  fetchShareLinks: (documentId: string) => Promise<void>;
  createShareLink: (
    documentId: string,
    options: { expires_in_hours: number; password?: string | null }
  ) => Promise<ShareLinkCreateResponse>;
  revokeShareLink: (documentId: string, linkId: string) => Promise<void>;
  clearShareLinkResponse: () => void;

  // Error handling
  clearError: () => void;
}

export type DocumentStore = DocumentState & DocumentActions;

const initialState: DocumentState = {
  documents: [],
  selectedDocument: null,
  shareLinks: [],
  currentShareLinkResponse: null,
  isLoading: false,
  isUploading: false,
  error: null,
  filters: {},
  pagination: {
    total: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
  },
  searchQuery: "",
  searchResults: [],
  isSearching: false,
};

export const useDocumentStore = create<DocumentStore>((set, get) => ({
  ...initialState,

  fetchDocuments: async (filters?: DocumentFilters) => {
    set({ isLoading: true, error: null });
    try {
      const currentFilters = filters || get().filters;
      const response: PaginatedResponse<Document> =
        await documentsApi.getDocuments(currentFilters);
      set({
        documents: response.items,
        pagination: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
        filters: currentFilters,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch documents",
        isLoading: false,
      });
    }
  },

  uploadDocument: async (file, metadata) => {
    set({ isUploading: true, error: null });
    try {
      const document = await documentsApi.uploadDocument(file, metadata);
      set((state) => ({
        documents: [document, ...state.documents],
        isUploading: false,
      }));
      return document;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to upload document",
        isUploading: false,
      });
      throw error;
    }
  },

  uploadCameraCapture: async (imageData, metadata) => {
    set({ isUploading: true, error: null });
    try {
      const document = await documentsApi.uploadCameraCapture(imageData, metadata);
      set((state) => ({
        documents: [document, ...state.documents],
        isUploading: false,
      }));
      return document;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to upload capture",
        isUploading: false,
      });
      throw error;
    }
  },

  deleteDocument: async (documentId) => {
    set({ isLoading: true, error: null });
    try {
      await documentsApi.deleteDocument(documentId);
      set((state) => ({
        documents: state.documents.filter((d) => d.id !== documentId),
        selectedDocument:
          state.selectedDocument?.id === documentId ? null : state.selectedDocument,
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete document",
        isLoading: false,
      });
      throw error;
    }
  },

  selectDocument: (document) => {
    set({ selectedDocument: document, shareLinks: [], currentShareLinkResponse: null });
  },

  searchDocuments: async (query) => {
    if (!query.trim()) {
      set({ searchResults: [], searchQuery: "", isSearching: false });
      return;
    }
    set({ isSearching: true, searchQuery: query, error: null });
    try {
      const results = await documentsApi.searchDocuments(query);
      set({ searchResults: results, isSearching: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Search failed",
        isSearching: false,
      });
    }
  },

  clearSearch: () => {
    set({ searchResults: [], searchQuery: "", isSearching: false });
  },

  setFilters: (filters) => {
    set({ filters });
    get().fetchDocuments(filters);
  },

  setCategoryFilter: (category) => {
    const newFilters = { ...get().filters, category, page: 1 };
    set({ filters: newFilters });
    get().fetchDocuments(newFilters);
  },

  setPage: (page) => {
    const newFilters = { ...get().filters, page };
    set({ filters: newFilters });
    get().fetchDocuments(newFilters);
  },

  fetchShareLinks: async (documentId) => {
    set({ isLoading: true, error: null });
    try {
      const shareLinks = await documentsApi.getShareLinks(documentId);
      set({ shareLinks, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch share links",
        isLoading: false,
      });
    }
  },

  createShareLink: async (documentId, options) => {
    set({ isLoading: true, error: null });
    try {
      const response = await documentsApi.createShareLink(documentId, options);
      set((state) => ({
        shareLinks: [response.share_link, ...state.shareLinks],
        currentShareLinkResponse: response,
        isLoading: false,
      }));
      return response;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create share link",
        isLoading: false,
      });
      throw error;
    }
  },

  revokeShareLink: async (documentId, linkId) => {
    set({ isLoading: true, error: null });
    try {
      await documentsApi.revokeShareLink(documentId, linkId);
      set((state) => ({
        shareLinks: state.shareLinks.filter((l) => l.id !== linkId),
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to revoke share link",
        isLoading: false,
      });
      throw error;
    }
  },

  clearShareLinkResponse: () => {
    set({ currentShareLinkResponse: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));
