"use client";

/**
 * Feature Usage Card component for admin dashboard.
 * 
 * Displays feature usage statistics by module including total records,
 * active users, and recent activity.
 * 
 * Validates: Requirements 38.2
 */

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  LayoutGrid,
  FileText,
  Wallet,
  Heart,
  Shirt,
  Briefcase,
  GraduationCap,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import type { FeatureUsage, ModuleUsageStats } from "@/lib/api/admin";

interface FeatureUsageCardProps {
  usage: FeatureUsage | null;
  isLoading: boolean;
}

const MODULE_ICONS: Record<string, React.ReactNode> = {
  documents: <FileText className="h-4 w-4" />,
  money: <Wallet className="h-4 w-4" />,
  health: <Heart className="h-4 w-4" />,
  wardrobe: <Shirt className="h-4 w-4" />,
  career: <Briefcase className="h-4 w-4" />,
  exam: <GraduationCap className="h-4 w-4" />,
};

const MODULE_COLORS: Record<string, string> = {
  documents: "#10b981",
  money: "#f59e0b",
  health: "#ef4444",
  wardrobe: "#8b5cf6",
  career: "#06b6d4",
  exam: "#3b82f6",
};

export function FeatureUsageCard({ usage, isLoading }: FeatureUsageCardProps) {
  if (isLoading && !usage) {
    return <FeatureUsageCardSkeleton />;
  }

  if (!usage) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Feature Usage</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const chartData = usage.modules.map((module) => ({
    name: formatModuleName(module.module_name),
    records: module.total_records,
    users: module.active_users,
    color: MODULE_COLORS[module.module_name.toLowerCase()] || "#6b7280",
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <LayoutGrid className="h-5 w-5" />
          Feature Usage by Module
        </CardTitle>
        <CardDescription>
          Usage statistics across all modules
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Most/Least Active Badges */}
        <div className="flex flex-wrap gap-2">
          {usage.most_active_module && (
            <Badge variant="default" className="flex items-center gap-1">
              <TrendingUp className="h-3 w-3" />
              Most Active: {formatModuleName(usage.most_active_module)}
            </Badge>
          )}
          {usage.least_active_module && (
            <Badge variant="secondary" className="flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              Least Active: {formatModuleName(usage.least_active_module)}
            </Badge>
          )}
        </div>

        {/* Records by Module Chart */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Total Records by Module</h4>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  width={80}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                />
                <Bar dataKey="records" name="Total Records" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Module Details Table */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Module Details</h4>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="text-left p-3 font-medium">Module</th>
                  <th className="text-right p-3 font-medium">Records</th>
                  <th className="text-right p-3 font-medium">Active Users</th>
                  <th className="text-right p-3 font-medium">7d Activity</th>
                  <th className="text-right p-3 font-medium">30d Activity</th>
                </tr>
              </thead>
              <tbody>
                {usage.modules.map((module) => (
                  <ModuleRow key={module.module_name} module={module} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ModuleRow({ module }: { module: ModuleUsageStats }) {
  const icon = MODULE_ICONS[module.module_name.toLowerCase()];
  const color = MODULE_COLORS[module.module_name.toLowerCase()] || "#6b7280";

  return (
    <tr className="border-t">
      <td className="p-3">
        <div className="flex items-center gap-2">
          <span style={{ color }}>{icon}</span>
          <span>{formatModuleName(module.module_name)}</span>
        </div>
      </td>
      <td className="text-right p-3 font-mono">
        {module.total_records.toLocaleString()}
      </td>
      <td className="text-right p-3 font-mono">
        {module.active_users.toLocaleString()}
      </td>
      <td className="text-right p-3 font-mono">
        {module.records_created_7d.toLocaleString()}
      </td>
      <td className="text-right p-3 font-mono">
        {module.records_created_30d.toLocaleString()}
      </td>
    </tr>
  );
}

function formatModuleName(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1).toLowerCase();
}

function FeatureUsageCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-64 mt-2" />
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex gap-2">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-6 w-32" />
        </div>
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </CardContent>
    </Card>
  );
}
