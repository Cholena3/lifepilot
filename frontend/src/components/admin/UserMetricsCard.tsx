"use client";

/**
 * User Metrics Card component for admin dashboard.
 * 
 * Displays user counts and growth trends including total users,
 * active users, and new user registrations.
 * 
 * Validates: Requirements 38.1
 */

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import { Users, UserPlus, TrendingUp, Shield, Globe } from "lucide-react";
import type { UserMetrics, UserGrowthDataPoint } from "@/lib/api/admin";

interface UserMetricsCardProps {
  metrics: UserMetrics | null;
  isLoading: boolean;
}

export function UserMetricsCard({ metrics, isLoading }: UserMetricsCardProps) {
  if (isLoading && !metrics) {
    return <UserMetricsCardSkeleton />;
  }

  if (!metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>User Metrics</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const formatChartData = (data: UserGrowthDataPoint[]) => {
    return data.map((item) => ({
      date: new Date(item.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      total: item.total_users,
      new: item.new_users,
    }));
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          User Metrics
        </CardTitle>
        <CardDescription>User counts and growth trends</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricBox
            icon={<Users className="h-4 w-4 text-blue-500" />}
            label="Total Users"
            value={metrics.total_users.toLocaleString()}
          />
          <MetricBox
            icon={<UserPlus className="h-4 w-4 text-green-500" />}
            label="New Today"
            value={metrics.new_users_today.toLocaleString()}
          />
          <MetricBox
            icon={<Shield className="h-4 w-4 text-purple-500" />}
            label="Phone Verified"
            value={metrics.verified_phone_users.toLocaleString()}
          />
          <MetricBox
            icon={<Globe className="h-4 w-4 text-orange-500" />}
            label="OAuth Users"
            value={metrics.oauth_users.toLocaleString()}
          />
        </div>

        {/* Active Users */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Active Users</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-primary">
                {metrics.active_users_24h.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Last 24h</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-primary">
                {metrics.active_users_7d.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Last 7 days</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-primary">
                {metrics.active_users_30d.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Last 30 days</div>
            </div>
          </div>
        </div>

        {/* Growth Trend Chart */}
        {metrics.growth_trend.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              User Growth Trend (30 days)
            </h4>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={formatChartData(metrics.growth_trend)}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="total"
                    name="Total Users"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* New Users Chart */}
        {metrics.growth_trend.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">New User Registrations</h4>
            <div className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={formatChartData(metrics.growth_trend)}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "8px",
                    }}
                  />
                  <Bar
                    dataKey="new"
                    name="New Users"
                    fill="hsl(var(--primary))"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MetricBox({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="p-3 border rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}

function UserMetricsCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-48 mt-2" />
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}
