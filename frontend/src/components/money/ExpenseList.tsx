"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ExpenseCard } from "./ExpenseCard";
import { useMoneyStore } from "@/store/money-store";
import type { Expense } from "@/lib/api/money";

interface ExpenseListProps {
  onEditExpense?: (expense: Expense) => void;
}

export function ExpenseList({ onEditExpense }: ExpenseListProps) {
  const {
    expenses,
    categories,
    isLoading,
    expensePagination,
    expenseFilters,
    fetchExpenses,
    fetchCategories,
    setExpenseFilters,
    setExpensePage,
  } = useMoneyStore();

  const [localFilters, setLocalFilters] = React.useState({
    category_id: expenseFilters.category_id || "",
    start_date: expenseFilters.start_date || "",
    end_date: expenseFilters.end_date || "",
  });

  React.useEffect(() => {
    fetchExpenses();
    fetchCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilterChange = (
    field: "category_id" | "start_date" | "end_date",
    value: string
  ) => {
    setLocalFilters((prev) => ({ ...prev, [field]: value }));
  };

  const applyFilters = () => {
    const filters: Record<string, string | undefined> = {};
    if (localFilters.category_id) filters.category_id = localFilters.category_id;
    if (localFilters.start_date) filters.start_date = localFilters.start_date;
    if (localFilters.end_date) filters.end_date = localFilters.end_date;
    setExpenseFilters(filters);
  };

  const clearFilters = () => {
    setLocalFilters({ category_id: "", start_date: "", end_date: "" });
    setExpenseFilters({});
  };

  const totalAmount = expenses.reduce((sum, exp) => sum + exp.amount, 0);

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-2">
              <Label htmlFor="filterCategory">Category</Label>
              <Select
                id="filterCategory"
                value={localFilters.category_id}
                onChange={(e) => handleFilterChange("category_id", e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.icon} {cat.name}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="startDate">From</Label>
              <Input
                id="startDate"
                type="date"
                value={localFilters.start_date}
                onChange={(e) => handleFilterChange("start_date", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">To</Label>
              <Input
                id="endDate"
                type="date"
                value={localFilters.end_date}
                onChange={(e) => handleFilterChange("end_date", e.target.value)}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={applyFilters} className="flex-1">
                Apply
              </Button>
              <Button variant="outline" onClick={clearFilters}>
                Clear
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="flex items-center justify-between">
        <p className="text-muted-foreground">
          {expensePagination.total} expense{expensePagination.total !== 1 && "s"}
        </p>
        <p className="font-semibold">Total: {formatAmount(totalAmount)}</p>
      </div>

      {/* Expense List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : expenses.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No expenses found. Log your first expense to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {expenses.map((expense) => (
            <ExpenseCard
              key={expense.id}
              expense={expense}
              onEdit={onEditExpense}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {expensePagination.totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpensePage(expensePagination.page - 1)}
            disabled={expensePagination.page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {expensePagination.page} of {expensePagination.totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpensePage(expensePagination.page + 1)}
            disabled={expensePagination.page >= expensePagination.totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
