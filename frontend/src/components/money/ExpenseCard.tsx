"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMoneyStore } from "@/store/money-store";
import type { Expense } from "@/lib/api/money";

interface ExpenseCardProps {
  expense: Expense;
  onEdit?: (expense: Expense) => void;
}

export function ExpenseCard({ expense, onEdit }: ExpenseCardProps) {
  const { deleteExpense, categories, isSubmitting } = useMoneyStore();
  const [showDeleteDialog, setShowDeleteDialog] = React.useState(false);

  const category = categories.find((c) => c.id === expense.category_id);

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const handleDelete = async () => {
    try {
      await deleteExpense(expense.id);
      setShowDeleteDialog(false);
    } catch {
      // Error handled by store
    }
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-3">
            {category && (
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                style={{ backgroundColor: category.color + "20" }}
              >
                {category.icon}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="font-medium truncate">{expense.description}</h3>
              <p className="text-sm text-muted-foreground">
                {formatDate(expense.expense_date)}
              </p>
              {category && (
                <Badge
                  variant="outline"
                  className="mt-1"
                  style={{
                    borderColor: category.color,
                    color: category.color,
                  }}
                >
                  {category.name}
                </Badge>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="font-semibold text-lg">{formatAmount(expense.amount)}</p>
            <div className="flex gap-1 mt-2">
              {onEdit && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onEdit(expense)}
                >
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
                    <DialogTitle>Delete Expense</DialogTitle>
                  </DialogHeader>
                  <p className="text-muted-foreground">
                    Are you sure you want to delete this expense? This action
                    cannot be undone.
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
        </div>
        {expense.receipt_url && (
          <div className="mt-3 pt-3 border-t">
            <a
              href={expense.receipt_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary hover:underline"
            >
              View Receipt
            </a>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
