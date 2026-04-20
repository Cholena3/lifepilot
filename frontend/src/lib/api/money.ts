import { apiClient } from "./client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Types
export interface ExpenseCategory {
  id: string;
  user_id: string;
  name: string;
  icon: string;
  color: string;
  is_default: boolean;
}

export interface Expense {
  id: string;
  user_id: string;
  category_id: string;
  category?: ExpenseCategory;
  amount: number;
  description: string;
  expense_date: string;
  receipt_url: string | null;
  ocr_data: Record<string, unknown> | null;
  created_at: string;
}

export interface Budget {
  id: string;
  user_id: string;
  category_id: string;
  category?: ExpenseCategory;
  amount: number;
  spent: number;
  period: "weekly" | "monthly";
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export interface SpendingAnalytics {
  total_spent: number;
  by_category: CategorySpending[];
  trends: SpendingTrend[];
  comparison: PeriodComparison;
}

export interface CategorySpending {
  category_id: string;
  category_name: string;
  category_color: string;
  amount: number;
  percentage: number;
}

export interface SpendingTrend {
  date: string;
  amount: number;
}

export interface PeriodComparison {
  current_period: number;
  previous_period: number;
  change_percentage: number;
}

export interface SplitGroup {
  id: string;
  created_by: string;
  name: string;
  description: string | null;
  created_at: string;
  members: SplitGroupMember[];
}

export interface SplitGroupMember {
  id: string;
  group_id: string;
  user_id: string;
  user_email: string;
  user_name: string;
  status: "pending" | "accepted" | "declined";
  joined_at: string | null;
  balance: number;
}

export interface SharedExpense {
  id: string;
  group_id: string;
  paid_by: string;
  paid_by_name: string;
  amount: number;
  description: string;
  split_type: "equal" | "percentage" | "exact";
  expense_date: string;
  splits: ExpenseSplit[];
}

export interface ExpenseSplit {
  id: string;
  shared_expense_id: string;
  user_id: string;
  user_name: string;
  amount: number;
  percentage: number | null;
}

export interface SimplifiedDebt {
  from_user_id: string;
  from_user_name: string;
  to_user_id: string;
  to_user_name: string;
  amount: number;
  upi_link: string | null;
}

export interface Settlement {
  id: string;
  group_id: string;
  from_user: string;
  to_user: string;
  amount: number;
  settled_at: string;
}

export interface ReceiptData {
  merchant_name: string | null;
  amount: number | null;
  date: string | null;
  items: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ExpenseFilters {
  category_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface DateRange {
  start_date: string;
  end_date: string;
}

// API Functions
export const moneyApi = {
  // Categories
  getCategories: async (): Promise<ExpenseCategory[]> => {
    return apiClient.get<ExpenseCategory[]>("/api/v1/expenses/categories");
  },

  createCategory: async (data: {
    name: string;
    icon: string;
    color: string;
  }): Promise<ExpenseCategory> => {
    return apiClient.post<ExpenseCategory>("/api/v1/expenses/categories", data);
  },

  // Expenses
  getExpenses: async (
    filters: ExpenseFilters = {}
  ): Promise<PaginatedResponse<Expense>> => {
    const params: Record<string, string> = {};
    if (filters.category_id) params.category_id = filters.category_id;
    if (filters.start_date) params.start_date = filters.start_date;
    if (filters.end_date) params.end_date = filters.end_date;
    if (filters.page) params.page = String(filters.page);
    if (filters.page_size) params.page_size = String(filters.page_size);

    return apiClient.get<PaginatedResponse<Expense>>("/api/v1/expenses", {
      params,
    });
  },

  createExpense: async (data: {
    category_id: string;
    amount: number;
    description: string;
    expense_date: string;
  }): Promise<Expense> => {
    return apiClient.post<Expense>("/api/v1/expenses", data);
  },

  updateExpense: async (
    expenseId: string,
    data: {
      category_id?: string;
      amount?: number;
      description?: string;
      expense_date?: string;
    }
  ): Promise<Expense> => {
    return apiClient.patch<Expense>(`/api/v1/expenses/${expenseId}`, data);
  },

  deleteExpense: async (expenseId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/expenses/${expenseId}`);
  },

  uploadReceipt: async (
    expenseId: string,
    file: File
  ): Promise<{ receipt_url: string; ocr_data: ReceiptData }> => {
    const formData = new FormData();
    formData.append("file", file);

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
      `${API_BASE_URL}/api/v1/expenses/${expenseId}/receipt`,
      {
        method: "POST",
        headers,
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to upload receipt");
    }

    return response.json();
  },

  processReceipt: async (file: File): Promise<ReceiptData> => {
    const formData = new FormData();
    formData.append("file", file);

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

    const response = await fetch(`${API_BASE_URL}/api/v1/expenses/receipts/process`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || "Failed to process receipt");
    }

    return response.json();
  },

  // Budgets
  getBudgets: async (): Promise<Budget[]> => {
    return apiClient.get<Budget[]>("/api/v1/budgets");
  },

  createBudget: async (data: {
    category_id: string;
    amount: number;
    period: "weekly" | "monthly";
  }): Promise<Budget> => {
    return apiClient.post<Budget>("/api/v1/budgets", data);
  },

  updateBudget: async (
    budgetId: string,
    data: { amount?: number; period?: "weekly" | "monthly" }
  ): Promise<Budget> => {
    return apiClient.patch<Budget>(`/api/v1/budgets/${budgetId}`, data);
  },

  deleteBudget: async (budgetId: string): Promise<void> => {
    return apiClient.delete(`/api/v1/budgets/${budgetId}`);
  },

  // Analytics
  getAnalytics: async (dateRange: DateRange): Promise<SpendingAnalytics> => {
    return apiClient.get<SpendingAnalytics>("/api/v1/analytics", {
      params: {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
      },
    });
  },

  // Split Groups
  getSplitGroups: async (): Promise<SplitGroup[]> => {
    return apiClient.get<SplitGroup[]>("/api/v1/splits/groups");
  },

  getSplitGroup: async (groupId: string): Promise<SplitGroup> => {
    return apiClient.get<SplitGroup>(`/api/v1/splits/groups/${groupId}`);
  },

  createSplitGroup: async (data: {
    name: string;
    description?: string;
    member_emails: string[];
  }): Promise<SplitGroup> => {
    return apiClient.post<SplitGroup>("/api/v1/splits/groups", data);
  },

  getGroupExpenses: async (groupId: string): Promise<SharedExpense[]> => {
    return apiClient.get<SharedExpense[]>(
      `/api/v1/splits/groups/${groupId}/expenses`
    );
  },

  addGroupExpense: async (
    groupId: string,
    data: {
      amount: number;
      description: string;
      split_type: "equal" | "percentage" | "exact";
      expense_date: string;
      splits?: { user_id: string; amount?: number; percentage?: number }[];
    }
  ): Promise<SharedExpense> => {
    return apiClient.post<SharedExpense>(
      `/api/v1/splits/groups/${groupId}/expenses`,
      data
    );
  },

  getSimplifiedDebts: async (groupId: string): Promise<SimplifiedDebt[]> => {
    return apiClient.get<SimplifiedDebt[]>(
      `/api/v1/splits/groups/${groupId}/simplified-debts`
    );
  },

  settleDebt: async (
    groupId: string,
    data: { to_user_id: string; amount: number }
  ): Promise<Settlement> => {
    return apiClient.post<Settlement>(
      `/api/v1/splits/groups/${groupId}/settlements`,
      data
    );
  },
};
