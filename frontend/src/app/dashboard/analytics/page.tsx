"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/store/auth-store";
import { useAnalyticsStore } from "@/store/analytics-store";
import {
  LifeScoreCard,
  BadgeCollection,
  WeeklySummaryCard,
} from "@/components/analytics";
import { ArrowLeft, RefreshCw } from "lucide-react";

export default function AnalyticsDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { isLoading, error, fetchAllAnalytics, clearError } = useAnalyticsStore();

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchAllAnalytics();
    }
  }, [isAuthenticated, fetchAllAnalytics]);

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
            <Button variant="ghost" size="icon" asChild>
              <Link href="/dashboard">
                <ArrowLeft className="h-5 w-5" />
              </Link>
            </Button>
            <div>
              <h1 className="text-xl font-bold">Analytics Dashboard</h1>
              <p className="text-sm text-muted-foreground">
                Track your progress and achievements
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchAllAnalytics()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive flex items-center justify-between">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={clearError}>
              Dismiss
            </Button>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Life Score Card - Full width on mobile, half on desktop */}
          <div className="lg:col-span-1">
            <LifeScoreCard />
          </div>

          {/* Weekly Summary Card */}
          <div className="lg:col-span-1">
            <WeeklySummaryCard />
          </div>

          {/* Badge Collection - Full width */}
          <div className="lg:col-span-2">
            <BadgeCollection />
          </div>
        </div>
      </main>
    </div>
  );
}
