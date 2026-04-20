import { apiClient } from "./client";

export interface ProfileResponse {
  id: string;
  user_id: string;
  first_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  avatar_url: string | null;
  completion_percentage: number;
}

export interface ProfileUpdateRequest {
  first_name?: string | null;
  last_name?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
}

export interface StudentProfileResponse {
  id: string;
  user_id: string;
  institution: string | null;
  degree: string | null;
  branch: string | null;
  cgpa: number | null;
  backlogs: number | null;
  graduation_year: number | null;
}

export interface StudentProfileUpdateRequest {
  institution?: string | null;
  degree?: string | null;
  branch?: string | null;
  cgpa?: number | null;
  backlogs?: number | null;
  graduation_year?: number | null;
}

export interface CareerPreferencesResponse {
  id: string;
  user_id: string;
  preferred_roles: string[] | null;
  preferred_locations: string[] | null;
  min_salary: number | null;
  max_salary: number | null;
  job_type: string | null;
}

export interface CareerPreferencesUpdateRequest {
  preferred_roles?: string[] | null;
  preferred_locations?: string[] | null;
  min_salary?: number | null;
  max_salary?: number | null;
  job_type?: string | null;
}

export const profileApi = {
  getProfile: async (): Promise<ProfileResponse> => {
    return apiClient.get<ProfileResponse>("/api/v1/profile");
  },

  updateProfile: async (data: ProfileUpdateRequest): Promise<ProfileResponse> => {
    return apiClient.put<ProfileResponse>("/api/v1/profile", data);
  },

  getStudentProfile: async (): Promise<StudentProfileResponse> => {
    return apiClient.get<StudentProfileResponse>("/api/v1/profile/student");
  },

  updateStudentProfile: async (
    data: StudentProfileUpdateRequest
  ): Promise<StudentProfileResponse> => {
    return apiClient.put<StudentProfileResponse>("/api/v1/profile/student", data);
  },

  getCareerPreferences: async (): Promise<CareerPreferencesResponse> => {
    return apiClient.get<CareerPreferencesResponse>("/api/v1/profile/career");
  },

  updateCareerPreferences: async (
    data: CareerPreferencesUpdateRequest
  ): Promise<CareerPreferencesResponse> => {
    return apiClient.put<CareerPreferencesResponse>("/api/v1/profile/career", data);
  },
};
