"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ExpenseForm, ExpenseList } from "@/components/money";
import { useAuthStore } from "@/store/auth-store";
import { useMoneyStore } from "@/store/money-store";
import type { Expense } from "@/lib/api/money";

export default function ExpensesPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { error, clearError } = useMoneyStore();
  const [editingExpense, setEditingExpense] = React.useState<Expense | null>(null);
  const [showForm, setShowForm] = React.useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setShowForm(true);
  };

  const handleSuccess = () => {
    setShowForm(false);
    setEditingExpense(null);
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-2xl font-bold text-primary">
              LifePilot
            </Link>
            <span className="text-muted-foreground">/</span>
            <Link href="/money" className="hover:text-primary">
              Money Manager
            </Link>
            <span className="text-muted-foreground">/</span>
            <span className="font-medium">Expenses</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button variant="outline" size="sm" asChild>
              <Link href="/money">Back</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && (
          <Card className="mb-4 border-destructive bg-destructive/10">
            <CardContent className="py-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-destructive">{error}</p>
                <Button variant="ghost" size="sm" onClick={clearError}>
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Expenses</h1>
            <p className="text-muted-foreground mt-2">
              View and manage all your expenses
            </p>
          </div>
          <Button onClick={() => setShowForm(true)}>Log Expense</Button>
        </div>

        {showForm && (
          <div className="mb-8 max-w-xl">
            <ExpenseForm
              onSuccess={handleSuccess}
              editExpense={
                editingExpense
                  ? {
                      id: editingExpense.id,
                      category_id: editingExpense.category_id,
                      amount: editingExpense.amount,
                      description: editingExpense.description,
                      expense_date: editingExpense.expense_date,
                    }
                  : undefined
              }
            />
            <Button
              variant="outline"
              className="w-full mt-2"
              onClick={() => {
                setShowForm(false);
                setEditingExpense(null);
              }}
            >
              Cancel
            </Button>
          </div>
        )}

        <ExpenseList onEditExpense={handleEditExpense} />
      </main>
    </div>
  );
}
