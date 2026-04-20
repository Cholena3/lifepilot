"use client";

/**
 * Admin Dashboard Page.
 * 
 * Protected admin-only page displaying system metrics including:
 * - User counts and growth trends
 * - Feature usage by module
 * - System health metrics
 * - Scraper job status
 * 
 * Validates: Requirements 38.1, 38.2, 38.3, 38.4
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuthStore } from "@/store/auth-store";
import { useAdminStore } from "@/store/admin-store";
import {
  UserMetricsCard,
  FeatureUsageCard,
  SystemHealthCard,
  ScraperStatusCard,
} from "@/components/admin";
import {
  Shield,
  RefreshCw,
  AlertTriangle,
  Users,
  LayoutGrid,
  Activity,
  Bot,
} from "lucide-react";

// Admin user IDs - in production, this would be fetched from the backend
// or determined by a role field on the user object
const ADMIN_USER_IDS: Set<string> = new Set([
  // Add admin user IDs here
]);

// For demo purposes, we'll check if the user email contains "admin"
// In production, use proper role-based access control
function isAdminUser(user: { id: string; email: string } | null): boolean {
  if (!user) return false;
  // Check if user ID is in admin list or email contains "admin"
  return ADMIN_USER_IDS.has(user.id) || user.email.toLowerCase().includes("admin");
}

export default function AdminDashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const {
    userMetrics,
    featureUsage,
    systemPerformance,
    scraperStatus,
    isLoading,
    error,
    lastRefreshed,
    fetchAllAdminData,
    clearError,
  } = useAdminStore();

  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  // Check authentication and admin status
  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
      return;
    }

    const adminStatus = isAdminUser(user);
    setIsAdmin(adminStatus);

    if (!adminStatus) {
      // Not an admin, redirect to dashboard
      router.push("/dashboard");
    }
  }, [isAuthenticated, user, router]);

  // Fetch admin data on mount
  useEffect(() => {
    if (isAdmin) {
      fetchAllAdminData();
    }
  }, [isAdmin, fetchAllAdminData]);

  // Show loading while checking auth/admin status
  if (!isAuthenticated || isAdmin === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Show access denied if not admin
  if (!isAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Access Denied
            </CardTitle>
            <CardDescription>
              You do not have permission to access the admin dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/dashboard">Return to Dashboard</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-2xl font-bold text-primary">
              LifePilot
            </Link>
            <span className="text-muted-foreground">/</span>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <span className="font-semibold">Admin Dashboard</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {user?.email}
            </span>
            <Button asChild variant="outline" size="sm">
              <Link href="/dashboard">Exit Admin</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Admin Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Monitor system health, user metrics, and feature usage
            </p>
          </div>
          <div className="flex items-center gap-4">
            {lastRefreshed && (
              <span className="text-sm text-muted-foreground">
                Last updated: {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
            <Button
              onClick={() => fetchAllAdminData()}
              disabled={isLoading}
              variant="outline"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Card className="mb-6 border-red-200 bg-red-50">
            <CardContent className="py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-red-800">
                  <AlertTriangle className="h-5 w-5" />
                  <span>{error}</span>
                </div>
                <Button variant="ghost" size="sm" onClick={clearError}>
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tabs for different sections */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <LayoutGrid className="h-4 w-4" />
              <span className="hidden sm:inline">Overview</span>
            </TabsTrigger>
            <TabsTrigger value="users" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Users</span>
            </TabsTrigger>
            <TabsTrigger value="health" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              <span className="hidden sm:inline">Health</span>
            </TabsTrigger>
            <TabsTrigger value="scrapers" className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              <span className="hidden sm:inline">Scrapers</span>
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Quick Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <QuickStatCard
                title="Total Users"
                value={userMetrics?.total_users.toLocaleString() || "—"}
                description="Registered users"
                icon={<Users className="h-4 w-4" />}
              />
              <QuickStatCard
                title="Active Today"
                value={userMetrics?.active_users_24h.toLocaleString() || "—"}
                description="Users in last 24h"
                icon={<Activity className="h-4 w-4" />}
              />
              <QuickStatCard
                title="Error Rate"
                value={
                  systemPerformance
                    ? `${Number(systemPerformance.error_rate_24h).toFixed(2)}%`
                    : "—"
                }
                description="Last 24 hours"
                icon={<AlertTriangle className="h-4 w-4" />}
                variant={
                  systemPerformance && Number(systemPerformance.error_rate_24h) > 5
                    ? "destructive"
                    : "default"
                }
              />
              <QuickStatCard
                title="Scraper Health"
                value={scraperStatus?.scraper_health || "—"}
                description="Overall status"
                icon={<Bot className="h-4 w-4" />}
                variant={
                  scraperStatus?.scraper_health === "unhealthy"
                    ? "destructive"
                    : scraperStatus?.scraper_health === "degraded"
                    ? "warning"
                    : "default"
                }
              />
            </div>

            {/* Main Content Grid */}
            <div className="grid gap-6 lg:grid-cols-2">
              <UserMetricsCard metrics={userMetrics} isLoading={isLoading} />
              <FeatureUsageCard usage={featureUsage} isLoading={isLoading} />
            </div>
            <div className="grid gap-6 lg:grid-cols-2">
              <SystemHealthCard performance={systemPerformance} isLoading={isLoading} />
              <ScraperStatusCard status={scraperStatus} isLoading={isLoading} />
            </div>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users">
            <UserMetricsCard metrics={userMetrics} isLoading={isLoading} />
            <div className="mt-6">
              <FeatureUsageCard usage={featureUsage} isLoading={isLoading} />
            </div>
          </TabsContent>

          {/* Health Tab */}
          <TabsContent value="health">
            <SystemHealthCard performance={systemPerformance} isLoading={isLoading} />
          </TabsContent>

          {/* Scrapers Tab */}
          <TabsContent value="scrapers">
            <ScraperStatusCard status={scraperStatus} isLoading={isLoading} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function QuickStatCard({
  title,
  value,
  description,
  icon,
  variant = "default",
}: {
  title: string;
  value: string;
  description: string;
  icon: React.ReactNode;
  variant?: "default" | "destructive" | "warning";
}) {
  const variantStyles = {
    default: "",
    destructive: "border-red-200 bg-red-50",
    warning: "border-yellow-200 bg-yellow-50",
  };

  return (
    <Card className={variantStyles[variant]}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  );
}
