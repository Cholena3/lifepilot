"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BudgetForm, BudgetList } from "@/components/money";
import { useAuthStore } from "@/store/auth-store";
import { useMoneyStore } from "@/store/money-store";
import type { Budget } from "@/lib/api/money";

export default function BudgetsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { error, clearError } = useMoneyStore();
  const [editingBudget, setEditingBudget] = React.useState<Budget | null>(null);
  const [showForm, setShowForm] = React.useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  const handleEditBudget = (budget: Budget) => {
    setEditingBudget(budget);
    setShowForm(true);
  };

  const handleSuccess = () => {
    setShowForm(false);
    setEditingBudget(null);
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
            <span className="font-medium">Budgets</span>
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
            <h1 className="text-3xl font-bold">Budgets</h1>
            <p className="text-muted-foreground mt-2">
              Set and track your spending budgets
            </p>
          </div>
          <Button onClick={() => setShowForm(true)}>Create Budget</Button>
        </div>

        {showForm && (
          <div className="mb-8 max-w-xl">
            <BudgetForm
              onSuccess={handleSuccess}
              editBudget={
                editingBudget
                  ? {
                      id: editingBudget.id,
                      category_id: editingBudget.category_id,
                      amount: editingBudget.amount,
                      period: editingBudget.period,
                    }
                  : undefined
              }
            />
            <Button
              variant="outline"
              className="w-full mt-2"
              onClick={() => {
                setShowForm(false);
                setEditingBudget(null);
              }}
            >
              Cancel
            </Button>
          </div>
        )}

        <BudgetList onEditBudget={handleEditBudget} />
      </main>
    </div>
  );
}
