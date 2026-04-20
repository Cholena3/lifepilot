import { apiClient } from "./client";
import type { DocumentCategory } from "@/lib/validations/documents";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Document {
  id: string;
  user_id: string;
  title: string;
  category: DocumentCategory;
  file_path: string;
  content_type: string;
  file_size: number;
  expiry_date: string | null;
  is_expired: boolean;
  ocr_text: string | null;
  extracted_fields: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  file_path: string;
  created_at: string;
}

export interface ShareLink {
  id: string;
  document_id: string;
  link_token: string;
  has_password: boolean;
  expires_at: string;
  is_revoked: boolean;
  created_at: string;
  access_count: number;
}

export interface ShareLinkAccess {
  id: string;
  share_link_id: string;
  ip_address: string;
  accessed_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentFilters {
  category?: DocumentCategory;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface ShareLinkCreateRequest {
  expires_in_hours: number;
  password?: string | null;
}

export interface ShareLinkCreateResponse {
  share_link: ShareLink;
  share_url: string;
  qr_code_data_url: string;
}

export const documentsApi = {
  // Upload document via file picker
  uploadDocument: async (
    file: File,
    metadata: { title: string; category: DocumentCategory; expiry_date?: string | null }
  ): Promise<Document> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", metadata.title);
    formData.append("category", metadata.category);
    if (metadata.expiry_date) {
      formData.append("expiry_date", metadata.expiry_date);
    }

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

    const response = await fetch(`${API_BASE_URL}/api/v1/documents/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to upload document");
    }

    return response.json();
  },

  // Upload document via camera capture (base64 image)
  uploadCameraCapture: async (
    imageData: string,
    metadata: { title: string; category: DocumentCategory; expiry_date?: string | null }
  ): Promise<Document> => {
    return apiClient.post<Document>("/api/v1/documents/capture", {
      image_data: imageData,
      ...metadata,
    });
  },

  // Get list of documents with filtering
  getDocuments: async (
    filters: DocumentFilters = {}
  ): Promise<PaginatedResponse<Document>> => {
    const params: Record<string, string> = {};
    if (filters.category) params.category = filters.category;
    if (filters.search) params.search = filters.search;
    if (filters.page) params.page = String(filters.page);
    if (filters.page_size) params.page_size = String(filters.page_size);

    return apiClient.get<PaginatedResponse<Document>>("/api/v1/documents", {
      params,
    });
  },

  // Get single document
  getDocument: async (documentId: string): Promise<Document> => {
    return apiClient.get<Document>(`/api/v1/documents/${documentId}`);
  },

  // Download document
  getDocumentDownloadUrl: (documentId: string): string => {
    return `${API_BASE_URL}/api/v1/documents/${documentId}/download`;
  },

  // Search documents
  searchDocuments: async (query: string): Promise<Document[]> => {
    return apiClient.get<Document[]>("/api/v1/documents/search", {
      params: { query },
    });
  },

  // Delete document
  deleteDocument: async (documentId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/documents/${documentId}`);
  },

  // Get document versions
  getDocumentVersions: async (documentId: string): Promise<DocumentVersion[]> => {
    return apiClient.get<DocumentVersion[]>(
      `/api/v1/documents/${documentId}/versions`
    );
  },

  // Create share link
  createShareLink: async (
    documentId: string,
    options: ShareLinkCreateRequest
  ): Promise<ShareLinkCreateResponse> => {
    return apiClient.post<ShareLinkCreateResponse>(
      `/api/v1/documents/${documentId}/share`,
      options
    );
  },

  // Get share links for a document
  getShareLinks: async (documentId: string): Promise<ShareLink[]> => {
    return apiClient.get<ShareLink[]>(`/api/v1/documents/${documentId}/share`);
  },

  // Revoke share link
  revokeShareLink: async (documentId: string, linkId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/documents/${documentId}/share/${linkId}`);
  },

  // Get share link access logs
  getShareLinkAccesses: async (
    documentId: string,
    linkId: string
  ): Promise<ShareLinkAccess[]> => {
    return apiClient.get<ShareLinkAccess[]>(
      `/api/v1/documents/${documentId}/share/${linkId}/accesses`
    );
  },
};
