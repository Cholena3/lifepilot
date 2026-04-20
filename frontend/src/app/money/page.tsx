"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ExpenseForm,
  ExpenseList,
  BudgetForm,
  BudgetList,
} from "@/components/money";
import { useAuthStore } from "@/store/auth-store";
import { useMoneyStore } from "@/store/money-store";
import type { Expense, Budget } from "@/lib/api/money";

export default function MoneyPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { error, clearError } = useMoneyStore();
  const [activeTab, setActiveTab] = React.useState("expenses");
  const [editingExpense, setEditingExpense] = React.useState<Expense | null>(null);
  const [editingBudget, setEditingBudget] = React.useState<Budget | null>(null);
  const [showExpenseForm, setShowExpenseForm] = React.useState(false);
  const [showBudgetForm, setShowBudgetForm] = React.useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense);
    setShowExpenseForm(true);
  };

  const handleEditBudget = (budget: Budget) => {
    setEditingBudget(budget);
    setShowBudgetForm(true);
  };

  const handleExpenseSuccess = () => {
    setShowExpenseForm(false);
    setEditingExpense(null);
  };

  const handleBudgetSuccess = () => {
    setShowBudgetForm(false);
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
            <span className="font-medium">Money Manager</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard">Dashboard</Link>
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

        <div className="mb-8">
          <h1 className="text-3xl font-bold">Money Manager</h1>
          <p className="text-muted-foreground mt-2">
            Track expenses, manage budgets, and split bills with friends
          </p>
        </div>

        {/* Quick Links */}
        <div className="flex flex-wrap gap-2 mb-6">
          <Button variant="outline" size="sm" asChild>
            <Link href="/money/analytics">View Analytics</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/money/splits">Split Groups</Link>
          </Button>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="expenses">Expenses</TabsTrigger>
            <TabsTrigger value="budgets">Budgets</TabsTrigger>
            <TabsTrigger value="add">
              {activeTab === "budgets" ? "Add Budget" : "Log Expense"}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="expenses">
            <ExpenseList onEditExpense={handleEditExpense} />
          </TabsContent>

          <TabsContent value="budgets">
            <BudgetList onEditBudget={handleEditBudget} />
          </TabsContent>

          <TabsContent value="add">
            <div className="max-w-xl">
              {activeTab === "budgets" || showBudgetForm ? (
                <BudgetForm
                  onSuccess={handleBudgetSuccess}
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
              ) : (
                <ExpenseForm
                  onSuccess={handleExpenseSuccess}
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
              )}
            </div>
          </TabsContent>
        </Tabs>

        {/* Edit Dialogs */}
        {showExpenseForm && editingExpense && (
          <div className="fixed inset-0 bg-background/80 flex items-center justify-center z-50">
            <div className="max-w-xl w-full mx-4">
              <ExpenseForm
                onSuccess={handleExpenseSuccess}
                editExpense={{
                  id: editingExpense.id,
                  category_id: editingExpense.category_id,
                  amount: editingExpense.amount,
                  description: editingExpense.description,
                  expense_date: editingExpense.expense_date,
                }}
              />
              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => {
                  setShowExpenseForm(false);
                  setEditingExpense(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {showBudgetForm && editingBudget && (
          <div className="fixed inset-0 bg-background/80 flex items-center justify-center z-50">
            <div className="max-w-xl w-full mx-4">
              <BudgetForm
                onSuccess={handleBudgetSuccess}
                editBudget={{
                  id: editingBudget.id,
                  category_id: editingBudget.category_id,
                  amount: editingBudget.amount,
                  period: editingBudget.period,
                }}
              />
              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => {
                  setShowBudgetForm(false);
                  setEditingBudget(null);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
