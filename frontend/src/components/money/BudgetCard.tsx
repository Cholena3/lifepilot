"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMoneyStore } from "@/store/money-store";
import type { Budget } from "@/lib/api/money";

interface BudgetCardProps {
  budget: Budget;
  onEdit?: (budget: Budget) => void;
}

export function BudgetCard({ budget, onEdit }: BudgetCardProps) {
  const { deleteBudget, categories, isSubmitting } = useMoneyStore();
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);

  const category = categories.find((c) => c.id === budget.category_id);
  const percentage = Math.min((budget.spent / budget.amount) * 100, 100);
  const remaining = budget.amount - budget.spent;

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  const getProgressColor = () => {
    if (percentage >= 100) return "bg-destructive";
    if (percentage >= 80) return "bg-orange-500";
    if (percentage >= 50) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getStatusText = () => {
    if (percentage >= 100) return "Budget exceeded!";
    if (percentage >= 80) return "Almost at limit";
    if (percentage >= 50) return "Halfway there";
    return "On track";
  };

  const handleDelete = async () => {
    try {
      await deleteBudget(budget.id);
      setShowDeleteDialog(false);
    } catch {
      // Error handled by store
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-4">
          <div className="flex items-center gap-3">
            {category && (
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                style={{ backgroundColor: category.color + "20" }}
              >
                {category.icon}
              </div>
            )}
            <div>
              <h3 className="font-medium">{category?.name || "Unknown"}</h3>
              <p className="text-sm text-muted-foreground capitalize">
                {budget.period} budget
              </p>
            </div>
          </div>
          <div className="flex gap-1">
            {onEdit && (
              <Button variant="ghost" size="sm" onClick={() => onEdit(budget)}>
                Edit
              </Button>
            )}
            <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="text-destructive">
                  Delete
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete Budget</DialogTitle>
                </DialogHeader>
                <p className="text-muted-foreground">
                  Are you sure you want to delete this budget? This action cannot
                  be undone.
                </p>
                <div className="flex justify-end gap-2 mt-4">
                  <Button
                    variant="outline"
                    onClick={() => setShowDeleteDialog(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={handleDelete}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">
              {formatAmount(budget.spent)} of {formatAmount(budget.amount)}
            </span>
            <span
              className={
                percentage >= 100
                  ? "text-destructive font-medium"
                  : percentage >= 80
                    ? "text-orange-500 font-medium"
                    : "text-muted-foreground"
              }
            >
              {percentage.toFixed(0)}%
            </span>
          </div>
          <div className="relative">
            <Progress value={percentage} className="h-3" />
            <div
              className={`absolute top-0 left-0 h-3 rounded-full transition-all ${getProgressColor()}`}
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-sm">
            <span
              className={
                remaining < 0 ? "text-destructive" : "text-muted-foreground"
              }
            >
              {remaining >= 0
                ? `${formatAmount(remaining)} remaining`
                : `${formatAmount(Math.abs(remaining))} over budget`}
            </span>
            <span
              className={
                percentage >= 100
                  ? "text-destructive"
                  : percentage >= 80
                    ? "text-orange-500"
                    : "text-green-500"
              }
            >
              {getStatusText()}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
