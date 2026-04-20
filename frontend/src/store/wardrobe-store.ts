import { create } from "zustand";
import {
  wardrobeApi,
  WardrobeItem,
  Outfit,
  OutfitPlan,
  PackingList,
  WardrobeStats,
  OutfitSuggestion,
  WardrobeItemFilters,
} from "@/lib/api/wardrobe";

interface WardrobeState {
  // Items
  items: WardrobeItem[];
  selectedItem: WardrobeItem | null;
  itemsTotal: number;
  itemsPage: number;
  itemsLoading: boolean;
  itemsError: string | null;

  // Outfits
  outfits: Outfit[];
  selectedOutfit: Outfit | null;
  outfitsTotal: number;
  outfitsLoading: boolean;
  outfitsError: string | null;

  // Suggestions
  suggestions: OutfitSuggestion[];
  suggestionsLoading: boolean;

  // Plans
  plans: OutfitPlan[];
  plansTotal: number;
  plansLoading: boolean;
  plansError: string | null;

  // Packing Lists
  packingLists: PackingList[];
  selectedPackingList: PackingList | null;
  packingListsTotal: number;
  packingListsLoading: boolean;
  packingListsError: string | null;

  // Statistics
  stats: WardrobeStats | null;
  statsLoading: boolean;

  // Filters
  filters: WardrobeItemFilters;

  // Actions
  fetchItems: (filters?: WardrobeItemFilters) => Promise<void>;
  fetchItem: (itemId: string) => Promise<void>;
  createItem: (
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
  ) => Promise<WardrobeItem>;
  updateItem: (itemId: string, data: Partial<WardrobeItem>) => Promise<void>;
  deleteItem: (itemId: string) => Promise<void>;
  setLaundryStatus: (itemId: string, inLaundry: boolean) => Promise<void>;
  markWorn: (itemId: string, wornDate: string, occasion?: string) => Promise<void>;

  fetchOutfits: (occasion?: string, page?: number) => Promise<void>;
  fetchOutfit: (outfitId: string) => Promise<void>;
  createOutfit: (data: {
    name: string;
    occasion?: string;
    item_ids: string[];
    notes?: string;
  }) => Promise<Outfit>;
  updateOutfit: (outfitId: string, data: Partial<Outfit>) => Promise<void>;
  deleteOutfit: (outfitId: string) => Promise<void>;

  fetchSuggestions: (occasion?: string, location?: string) => Promise<void>;

  fetchPlans: (startDate?: string, endDate?: string, isCompleted?: boolean) => Promise<void>;
  createPlan: (data: {
    outfit_id: string;
    planned_date: string;
    event_name?: string;
    notes?: string;
  }) => Promise<OutfitPlan>;
  completePlan: (planId: string) => Promise<void>;
  deletePlan: (planId: string) => Promise<void>;

  fetchPackingLists: (isTemplate?: boolean, page?: number) => Promise<void>;
  fetchPackingList: (listId: string) => Promise<void>;
  createPackingList: (data: {
    name: string;
    destination?: string;
    trip_start?: string;
    trip_end?: string;
    is_template?: boolean;
    notes?: string;
  }) => Promise<PackingList>;
  deletePackingList: (listId: string) => Promise<void>;
  toggleItemPacked: (listId: string, itemId: string, isPacked: boolean) => Promise<void>;

  fetchStats: () => Promise<void>;

  setFilters: (filters: WardrobeItemFilters) => void;
  clearSelection: () => void;
}

export const useWardrobeStore = create<WardrobeState>((set, get) => ({
  // Initial state
  items: [],
  selectedItem: null,
  itemsTotal: 0,
  itemsPage: 1,
  itemsLoading: false,
  itemsError: null,

  outfits: [],
  selectedOutfit: null,
  outfitsTotal: 0,
  outfitsLoading: false,
  outfitsError: null,

  suggestions: [],
  suggestionsLoading: false,

  plans: [],
  plansTotal: 0,
  plansLoading: false,
  plansError: null,

  packingLists: [],
  selectedPackingList: null,
  packingListsTotal: 0,
  packingListsLoading: false,
  packingListsError: null,

  stats: null,
  statsLoading: false,

  filters: {},

  // Actions
  fetchItems: async (filters?: WardrobeItemFilters) => {
    set({ itemsLoading: true, itemsError: null });
    try {
      const mergedFilters = { ...get().filters, ...filters };
      const response = await wardrobeApi.getItems(mergedFilters);
      set({
        items: response.items,
        itemsTotal: response.total,
        itemsPage: response.page,
        itemsLoading: false,
      });
    } catch (error) {
      set({
        itemsError: error instanceof Error ? error.message : "Failed to fetch items",
        itemsLoading: false,
      });
    }
  },

  fetchItem: async (itemId: string) => {
    try {
      const item = await wardrobeApi.getItem(itemId);
      set({ selectedItem: item });
    } catch (error) {
      console.error("Failed to fetch item:", error);
    }
  },

  createItem: async (file, data) => {
    const item = await wardrobeApi.createItem(file, data);
    set((state) => ({ items: [item, ...state.items] }));
    return item;
  },

  updateItem: async (itemId, data) => {
    const updated = await wardrobeApi.updateItem(itemId, data);
    set((state) => ({
      items: state.items.map((i) => (i.id === itemId ? updated : i)),
      selectedItem: state.selectedItem?.id === itemId ? updated : state.selectedItem,
    }));
  },

  deleteItem: async (itemId) => {
    await wardrobeApi.deleteItem(itemId);
    set((state) => ({
      items: state.items.filter((i) => i.id !== itemId),
      selectedItem: state.selectedItem?.id === itemId ? null : state.selectedItem,
    }));
  },

  setLaundryStatus: async (itemId, inLaundry) => {
    const updated = await wardrobeApi.setLaundryStatus(itemId, inLaundry);
    set((state) => ({
      items: state.items.map((i) => (i.id === itemId ? updated : i)),
    }));
  },

  markWorn: async (itemId, wornDate, occasion) => {
    await wardrobeApi.markWorn(itemId, { worn_date: wornDate, occasion });
    // Refresh the item to get updated wear count
    const updated = await wardrobeApi.getItem(itemId);
    set((state) => ({
      items: state.items.map((i) => (i.id === itemId ? updated : i)),
    }));
  },

  fetchOutfits: async (occasion, page) => {
    set({ outfitsLoading: true, outfitsError: null });
    try {
      const response = await wardrobeApi.getOutfits(occasion, page);
      set({
        outfits: response.items,
        outfitsTotal: response.total,
        outfitsLoading: false,
      });
    } catch (error) {
      set({
        outfitsError: error instanceof Error ? error.message : "Failed to fetch outfits",
        outfitsLoading: false,
      });
    }
  },

  fetchOutfit: async (outfitId) => {
    try {
      const outfit = await wardrobeApi.getOutfit(outfitId);
      set({ selectedOutfit: outfit });
    } catch (error) {
      console.error("Failed to fetch outfit:", error);
    }
  },

  createOutfit: async (data) => {
    const outfit = await wardrobeApi.createOutfit(data);
    set((state) => ({ outfits: [outfit, ...state.outfits] }));
    return outfit;
  },

  updateOutfit: async (outfitId, data) => {
    const updated = await wardrobeApi.updateOutfit(outfitId, data);
    set((state) => ({
      outfits: state.outfits.map((o) => (o.id === outfitId ? updated : o)),
      selectedOutfit: state.selectedOutfit?.id === outfitId ? updated : state.selectedOutfit,
    }));
  },

  deleteOutfit: async (outfitId) => {
    await wardrobeApi.deleteOutfit(outfitId);
    set((state) => ({
      outfits: state.outfits.filter((o) => o.id !== outfitId),
      selectedOutfit: state.selectedOutfit?.id === outfitId ? null : state.selectedOutfit,
    }));
  },

  fetchSuggestions: async (occasion, location) => {
    set({ suggestionsLoading: true });
    try {
      const suggestions = await wardrobeApi.getSuggestions(occasion, location);
      set({ suggestions, suggestionsLoading: false });
    } catch (error) {
      console.error("Failed to fetch suggestions:", error);
      set({ suggestionsLoading: false });
    }
  },

  fetchPlans: async (startDate, endDate, isCompleted) => {
    set({ plansLoading: true, plansError: null });
    try {
      const response = await wardrobeApi.getPlans(startDate, endDate, isCompleted);
      set({
        plans: response.items,
        plansTotal: response.total,
        plansLoading: false,
      });
    } catch (error) {
      set({
        plansError: error instanceof Error ? error.message : "Failed to fetch plans",
        plansLoading: false,
      });
    }
  },

  createPlan: async (data) => {
    const plan = await wardrobeApi.createPlan(data);
    set((state) => ({ plans: [plan, ...state.plans] }));
    return plan;
  },

  completePlan: async (planId) => {
    const updated = await wardrobeApi.completePlan(planId);
    set((state) => ({
      plans: state.plans.map((p) => (p.id === planId ? updated : p)),
    }));
  },

  deletePlan: async (planId) => {
    await wardrobeApi.deletePlan(planId);
    set((state) => ({
      plans: state.plans.filter((p) => p.id !== planId),
    }));
  },

  fetchPackingLists: async (isTemplate, page) => {
    set({ packingListsLoading: true, packingListsError: null });
    try {
      const response = await wardrobeApi.getPackingLists(isTemplate, page);
      set({
        packingLists: response.items,
        packingListsTotal: response.total,
        packingListsLoading: false,
      });
    } catch (error) {
      set({
        packingListsError: error instanceof Error ? error.message : "Failed to fetch packing lists",
        packingListsLoading: false,
      });
    }
  },

  fetchPackingList: async (listId) => {
    try {
      const list = await wardrobeApi.getPackingList(listId);
      set({ selectedPackingList: list });
    } catch (error) {
      console.error("Failed to fetch packing list:", error);
    }
  },

  createPackingList: async (data) => {
    const list = await wardrobeApi.createPackingList(data);
    set((state) => ({ packingLists: [list, ...state.packingLists] }));
    return list;
  },

  deletePackingList: async (listId) => {
    await wardrobeApi.deletePackingList(listId);
    set((state) => ({
      packingLists: state.packingLists.filter((l) => l.id !== listId),
      selectedPackingList:
        state.selectedPackingList?.id === listId ? null : state.selectedPackingList,
    }));
  },

  toggleItemPacked: async (listId, itemId, isPacked) => {
    await wardrobeApi.toggleItemPacked(listId, itemId, isPacked);
    // Refresh the packing list
    const updated = await wardrobeApi.getPackingList(listId);
    set((state) => ({
      packingLists: state.packingLists.map((l) => (l.id === listId ? updated : l)),
      selectedPackingList: state.selectedPackingList?.id === listId ? updated : state.selectedPackingList,
    }));
  },

  fetchStats: async () => {
    set({ statsLoading: true });
    try {
      const stats = await wardrobeApi.getStatistics();
      set({ stats, statsLoading: false });
    } catch (error) {
      console.error("Failed to fetch stats:", error);
      set({ statsLoading: false });
    }
  },

  setFilters: (filters) => {
    set({ filters });
  },

  clearSelection: () => {
    set({
      selectedItem: null,
      selectedOutfit: null,
      selectedPackingList: null,
    });
  },
}));
