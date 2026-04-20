import { create } from "zustand";

export interface UIState {
  sidebarOpen: boolean;
  theme: "light" | "dark" | "system";
  isOffline: boolean;
}

export interface UIActions {
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
  setOffline: (isOffline: boolean) => void;
}

export type UIStore = UIState & UIActions;

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  theme: "system",
  isOffline: false,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => set({ theme }),
  setOffline: (isOffline) => set({ isOffline }),
}));
