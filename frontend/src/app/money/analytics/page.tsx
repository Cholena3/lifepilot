"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AnalyticsDashboard } from "@/components/money";
import { useAuthStore } from "@/store/auth-store";
import { useMoneyStore } from "@/store/money-store";

export default function AnalyticsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { error, clearError } = useMoneyStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

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
            <span className="font-medium">Analytics</span>
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

        <div className="mb-8">
          <h1 className="text-3xl font-bold">Spending Analytics</h1>
          <p className="text-muted-foreground mt-2">
            Visualize your spending patterns and trends
          </p>
        </div>

        <AnalyticsDashboard />
      </main>
    </div>
  );
}
