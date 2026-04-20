import { apiClient, ApiError } from "./client";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  phone_verified: boolean;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface OTPRequest {
  phone: string;
}

export interface OTPVerifyRequest {
  phone: string;
  otp: string;
}

export interface OTPResponse {
  message: string;
  expires_in: number;
}

export interface OTPVerifyResponse {
  verified: boolean;
  message: string;
}

export interface AuthResponse {
  user: UserResponse;
  tokens: TokenResponse;
}

export const authApi = {
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    return apiClient.post<AuthResponse>("/api/v1/auth/register", data);
  },

  login: async (data: LoginRequest): Promise<AuthResponse> => {
    return apiClient.post<AuthResponse>("/api/v1/auth/login", data);
  },

  getGoogleAuthUrl: (): string => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${baseUrl}/api/v1/auth/google`;
  },

  googleCallback: async (code: string): Promise<TokenResponse> => {
    return apiClient.get<TokenResponse>("/api/v1/auth/google/callback", {
      params: { code },
    });
  },

  sendOTP: async (data: OTPRequest): Promise<OTPResponse> => {
    return apiClient.post<OTPResponse>("/api/v1/auth/otp/send", data);
  },

  verifyOTP: async (data: OTPVerifyRequest): Promise<OTPVerifyResponse> => {
    return apiClient.post<OTPVerifyResponse>("/api/v1/auth/otp/verify", data);
  },

  getCurrentUser: async (): Promise<UserResponse> => {
    return apiClient.get<UserResponse>("/api/v1/auth/me");
  },

  refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
    return apiClient.post<TokenResponse>("/api/v1/auth/refresh", {
      refresh_token: refreshToken,
    });
  },

  logout: async (): Promise<void> => {
    return apiClient.post("/api/v1/auth/logout");
  },
};

export { ApiError };
