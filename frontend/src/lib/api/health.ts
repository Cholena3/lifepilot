import { apiClient } from "./client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface FamilyMember {
  id: string;
  user_id: string;
  name: string;
  relationship: string;
  date_of_birth: string | null;
  gender: string | null;
  created_at: string;
}

export interface HealthRecord {
  id: string;
  user_id: string;
  family_member_id: string | null;
  category: string;
  title: string;
  file_path: string;
  content_type: string;
  file_size: number;
  record_date: string | null;
  doctor_name: string | null;
  hospital_name: string | null;
  notes: string | null;
  ocr_text: string | null;
  extracted_data: Record<string, unknown> | null;
  created_at: string;
}

export interface Medicine {
  id: string;
  user_id: string;
  name: string;
  dosage: string;
  frequency: string;
  times_per_day: number;
  reminder_times: string[];
  start_date: string;
  end_date: string | null;
  current_stock: number;
  refill_threshold: number;
  instructions: string | null;
  is_active: boolean;
  created_at: string;
}

export interface MedicineDose {
  id: string;
  medicine_id: string;
  scheduled_time: string;
  taken_at: string | null;
  status: "pending" | "taken" | "missed" | "skipped";
}

export interface MedicineAdherence {
  medicine_id: string;
  medicine_name: string;
  total_doses: number;
  taken_doses: number;
  missed_doses: number;
  adherence_percentage: number;
}

export interface Vital {
  id: string;
  user_id: string;
  vital_type: string;
  value: number;
  unit: string;
  recorded_at: string;
  notes: string | null;
}

export interface VitalRange {
  vital_type: string;
  min_value: number;
  max_value: number;
  unit: string;
}

export interface VitalTrend {
  vital_type: string;
  readings: { date: string; value: number }[];
  average: number;
  min: number;
  max: number;
}

export interface EmergencyInfo {
  id: string;
  user_id: string;
  public_token: string;
  blood_type: string | null;
  allergies: string[];
  medical_conditions: string[];
  emergency_contacts: EmergencyContact[];
  current_medications: string[];
  visible_fields: string[];
  qr_code_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
}

export interface HealthRecordShare {
  id: string;
  user_id: string;
  public_token: string;
  doctor_name: string | null;
  doctor_email: string | null;
  purpose: string | null;
  record_ids: string[];
  expires_at: string;
  is_revoked: boolean;
  is_expired: boolean;
  is_valid: boolean;
  access_count: number;
  last_accessed_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface HealthRecordFilters {
  category?: string;
  family_member_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

// API Functions
export const healthApi = {
  // Family Members
  getFamilyMembers: async (): Promise<PaginatedResponse<FamilyMember>> => {
    return apiClient.get<PaginatedResponse<FamilyMember>>("/api/v1/health-records/family-members");
  },

  createFamilyMember: async (data: {
    name: string;
    relationship: string;
    date_of_birth?: string;
    gender?: string;
  }): Promise<FamilyMember> => {
    return apiClient.post<FamilyMember>("/api/v1/health-records/family-members", data);
  },

  deleteFamilyMember: async (memberId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/health-records/family-members/${memberId}`);
  },

  // Health Records
  getHealthRecords: async (
    filters: HealthRecordFilters = {}
  ): Promise<PaginatedResponse<HealthRecord>> => {
    const params: Record<string, string> = {};
    if (filters.category) params.category = filters.category;
    if (filters.family_member_id) params.family_member_id = filters.family_member_id;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.page) params.page = String(filters.page);
    if (filters.page_size) params.page_size = String(filters.page_size);

    return apiClient.get<PaginatedResponse<HealthRecord>>("/api/v1/health-records", { params });
  },

  uploadHealthRecord: async (
    file: File,
    data: {
      category: string;
      title: string;
      family_member_id?: string;
      record_date?: string;
      doctor_name?: string;
      hospital_name?: string;
      notes?: string;
    }
  ): Promise<HealthRecord> => {
    const formData = new FormData();
    formData.append("file", file);
    Object.entries(data).forEach(([key, value]) => {
      if (value) formData.append(key, value);
    });

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

    const response = await fetch(`${API_BASE_URL}/api/v1/health-records`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to upload health record");
    }

    return response.json();
  },

  deleteHealthRecord: async (recordId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/health-records/${recordId}`);
  },

  searchHealthRecords: async (query: string): Promise<PaginatedResponse<HealthRecord>> => {
    return apiClient.get<PaginatedResponse<HealthRecord>>("/api/v1/health-records/search", {
      params: { q: query },
    });
  },

  // Medicines
  getMedicines: async (): Promise<PaginatedResponse<Medicine>> => {
    return apiClient.get<PaginatedResponse<Medicine>>("/api/v1/medicines");
  },

  createMedicine: async (data: {
    name: string;
    dosage: string;
    frequency: string;
    times_per_day: number;
    reminder_times: string[];
    start_date: string;
    end_date?: string;
    current_stock?: number;
    refill_threshold?: number;
    instructions?: string;
  }): Promise<Medicine> => {
    return apiClient.post<Medicine>("/api/v1/medicines", data);
  },

  updateMedicine: async (
    medicineId: string,
    data: Partial<{
      name: string;
      dosage: string;
      frequency: string;
      times_per_day: number;
      reminder_times: string[];
      end_date: string;
      current_stock: number;
      refill_threshold: number;
      instructions: string;
      is_active: boolean;
    }>
  ): Promise<Medicine> => {
    return apiClient.patch<Medicine>(`/api/v1/medicines/${medicineId}`, data);
  },

  deleteMedicine: async (medicineId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/medicines/${medicineId}`);
  },

  getTodayDoses: async (): Promise<MedicineDose[]> => {
    return apiClient.get<MedicineDose[]>("/api/v1/medicines/doses/today");
  },

  recordDose: async (doseId: string, status: "taken" | "skipped"): Promise<MedicineDose> => {
    return apiClient.post<MedicineDose>(`/api/v1/medicines/doses/${doseId}/${status}`);
  },

  getAdherence: async (medicineId: string, days?: number): Promise<MedicineAdherence> => {
    const params: Record<string, string> = {};
    if (days) params.days = String(days);
    return apiClient.get<MedicineAdherence>(`/api/v1/medicines/${medicineId}/adherence`, { params });
  },

  // Vitals
  getVitals: async (vitalType?: string): Promise<PaginatedResponse<Vital>> => {
    const params: Record<string, string> = {};
    if (vitalType) params.vital_type = vitalType;
    return apiClient.get<PaginatedResponse<Vital>>("/api/v1/vitals", { params });
  },

  createVital: async (data: {
    vital_type: string;
    value: number;
    unit: string;
    recorded_at?: string;
    notes?: string;
  }): Promise<Vital> => {
    return apiClient.post<Vital>("/api/v1/vitals", data);
  },

  deleteVital: async (vitalId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/vitals/${vitalId}`);
  },

  getVitalTrends: async (vitalType: string, days?: number): Promise<VitalTrend> => {
    const params: Record<string, string> = { vital_type: vitalType };
    if (days) params.days = String(days);
    return apiClient.get<VitalTrend>("/api/v1/vitals/trends", { params });
  },

  getVitalRanges: async (): Promise<VitalRange[]> => {
    return apiClient.get<VitalRange[]>("/api/v1/vitals/ranges");
  },

  exportVitalsPdf: async (vitalType: string): Promise<Blob> => {
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
      `${API_BASE_URL}/api/v1/vitals/export/pdf?vital_type=${vitalType}`,
      { headers }
    );

    if (!response.ok) {
      throw new Error("Failed to export vitals PDF");
    }

    return response.blob();
  },

  // Emergency Info
  getEmergencyInfo: async (): Promise<EmergencyInfo> => {
    return apiClient.get<EmergencyInfo>("/api/v1/health/emergency");
  },

  createOrUpdateEmergencyInfo: async (data: {
    blood_type?: string;
    allergies?: string[];
    medical_conditions?: string[];
    emergency_contacts?: EmergencyContact[];
    current_medications?: string[];
    visible_fields?: string[];
  }): Promise<EmergencyInfo> => {
    return apiClient.post<EmergencyInfo>("/api/v1/health/emergency", data);
  },

  getEmergencyQrCode: async (): Promise<Blob> => {
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

    const response = await fetch(`${API_BASE_URL}/api/v1/health/emergency/qr`, { headers });

    if (!response.ok) {
      throw new Error("Failed to get QR code");
    }

    return response.blob();
  },

  // Health Record Sharing
  getHealthShares: async (): Promise<PaginatedResponse<HealthRecordShare>> => {
    return apiClient.get<PaginatedResponse<HealthRecordShare>>("/api/v1/health/shares");
  },

  createHealthShare: async (data: {
    record_ids: string[];
    doctor_name?: string;
    doctor_email?: string;
    purpose?: string;
    expires_in_hours?: number;
    notes?: string;
  }): Promise<HealthRecordShare> => {
    return apiClient.post<HealthRecordShare>("/api/v1/health/shares", data);
  },

  revokeHealthShare: async (shareId: string): Promise<HealthRecordShare> => {
    return apiClient.post<HealthRecordShare>(`/api/v1/health/shares/${shareId}/revoke`);
  },

  deleteHealthShare: async (shareId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/health/shares/${shareId}`);
  },
};

export const HEALTH_RECORD_CATEGORIES = [
  { value: "prescription", label: "Prescription" },
  { value: "lab_report", label: "Lab Report" },
  { value: "scan", label: "Scan/X-Ray" },
  { value: "vaccine", label: "Vaccine Record" },
  { value: "insurance", label: "Insurance" },
  { value: "other", label: "Other" },
];

export const VITAL_TYPES = [
  { value: "blood_pressure_systolic", label: "Blood Pressure (Systolic)", unit: "mmHg" },
  { value: "blood_pressure_diastolic", label: "Blood Pressure (Diastolic)", unit: "mmHg" },
  { value: "heart_rate", label: "Heart Rate", unit: "bpm" },
  { value: "blood_sugar", label: "Blood Sugar", unit: "mg/dL" },
  { value: "weight", label: "Weight", unit: "kg" },
  { value: "temperature", label: "Temperature", unit: "°F" },
  { value: "oxygen_saturation", label: "Oxygen Saturation", unit: "%" },
];

export const BLOOD_TYPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
