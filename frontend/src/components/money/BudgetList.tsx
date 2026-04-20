"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { BudgetCard } from "./BudgetCard";
import { useMoneyStore } from "@/store/money-store";
import type { Budget } from "@/lib/api/money";

interface BudgetListProps {
  onEditBudget?: (budget: Budget) => void;
}

export function BudgetList({ onEditBudget }: BudgetListProps) {
  const { budgets, isLoading, fetchBudgets, fetchCategories } = useMoneyStore();

  React.useEffect(() => {
    fetchBudgets();
    fetchCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalBudget = budgets.reduce((sum, b) => sum + b.amount, 0);
  const totalSpent = budgets.reduce((sum, b) => sum + b.spent, 0);

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (budgets.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No budgets set. Create your first budget to start tracking spending.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <p className="text-sm text-muted-foreground">Total Budget</p>
              <p className="text-xl font-semibold">{formatAmount(totalBudget)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Spent</p>
              <p className="text-xl font-semibold">{formatAmount(totalSpent)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Remaining</p>
              <p
                className={`text-xl font-semibold ${
                  totalBudget - totalSpent < 0 ? "text-destructive" : "text-green-500"
                }`}
              >
                {formatAmount(totalBudget - totalSpent)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Budget Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {budgets.map((budget) => (
          <BudgetCard key={budget.id} budget={budget} onEdit={onEditBudget} />
        ))}
      </div>
    </div>
  );
}
