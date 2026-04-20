import { create } from "zustand";
import {
  moneyApi,
  type Expense,
  type ExpenseCategory,
  type Budget,
  type SpendingAnalytics,
  type SplitGroup,
  type SharedExpense,
  type SimplifiedDebt,
  type ExpenseFilters,
  type DateRange,
  type PaginatedResponse,
} from "@/lib/api/money";

export interface MoneyState {
  // Expenses
  expenses: Expense[];
  categories: ExpenseCategory[];
  selectedExpense: Expense | null;
  expenseFilters: ExpenseFilters;
  expensePagination: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };

  // Budgets
  budgets: Budget[];
  selectedBudget: Budget | null;

  // Analytics
  analytics: SpendingAnalytics | null;
  analyticsDateRange: DateRange;

  // Split Groups
  splitGroups: SplitGroup[];
  selectedGroup: SplitGroup | null;
  groupExpenses: SharedExpense[];
  simplifiedDebts: SimplifiedDebt[];

  // UI State
  isLoading: boolean;
  isSubmitting: boolean;
  error: string | null;
}

export interface MoneyActions {
  // Categories
  fetchCategories: () => Promise<void>;
  createCategory: (data: {
    name: string;
    icon: string;
    color: string;
  }) => Promise<ExpenseCategory>;

  // Expenses
  fetchExpenses: (filters?: ExpenseFilters) => Promise<void>;
  createExpense: (data: {
    category_id: string;
    amount: number;
    description: string;
    expense_date: string;
  }) => Promise<Expense>;
  updateExpense: (
    expenseId: string,
    data: {
      category_id?: string;
      amount?: number;
      description?: string;
      expense_date?: string;
    }
  ) => Promise<Expense>;
  deleteExpense: (expenseId: string) => Promise<void>;
  selectExpense: (expense: Expense | null) => void;
  setExpenseFilters: (filters: ExpenseFilters) => void;
  setExpensePage: (page: number) => void;

  // Budgets
  fetchBudgets: () => Promise<void>;
  createBudget: (data: {
    category_id: string;
    amount: number;
    period: "weekly" | "monthly";
  }) => Promise<Budget>;
  updateBudget: (
    budgetId: string,
    data: { amount?: number; period?: "weekly" | "monthly" }
  ) => Promise<Budget>;
  deleteBudget: (budgetId: string) => Promise<void>;
  selectBudget: (budget: Budget | null) => void;

  // Analytics
  fetchAnalytics: (dateRange?: DateRange) => Promise<void>;
  setAnalyticsDateRange: (dateRange: DateRange) => void;

  // Split Groups
  fetchSplitGroups: () => Promise<void>;
  fetchSplitGroup: (groupId: string) => Promise<void>;
  createSplitGroup: (data: {
    name: string;
    description?: string;
    member_emails: string[];
  }) => Promise<SplitGroup>;
  selectGroup: (group: SplitGroup | null) => void;
  fetchGroupExpenses: (groupId: string) => Promise<void>;
  addGroupExpense: (
    groupId: string,
    data: {
      amount: number;
      description: string;
      split_type: "equal" | "percentage" | "exact";
      expense_date: string;
      splits?: { user_id: string; amount?: number; percentage?: number }[];
    }
  ) => Promise<SharedExpense>;
  fetchSimplifiedDebts: (groupId: string) => Promise<void>;
  settleDebt: (
    groupId: string,
    data: { to_user_id: string; amount: number }
  ) => Promise<void>;

  // Error handling
  clearError: () => void;
}

export type MoneyStore = MoneyState & MoneyActions;

const getDefaultDateRange = (): DateRange => {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 1);
  return {
    start_date: start.toISOString().split("T")[0],
    end_date: end.toISOString().split("T")[0],
  };
};

const initialState: MoneyState = {
  expenses: [],
  categories: [],
  selectedExpense: null,
  expenseFilters: {},
  expensePagination: {
    total: 0,
    page: 1,
    pageSize: 10,
    totalPages: 0,
  },
  budgets: [],
  selectedBudget: null,
  analytics: null,
  analyticsDateRange: getDefaultDateRange(),
  splitGroups: [],
  selectedGroup: null,
  groupExpenses: [],
  simplifiedDebts: [],
  isLoading: false,
  isSubmitting: false,
  error: null,
};

export const useMoneyStore = create<MoneyStore>((set, get) => ({
  ...initialState,

  // Categories
  fetchCategories: async () => {
    set({ isLoading: true, error: null });
    try {
      const categories = await moneyApi.getCategories();
      set({ categories, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch categories",
        isLoading: false,
      });
    }
  },

  createCategory: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const category = await moneyApi.createCategory(data);
      set((state) => ({
        categories: [...state.categories, category],
        isSubmitting: false,
      }));
      return category;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create category",
        isSubmitting: false,
      });
      throw error;
    }
  },

  // Expenses
  fetchExpenses: async (filters?: ExpenseFilters) => {
    set({ isLoading: true, error: null });
    try {
      const currentFilters = filters || get().expenseFilters;
      const response: PaginatedResponse<Expense> = await moneyApi.getExpenses(
        currentFilters
      );
      set({
        expenses: response.items,
        expensePagination: {
          total: response.total,
          page: response.page,
          pageSize: response.page_size,
          totalPages: response.total_pages,
        },
        expenseFilters: currentFilters,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch expenses",
        isLoading: false,
      });
    }
  },

  createExpense: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const expense = await moneyApi.createExpense(data);
      set((state) => ({
        expenses: [expense, ...state.expenses],
        isSubmitting: false,
      }));
      // Refresh budgets to update spent amounts
      get().fetchBudgets();
      return expense;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create expense",
        isSubmitting: false,
      });
      throw error;
    }
  },

  updateExpense: async (expenseId, data) => {
    set({ isSubmitting: true, error: null });
    try {
      const expense = await moneyApi.updateExpense(expenseId, data);
      set((state) => ({
        expenses: state.expenses.map((e) => (e.id === expenseId ? expense : e)),
        selectedExpense:
          state.selectedExpense?.id === expenseId ? expense : state.selectedExpense,
        isSubmitting: false,
      }));
      // Refresh budgets to update spent amounts
      get().fetchBudgets();
      return expense;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to update expense",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteExpense: async (expenseId) => {
    set({ isSubmitting: true, error: null });
    try {
      await moneyApi.deleteExpense(expenseId);
      set((state) => ({
        expenses: state.expenses.filter((e) => e.id !== expenseId),
        selectedExpense:
          state.selectedExpense?.id === expenseId ? null : state.selectedExpense,
        isSubmitting: false,
      }));
      // Refresh budgets to update spent amounts
      get().fetchBudgets();
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete expense",
        isSubmitting: false,
      });
      throw error;
    }
  },

  selectExpense: (expense) => {
    set({ selectedExpense: expense });
  },

  setExpenseFilters: (filters) => {
    set({ expenseFilters: filters });
    get().fetchExpenses(filters);
  },

  setExpensePage: (page) => {
    const newFilters = { ...get().expenseFilters, page };
    set({ expenseFilters: newFilters });
    get().fetchExpenses(newFilters);
  },

  // Budgets
  fetchBudgets: async () => {
    set({ isLoading: true, error: null });
    try {
      const budgets = await moneyApi.getBudgets();
      set({ budgets, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch budgets",
        isLoading: false,
      });
    }
  },

  createBudget: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const budget = await moneyApi.createBudget(data);
      set((state) => ({
        budgets: [...state.budgets, budget],
        isSubmitting: false,
      }));
      return budget;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create budget",
        isSubmitting: false,
      });
      throw error;
    }
  },

  updateBudget: async (budgetId, data) => {
    set({ isSubmitting: true, error: null });
    try {
      const budget = await moneyApi.updateBudget(budgetId, data);
      set((state) => ({
        budgets: state.budgets.map((b) => (b.id === budgetId ? budget : b)),
        selectedBudget:
          state.selectedBudget?.id === budgetId ? budget : state.selectedBudget,
        isSubmitting: false,
      }));
      return budget;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to update budget",
        isSubmitting: false,
      });
      throw error;
    }
  },

  deleteBudget: async (budgetId) => {
    set({ isSubmitting: true, error: null });
    try {
      await moneyApi.deleteBudget(budgetId);
      set((state) => ({
        budgets: state.budgets.filter((b) => b.id !== budgetId),
        selectedBudget:
          state.selectedBudget?.id === budgetId ? null : state.selectedBudget,
        isSubmitting: false,
      }));
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to delete budget",
        isSubmitting: false,
      });
      throw error;
    }
  },

  selectBudget: (budget) => {
    set({ selectedBudget: budget });
  },

  // Analytics
  fetchAnalytics: async (dateRange?: DateRange) => {
    set({ isLoading: true, error: null });
    try {
      const range = dateRange || get().analyticsDateRange;
      const analytics = await moneyApi.getAnalytics(range);
      set({ analytics, analyticsDateRange: range, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch analytics",
        isLoading: false,
      });
    }
  },

  setAnalyticsDateRange: (dateRange) => {
    set({ analyticsDateRange: dateRange });
    get().fetchAnalytics(dateRange);
  },

  // Split Groups
  fetchSplitGroups: async () => {
    set({ isLoading: true, error: null });
    try {
      const splitGroups = await moneyApi.getSplitGroups();
      set({ splitGroups, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch split groups",
        isLoading: false,
      });
    }
  },

  fetchSplitGroup: async (groupId) => {
    set({ isLoading: true, error: null });
    try {
      const group = await moneyApi.getSplitGroup(groupId);
      set({ selectedGroup: group, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to fetch split group",
        isLoading: false,
      });
    }
  },

  createSplitGroup: async (data) => {
    set({ isSubmitting: true, error: null });
    try {
      const group = await moneyApi.createSplitGroup(data);
      set((state) => ({
        splitGroups: [...state.splitGroups, group],
        isSubmitting: false,
      }));
      return group;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to create split group",
        isSubmitting: false,
      });
      throw error;
    }
  },

  selectGroup: (group) => {
    set({ selectedGroup: group, groupExpenses: [], simplifiedDebts: [] });
  },

  fetchGroupExpenses: async (groupId) => {
    set({ isLoading: true, error: null });
    try {
      const groupExpenses = await moneyApi.getGroupExpenses(groupId);
      set({ groupExpenses, isLoading: false });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to fetch group expenses",
        isLoading: false,
      });
    }
  },

  addGroupExpense: async (groupId, data) => {
    set({ isSubmitting: true, error: null });
    try {
      const expense = await moneyApi.addGroupExpense(groupId, data);
      set((state) => ({
        groupExpenses: [expense, ...state.groupExpenses],
        isSubmitting: false,
      }));
      // Refresh debts and group
      get().fetchSimplifiedDebts(groupId);
      get().fetchSplitGroup(groupId);
      return expense;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to add group expense",
        isSubmitting: false,
      });
      throw error;
    }
  },

  fetchSimplifiedDebts: async (groupId) => {
    set({ isLoading: true, error: null });
    try {
      const simplifiedDebts = await moneyApi.getSimplifiedDebts(groupId);
      set({ simplifiedDebts, isLoading: false });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to fetch simplified debts",
        isLoading: false,
      });
    }
  },

  settleDebt: async (groupId, data) => {
    set({ isSubmitting: true, error: null });
    try {
      await moneyApi.settleDebt(groupId, data);
      set({ isSubmitting: false });
      // Refresh debts and group
      get().fetchSimplifiedDebts(groupId);
      get().fetchSplitGroup(groupId);
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to settle debt",
        isSubmitting: false,
      });
      throw error;
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));
