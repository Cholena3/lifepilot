import { apiClient } from "./client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface WardrobeItem {
  id: string;
  user_id: string;
  image_url: string;
  processed_image_url: string | null;
  item_type: string;
  name: string | null;
  primary_color: string | null;
  pattern: string | null;
  brand: string | null;
  price: number | null;
  purchase_date: string | null;
  in_laundry: boolean;
  wear_count: number;
  last_worn: string | null;
  occasions: string[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WardrobeItemWithStats extends WardrobeItem {
  cost_per_wear: number | null;
  days_since_last_worn: number | null;
}

export interface WearLog {
  id: string;
  item_id: string;
  worn_date: string;
  occasion: string | null;
  created_at: string;
}

export interface Outfit {
  id: string;
  user_id: string;
  name: string;
  occasion: string | null;
  notes: string | null;
  items: OutfitItem[];
  created_at: string;
  updated_at: string;
}

export interface OutfitItem {
  id: string;
  wardrobe_item_id: string;
  wardrobe_item: WardrobeItem | null;
}

export interface OutfitPlan {
  id: string;
  user_id: string;
  outfit_id: string;
  planned_date: string;
  event_name: string | null;
  is_completed: boolean;
  notes: string | null;
  outfit: Outfit | null;
  laundry_conflicts: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface PackingList {
  id: string;
  user_id: string;
  name: string;
  destination: string | null;
  trip_start: string | null;
  trip_end: string | null;
  is_template: boolean;
  notes: string | null;
  items: PackingListItem[];
  created_at: string;
  updated_at: string;
}

export interface PackingListItem {
  id: string;
  packing_list_id: string;
  wardrobe_item_id: string | null;
  custom_item_name: string | null;
  quantity: number;
  is_packed: boolean;
  wardrobe_item: WardrobeItem | null;
}

export interface WardrobeStats {
  total_items: number;
  total_value: number;
  items_by_type: Record<string, number>;
  items_by_color: Record<string, number>;
  most_worn_items: WardrobeItemWithStats[];
  least_worn_items: WardrobeItemWithStats[];
  unworn_items: WardrobeItem[];
  items_in_laundry: number;
  average_cost_per_wear: number | null;
}

export interface OutfitSuggestion {
  items: WardrobeItem[];
  weather: { temperature: number; condition: string; humidity: number | null } | null;
  occasion: string | null;
  score: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface WardrobeItemFilters {
  item_type?: string;
  primary_color?: string;
  pattern?: string;
  occasion?: string;
  in_laundry?: boolean;
  min_price?: number;
  max_price?: number;
  page?: number;
  page_size?: number;
}

// API Functions
export const wardrobeApi = {
  // Wardrobe Items
  getItems: async (filters: WardrobeItemFilters = {}): Promise<PaginatedResponse<WardrobeItem>> => {
    const params: Record<string, string> = {};
    if (filters.item_type) params.item_type = filters.item_type;
    if (filters.primary_color) params.primary_color = filters.primary_color;
    if (filters.pattern) params.pattern = filters.pattern;
    if (filters.occasion) params.occasion = filters.occasion;
    if (filters.in_laundry !== undefined) params.in_laundry = String(filters.in_laundry);
    if (filters.min_price) params.min_price = String(filters.min_price);
    if (filters.max_price) params.max_price = String(filters.max_price);
    if (filters.page) params.page = String(filters.page);
    if (filters.page_size) params.page_size = String(filters.page_size);

    return apiClient.get<PaginatedResponse<WardrobeItem>>("/api/v1/wardrobe/items", { params });
  },

  getItem: async (itemId: string): Promise<WardrobeItem> => {
    return apiClient.get<WardrobeItem>(`/api/v1/wardrobe/items/${itemId}`);
  },

  createItem: async (
    file: File,
    data: {
      item_type: string;
      name?: string;
      primary_color?: string;
      pattern?: string;
      brand?: string;
      price?: number;
      purchase_date?: string;
      occasions?: string[];
      notes?: string;
    }
  ): Promise<WardrobeItem> => {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("item_type", data.item_type);
    if (data.name) formData.append("name", data.name);
    if (data.primary_color) formData.append("primary_color", data.primary_color);
    if (data.pattern) formData.append("pattern", data.pattern);
    if (data.brand) formData.append("brand", data.brand);
    if (data.price) formData.append("price", String(data.price));
    if (data.purchase_date) formData.append("purchase_date", data.purchase_date);
    if (data.occasions) formData.append("occasions", data.occasions.join(","));
    if (data.notes) formData.append("notes", data.notes);

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

    const response = await fetch(`${API_BASE_URL}/api/v1/wardrobe/items`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to create wardrobe item");
    }

    return response.json();
  },

  updateItem: async (
    itemId: string,
    data: Partial<{
      item_type: string;
      name: string;
      primary_color: string;
      pattern: string;
      brand: string;
      price: number;
      purchase_date: string;
      occasions: string[];
      notes: string;
    }>
  ): Promise<WardrobeItem> => {
    return apiClient.patch<WardrobeItem>(`/api/v1/wardrobe/items/${itemId}`, data);
  },

  deleteItem: async (itemId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/wardrobe/items/${itemId}`);
  },

  setLaundryStatus: async (itemId: string, inLaundry: boolean): Promise<WardrobeItem> => {
    return apiClient.post<WardrobeItem>(
      `/api/v1/wardrobe/items/${itemId}/laundry?in_laundry=${inLaundry}`
    );
  },

  markWorn: async (
    itemId: string,
    data: { worn_date: string; occasion?: string }
  ): Promise<WearLog> => {
    return apiClient.post<WearLog>(`/api/v1/wardrobe/items/${itemId}/worn`, data);
  },

  getWearLogs: async (
    itemId: string,
    startDate?: string,
    endDate?: string
  ): Promise<WearLog[]> => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return apiClient.get<WearLog[]>(`/api/v1/wardrobe/items/${itemId}/wear-logs`, { params });
  },

  getStatistics: async (): Promise<WardrobeStats> => {
    return apiClient.get<WardrobeStats>("/api/v1/wardrobe/statistics");
  },

  // Outfits
  getOutfits: async (
    occasion?: string,
    page?: number,
    pageSize?: number
  ): Promise<PaginatedResponse<Outfit>> => {
    const params: Record<string, string> = {};
    if (occasion) params.occasion = occasion;
    if (page) params.page = String(page);
    if (pageSize) params.page_size = String(pageSize);
    return apiClient.get<PaginatedResponse<Outfit>>("/api/v1/wardrobe/outfits", { params });
  },

  getOutfit: async (outfitId: string): Promise<Outfit> => {
    return apiClient.get<Outfit>(`/api/v1/wardrobe/outfits/${outfitId}`);
  },

  createOutfit: async (data: {
    name: string;
    occasion?: string;
    item_ids: string[];
    notes?: string;
  }): Promise<Outfit> => {
    return apiClient.post<Outfit>("/api/v1/wardrobe/outfits", data);
  },

  updateOutfit: async (
    outfitId: string,
    data: Partial<{
      name: string;
      occasion: string;
      item_ids: string[];
      notes: string;
    }>
  ): Promise<Outfit> => {
    return apiClient.patch<Outfit>(`/api/v1/wardrobe/outfits/${outfitId}`, data);
  },

  deleteOutfit: async (outfitId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/wardrobe/outfits/${outfitId}`);
  },

  getSuggestions: async (occasion?: string, location?: string): Promise<OutfitSuggestion[]> => {
    const params: Record<string, string> = {};
    if (occasion) params.occasion = occasion;
    if (location) params.location = location;
    return apiClient.get<OutfitSuggestion[]>("/api/v1/wardrobe/outfits/suggestions", { params });
  },

  // Outfit Plans
  getPlans: async (
    startDate?: string,
    endDate?: string,
    isCompleted?: boolean,
    page?: number,
    pageSize?: number
  ): Promise<PaginatedResponse<OutfitPlan>> => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (isCompleted !== undefined) params.is_completed = String(isCompleted);
    if (page) params.page = String(page);
    if (pageSize) params.page_size = String(pageSize);
    return apiClient.get<PaginatedResponse<OutfitPlan>>("/api/v1/wardrobe/plans", { params });
  },

  getPlan: async (planId: string): Promise<OutfitPlan> => {
    return apiClient.get<OutfitPlan>(`/api/v1/wardrobe/plans/${planId}`);
  },

  createPlan: async (data: {
    outfit_id: string;
    planned_date: string;
    event_name?: string;
    notes?: string;
  }): Promise<OutfitPlan> => {
    return apiClient.post<OutfitPlan>("/api/v1/wardrobe/plans", data);
  },

  updatePlan: async (
    planId: string,
    data: Partial<{
      outfit_id: string;
      planned_date: string;
      event_name: string;
      is_completed: boolean;
      notes: string;
    }>
  ): Promise<OutfitPlan> => {
    return apiClient.patch<OutfitPlan>(`/api/v1/wardrobe/plans/${planId}`, data);
  },

  completePlan: async (planId: string): Promise<OutfitPlan> => {
    return apiClient.post<OutfitPlan>(`/api/v1/wardrobe/plans/${planId}/complete`);
  },

  deletePlan: async (planId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/wardrobe/plans/${planId}`);
  },

  // Packing Lists
  getPackingLists: async (
    isTemplate?: boolean,
    page?: number,
    pageSize?: number
  ): Promise<PaginatedResponse<PackingList>> => {
    const params: Record<string, string> = {};
    if (isTemplate !== undefined) params.is_template = String(isTemplate);
    if (page) params.page = String(page);
    if (pageSize) params.page_size = String(pageSize);
    return apiClient.get<PaginatedResponse<PackingList>>("/api/v1/wardrobe/packing-lists", {
      params,
    });
  },

  getPackingList: async (listId: string): Promise<PackingList> => {
    return apiClient.get<PackingList>(`/api/v1/wardrobe/packing-lists/${listId}`);
  },

  createPackingList: async (data: {
    name: string;
    destination?: string;
    trip_start?: string;
    trip_end?: string;
    is_template?: boolean;
    notes?: string;
    items?: { wardrobe_item_id?: string; custom_item_name?: string; quantity?: number }[];
  }): Promise<PackingList> => {
    return apiClient.post<PackingList>("/api/v1/wardrobe/packing-lists", data);
  },

  updatePackingList: async (
    listId: string,
    data: Partial<{
      name: string;
      destination: string;
      trip_start: string;
      trip_end: string;
      is_template: boolean;
      notes: string;
    }>
  ): Promise<PackingList> => {
    return apiClient.patch<PackingList>(`/api/v1/wardrobe/packing-lists/${listId}`, data);
  },

  deletePackingList: async (listId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/wardrobe/packing-lists/${listId}`);
  },

  getTemplates: async (): Promise<PackingList[]> => {
    return apiClient.get<PackingList[]>("/api/v1/wardrobe/packing-lists/templates");
  },

  createFromTemplate: async (
    templateId: string,
    name: string,
    destination?: string,
    tripStart?: string,
    tripEnd?: string
  ): Promise<PackingList> => {
    const params: Record<string, string> = { name };
    if (destination) params.destination = destination;
    if (tripStart) params.trip_start = tripStart;
    if (tripEnd) params.trip_end = tripEnd;
    return apiClient.post<PackingList>(
      `/api/v1/wardrobe/packing-lists/from-template/${templateId}`,
      null,
      { params }
    );
  },

  addPackingListItem: async (
    listId: string,
    data: { wardrobe_item_id?: string; custom_item_name?: string; quantity?: number }
  ): Promise<PackingListItem> => {
    return apiClient.post<PackingListItem>(`/api/v1/wardrobe/packing-lists/${listId}/items`, data);
  },

  toggleItemPacked: async (
    listId: string,
    itemId: string,
    isPacked: boolean
  ): Promise<PackingListItem> => {
    return apiClient.patch<PackingListItem>(
      `/api/v1/wardrobe/packing-lists/${listId}/items/${itemId}/packed?is_packed=${isPacked}`
    );
  },

  removePackingListItem: async (listId: string, itemId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/wardrobe/packing-lists/${listId}/items/${itemId}`);
  },
};

// Constants
export const CLOTHING_TYPES = [
  { value: "top", label: "Top" },
  { value: "bottom", label: "Bottom" },
  { value: "dress", label: "Dress" },
  { value: "outerwear", label: "Outerwear" },
  { value: "footwear", label: "Footwear" },
  { value: "accessory", label: "Accessory" },
  { value: "activewear", label: "Activewear" },
  { value: "sleepwear", label: "Sleepwear" },
  { value: "swimwear", label: "Swimwear" },
  { value: "formal", label: "Formal" },
  { value: "other", label: "Other" },
];

export const CLOTHING_PATTERNS = [
  { value: "solid", label: "Solid" },
  { value: "striped", label: "Striped" },
  { value: "plaid", label: "Plaid" },
  { value: "floral", label: "Floral" },
  { value: "polka_dot", label: "Polka Dot" },
  { value: "geometric", label: "Geometric" },
  { value: "abstract", label: "Abstract" },
  { value: "animal_print", label: "Animal Print" },
  { value: "camouflage", label: "Camouflage" },
  { value: "other", label: "Other" },
];

export const OCCASIONS = [
  { value: "casual", label: "Casual" },
  { value: "formal", label: "Formal" },
  { value: "business", label: "Business" },
  { value: "party", label: "Party" },
  { value: "sports", label: "Sports" },
  { value: "beach", label: "Beach" },
  { value: "wedding", label: "Wedding" },
  { value: "date", label: "Date" },
  { value: "interview", label: "Interview" },
  { value: "other", label: "Other" },
];

export const COLORS = [
  { value: "red", label: "Red" },
  { value: "blue", label: "Blue" },
  { value: "green", label: "Green" },
  { value: "black", label: "Black" },
  { value: "white", label: "White" },
  { value: "gray", label: "Gray" },
  { value: "navy", label: "Navy" },
  { value: "beige", label: "Beige" },
  { value: "brown", label: "Brown" },
  { value: "pink", label: "Pink" },
  { value: "purple", label: "Purple" },
  { value: "yellow", label: "Yellow" },
  { value: "orange", label: "Orange" },
];
