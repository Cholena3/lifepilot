"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AddExpenseForm,
  BalanceSummary,
  SimplifiedDebts,
} from "@/components/money";
import { useAuthStore } from "@/store/auth-store";
import { useMoneyStore } from "@/store/money-store";

export default function SplitGroupDetailPage() {
  const router = useRouter();
  const params = useParams();
  const groupId = params.id as string;

  const { user, isAuthenticated } = useAuthStore();
  const {
    selectedGroup,
    groupExpenses,
    simplifiedDebts,
    isLoading,
    error,
    clearError,
    fetchSplitGroup,
    fetchGroupExpenses,
    fetchSimplifiedDebts,
  } = useMoneyStore();

  const [activeTab, setActiveTab] = React.useState("balances");

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
      return;
    }

    if (groupId) {
      fetchSplitGroup(groupId);
      fetchGroupExpenses(groupId);
      fetchSimplifiedDebts(groupId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, groupId]);

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

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (isLoading && !selectedGroup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!selectedGroup) {
    return (
      <div className="min-h-screen bg-background">
        <header className="border-b">
          <div className="container mx-auto px-4 py-4">
            <Link href="/money/splits" className="text-primary hover:underline">
              ← Back to Split Groups
            </Link>
          </div>
        </header>
        <main className="container mx-auto px-4 py-8">
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              Group not found.
            </CardContent>
          </Card>
        </main>
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
            <Link href="/money/splits" className="hover:text-primary">
              Splits
            </Link>
            <span className="text-muted-foreground">/</span>
            <span className="font-medium">{selectedGroup.name}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button variant="outline" size="sm" asChild>
              <Link href="/money/splits">Back</Link>
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
          <h1 className="text-3xl font-bold">{selectedGroup.name}</h1>
          {selectedGroup.description && (
            <p className="text-muted-foreground mt-2">
              {selectedGroup.description}
            </p>
          )}
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6">
            <TabsTrigger value="balances">Balances</TabsTrigger>
            <TabsTrigger value="expenses">Expenses</TabsTrigger>
            <TabsTrigger value="settle">Settle Up</TabsTrigger>
            <TabsTrigger value="add">Add Expense</TabsTrigger>
          </TabsList>

          <TabsContent value="balances">
            <BalanceSummary members={selectedGroup.members} />
          </TabsContent>

          <TabsContent value="expenses">
            <Card>
              <CardHeader>
                <CardTitle>Group Expenses</CardTitle>
              </CardHeader>
              <CardContent>
                {groupExpenses.length === 0 ? (
                  <p className="text-center text-muted-foreground py-4">
                    No expenses yet. Add your first shared expense.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {groupExpenses.map((expense) => (
                      <div
                        key={expense.id}
                        className="flex items-start justify-between py-3 border-b last:border-0"
                      >
                        <div>
                          <p className="font-medium">{expense.description}</p>
                          <p className="text-sm text-muted-foreground">
                            Paid by {expense.paid_by_name} •{" "}
                            {formatDate(expense.expense_date)}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1">
                            Split: {expense.split_type}
                          </p>
                        </div>
                        <p className="font-semibold text-lg">
                          {formatAmount(expense.amount)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settle">
            <SimplifiedDebts
              groupId={groupId}
              debts={simplifiedDebts}
              currentUserId={user.id}
            />
          </TabsContent>

          <TabsContent value="add">
            <div className="max-w-xl">
              <AddExpenseForm
                groupId={groupId}
                onSuccess={() => setActiveTab("expenses")}
              />
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
