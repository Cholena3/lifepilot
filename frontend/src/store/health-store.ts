import { create } from "zustand";
import {
  healthApi,
  type FamilyMember,
  type HealthRecord,
  type Medicine,
  type MedicineDose,
  type MedicineAdherence,
  type Vital,
  type VitalTrend,
  type EmergencyInfo,
  type HealthRecordShare,
  type HealthRecordFilters,
  type PaginatedResponse,
} from "@/lib/api/health";

export interface HealthState {
  // Family Members
  familyMembers: FamilyMember[];

  // Health Records
  healthRecords: HealthRecord[];
  recordFilters: HealthRecordFilters;
  recordPagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };

  // Medicines
  medicines: Medicine[];
  todayDoses: MedicineDose[];
  selectedMedicineAdherence: MedicineAdherence | null;

  // Vitals
  vitals: Vital[];
  vitalTrends: VitalTrend | null;
  selectedVitalType: string | null;

  // Emergency Info
  emergencyInfo: EmergencyInfo | null;
  emergencyQrUrl: string | null;

  // Health Shares
  healthShares: HealthRecordShare[];

  // UI State
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;
}

export interface HealthActions {
  // Family Members
  fetchFamilyMembers: () => Promise<void>;
  createFamilyMember: (data: {
    name: string;
    relationship: string;
    date_of_birth?: string;
    gender?: string;
  }) => Promise<FamilyMember>;
  deleteFamilyMember: (memberId: string) => Promise<void>;

  // Health Records
  fetchHealthRecords: (filters?: HealthRecordFilters) => Promise<void>;
  uploadHealthRecord: (
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
  ) => Promise<HealthRecord>;
  deleteHealthRecord: (recordId: string) => Promise<void>;
  searchHealthRecords: (query: string) => Promise<void>;
  setRecordFilters: (filters: HealthRecordFilters) => void;
  setRecordPage: (page: number) => void;

  // Medicines
  fetchMedicines: () => Promise<void>;
  createMedicine: (data: {
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
  }) => Promise<Medicine>;
  updateMedicine: (medicineId: string, data: Partial<Medicine>) => Promise<Medicine>;
  deleteMedicine: (medicineId: string) => Promise<void>;
  fetchTodayDoses: () => Promise<void>;
  recordDose: (doseId: string, status: "taken" | "skipped") => Promise<void>;
  fetchAdherence: (medicineId: string, days?: number) => Promise<void>;

  // Vitals
  fetchVitals: (vitalType?: string) => Promise<void>;
  createVital: (data: {
    vital_type: string;
    value: number;
    unit: string;
    recorded_at?: string;
    notes?: string;
  }) => Promise<Vital>;
  deleteVital: (vitalId: string) => Promise<void>;
  fetchVitalTrends: (vitalType: string, days?: number) => Promise<void>;
  setSelectedVitalType: (vitalType: string | null) => void;
  exportVitalsPdf: (vitalType: string) => Promise<void>;

  // Emergency Info
  fetchEmergencyInfo: () => Promise<void>;
  saveEmergencyInfo: (data: {
    blood_type?: string;
    allergies?: string[];
    medical_conditions?: string[];
    emergency_contacts?: { name: string; relationship: string; phone: string }[];
    current_medications?: string[];
    visible_fields?: string[];
  }) => Promise<void>;
  fetchEmergencyQrCode: () => Promise<void>;

  // Health Shares
  fetchHealthShares: () => Promise<void>;
  createHealthShare: (data: {
    record_ids: string[];
    doctor_name?: string;
    doctor_email?: string;
    purpose?: string;
    expires_in_hours?: number;
    notes?: string;
  }) => Promise<HealthRecordShare>;
  revokeHealthShare: (shareId: string) => Promise<void>;
  deleteHealthShare: (shareId: string) => Promise<void>;

  // Error handling
  clearError: () => void;
}

export type HealthStore = HealthState & HealthActions;

const initialState: HealthState = {
  familyMembers: [],
  healthRecords: [],
  recordFilters: {},
  recordPagination: {
    total: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
  },
  medicines: [],
  todayDoses: [],
  selectedMedicineAdherence: null,
  vitals: [],
  vitalTrends: null,
  selectedVitalType: null,
  emergencyInfo: null,
  emergencyQrUrl: null,
  healthShares: [],
  isLoading: false,
  isSubmitting: false,
  error: null,
};

export const useHealthStore = create<HealthStore>((set, get) => ({
  ...initialState,

  // Family Members
  fetchFamilyMembers: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await healthApi.getFamilyMembers();
      set({ familyMembers: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch family members",
        isLoading: false,
      });
    }
  },

  createFamilyMember: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const member = await healthApi.createFamilyMember(data);
      set((state) => ({
        familyMembers: [...state.familyMembers, member],
        isSubmitting: false,
      }));
      return member;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create family member",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteFamilyMember: async (memberId) => {
    set({ isSubmitting: true, error: null });
    try {
      await healthApi.deleteFamilyMember(memberId);
      set((state) => ({
        familyMembers: state.familyMembers.filter((m) => m.id !== memberId),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete family member",
        isSubmitting: false,
      });
      throw error;
    }
  },

  // Health Records
  fetchHealthRecords: async (filters?: HealthRecordFilters) => {
    set({ isLoading: true, error: null });
    try {
      const currentFilters = filters || get().recordFilters;
      const response = await healthApi.getHealthRecords(currentFilters);
      set({
        healthRecords: response.items,
        recordPagination: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
        recordFilters: currentFilters,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch health records",
        isLoading: false,
      });
    }
  },

  uploadHealthRecord: async (file, data) => {
    set({ isSubmitting: true, error: null });
    try {
      const record = await healthApi.uploadHealthRecord(file, data);
      set((state) => ({
        healthRecords: [record, ...state.healthRecords],
        isSubmitting: false,
      }));
      return record;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to upload health record",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteHealthRecord: async (recordId) => {
    set({ isSubmitting: true, error: null });
    try {
      await healthApi.deleteHealthRecord(recordId);
      set((state) => ({
        healthRecords: state.healthRecords.filter((r) => r.id !== recordId),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete health record",
        isSubmitting: false,
      });
      throw error;
    }
  },

  searchHealthRecords: async (query) => {
    set({ isLoading: true, error: null });
    try {
      const response = await healthApi.searchHealthRecords(query);
      set({
        healthRecords: response.items,
        recordPagination: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to search health records",
        isLoading: false,
      });
    }
  },

  setRecordFilters: (filters) => {
    set({ recordFilters: filters });
    get().fetchHealthRecords(filters);
  },

  setRecordPage: (page) => {
    const newFilters = { ...get().recordFilters, page };
    set({ recordFilters: newFilters });
    get().fetchHealthRecords(newFilters);
  },

  // Medicines
  fetchMedicines: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await healthApi.getMedicines();
      set({ medicines: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch medicines",
        isLoading: false,
      });
    }
  },

  createMedicine: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const medicine = await healthApi.createMedicine(data);
      set((state) => ({
        medicines: [...state.medicines, medicine],
        isSubmitting: false,
      }));
      return medicine;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create medicine",
        isSubmitting: false,
      });
      throw error;
    }
  },

  updateMedicine: async (medicineId, data) => {
    set({ isSubmitting: true, error: null });
    try {
      const medicine = await healthApi.updateMedicine(medicineId, data);
      set((state) => ({
        medicines: state.medicines.map((m) => (m.id === medicineId ? medicine : m)),
        isSubmitting: false,
      }));
      return medicine;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to update medicine",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteMedicine: async (medicineId) => {
    set({ isSubmitting: true, error: null });
    try {
      await healthApi.deleteMedicine(medicineId);
      set((state) => ({
        medicines: state.medicines.filter((m) => m.id !== medicineId),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete medicine",
        isSubmitting: false,
      });
      throw error;
    }
  },

  fetchTodayDoses: async () => {
    set({ isLoading: true, error: null });
    try {
      const doses = await healthApi.getTodayDoses();
      set({ todayDoses: doses, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch today's doses",
        isLoading: false,
      });
    }
  },

  recordDose: async (doseId, status) => {
    set({ isSubmitting: true, error: null });
    try {
      const dose = await healthApi.recordDose(doseId, status);
      set((state) => ({
        todayDoses: state.todayDoses.map((d) => (d.id === doseId ? dose : d)),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to record dose",
        isSubmitting: false,
      });
      throw error;
    }
  },

  fetchAdherence: async (medicineId, days) => {
    set({ isLoading: true, error: null });
    try {
      const adherence = await healthApi.getAdherence(medicineId, days);
      set({ selectedMedicineAdherence: adherence, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch adherence",
        isLoading: false,
      });
    }
  },

  // Vitals
  fetchVitals: async (vitalType) => {
    set({ isLoading: true, error: null });
    try {
      const response = await healthApi.getVitals(vitalType);
      set({ vitals: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch vitals",
        isLoading: false,
      });
    }
  },

  createVital: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const vital = await healthApi.createVital(data);
      set((state) => ({
        vitals: [vital, ...state.vitals],
        isSubmitting: false,
      }));
      return vital;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create vital",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteVital: async (vitalId) => {
    set({ isSubmitting: true, error: null });
    try {
      await healthApi.deleteVital(vitalId);
      set((state) => ({
        vitals: state.vitals.filter((v) => v.id !== vitalId),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete vital",
        isSubmitting: false,
      });
      throw error;
    }
  },

  fetchVitalTrends: async (vitalType, days) => {
    set({ isLoading: true, error: null });
    try {
      const trends = await healthApi.getVitalTrends(vitalType, days);
      set({ vitalTrends: trends, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch vital trends",
        isLoading: false,
      });
    }
  },

  setSelectedVitalType: (vitalType) => {
    set({ selectedVitalType: vitalType });
    if (vitalType) {
      get().fetchVitals(vitalType);
      get().fetchVitalTrends(vitalType);
    }
  },

  exportVitalsPdf: async (vitalType) => {
    set({ isSubmitting: true, error: null });
    try {
      const blob = await healthApi.exportVitalsPdf(vitalType);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vitals_${vitalType}_report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      set({ isSubmitting: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to export vitals PDF",
        isSubmitting: false,
      });
      throw error;
    }
  },

  // Emergency Info
  fetchEmergencyInfo: async () => {
    set({ isLoading: true, error: null });
    try {
      const info = await healthApi.getEmergencyInfo();
      set({ emergencyInfo: info, isLoading: false });
    } catch (error) {
      // 404 is expected if no emergency info exists yet
      if (error instanceof Error && error.message.includes("404")) {
        set({ emergencyInfo: null, isLoading: false });
      } else {
        set({
          error: error instanceof Error ? error.message : "Failed to fetch emergency info",
          isLoading: false,
        });
      }
    }
  },

  saveEmergencyInfo: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const info = await healthApi.createOrUpdateEmergencyInfo(data);
      set({ emergencyInfo: info, isSubmitting: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to save emergency info",
        isSubmitting: false,
      });
      throw error;
    }
  },

  fetchEmergencyQrCode: async () => {
    set({ isLoading: true, error: null });
    try {
      const blob = await healthApi.getEmergencyQrCode();
      const url = URL.createObjectURL(blob);
      set({ emergencyQrUrl: url, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch QR code",
        isLoading: false,
      });
    }
  },

  // Health Shares
  fetchHealthShares: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await healthApi.getHealthShares();
      set({ healthShares: response.items, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch health shares",
        isLoading: false,
      });
    }
  },

  createHealthShare: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const share = await healthApi.createHealthShare(data);
      set((state) => ({
        healthShares: [share, ...state.healthShares],
        isSubmitting: false,
      }));
      return share;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create health share",
        isSubmitting: false,
      });
      throw error;
    }
  },

  revokeHealthShare: async (shareId) => {
    set({ isSubmitting: true, error: null });
    try {
      const share = await healthApi.revokeHealthShare(shareId);
      set((state) => ({
        healthShares: state.healthShares.map((s) => (s.id === shareId ? share : s)),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to revoke health share",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteHealthShare: async (shareId) => {
    set({ isSubmitting: true, error: null });
    try {
      await healthApi.deleteHealthShare(shareId);
      set((state) => ({
        healthShares: state.healthShares.filter((s) => s.id !== shareId),
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete health share",
        isSubmitting: false,
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
