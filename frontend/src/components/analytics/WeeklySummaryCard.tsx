"use client";

import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  DollarSign,
  FileText,
  Heart,
  Pill,
  Shirt,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  History,
} from "lucide-react";
import { useAnalyticsStore } from "@/store/analytics-store";
import type { WeeklySummary, WeeklySummaryMetrics } from "@/lib/api/analytics";

interface MetricConfig {
  key: keyof WeeklySummaryMetrics;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  format?: (value: number) => string;
  changeKey?: string;
}

const METRICS: MetricConfig[] = [
  {
    key: "expenses_total",
    label: "Total Expenses",
    icon: DollarSign,
    format: (v) => `$${v.toFixed(2)}`,
    changeKey: "expenses_change",
  },
  {
    key: "documents_added",
    label: "Documents Added",
    icon: FileText,
    changeKey: "documents_change",
  },
  {
    key: "health_records_logged",
    label: "Health Records",
    icon: Heart,
    changeKey: "health_records_change",
  },
  {
    key: "medicines_taken",
    label: "Medicines Taken",
    icon: Pill,
  },
  {
    key: "wardrobe_items_worn",
    label: "Items Worn",
    icon: Shirt,
    changeKey: "wardrobe_activity_change",
  },
  {
    key: "applications_submitted",
    label: "Job Applications",
    icon: Briefcase,
    changeKey: "career_activity_change",
  },
];

export function WeeklySummaryCard() {
  const {
    latestSummary,
    weeklySummaries,
    summariesPage,
    summariesTotalPages,
    isLoading,
    fetchLatestSummary,
    fetchWeeklySummaries,
  } = useAnalyticsStore();

  const [showHistory, setShowHistory] = React.useState(false);

  React.useEffect(() => {
    fetchLatestSummary();
  }, [fetchLatestSummary]);

  const formatDateRange = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    return `${startDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    })} - ${endDate.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    })}`;
  };

  const getChangeIndicator = (change: number) => {
    if (change > 0) {
      return (
        <span className="flex items-center text-green-600 text-xs">
          <TrendingUp className="h-3 w-3 mr-0.5" />
          +{change.toFixed(0)}%
        </span>
      );
    } else if (change < 0) {
      return (
        <span className="flex items-center text-red-600 text-xs">
          <TrendingDown className="h-3 w-3 mr-0.5" />
          {change.toFixed(0)}%
        </span>
      );
    }
    return (
      <span className="flex items-center text-muted-foreground text-xs">
        <Minus className="h-3 w-3 mr-0.5" />
        0%
      </span>
    );
  };

  const handleOpenHistory = () => {
    setShowHistory(true);
    fetchWeeklySummaries(1);
  };

  if (isLoading && !latestSummary) {
    return <WeeklySummarySkeleton />;
  }

  if (!latestSummary) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Weekly Summary</CardTitle>
          <CardDescription>Your activity overview</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            No weekly summary available yet. Check back after your first week of activity!
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Weekly Summary</CardTitle>
            <CardDescription className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {formatDateRange(latestSummary.week_start, latestSummary.week_end)}
            </CardDescription>
          </div>
          <Dialog open={showHistory} onOpenChange={setShowHistory}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" onClick={handleOpenHistory}>
                <History className="h-4 w-4 mr-1" />
                History
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Past Weekly Summaries</DialogTitle>
                <DialogDescription>
                  View your activity history week by week
                </DialogDescription>
              </DialogHeader>
              <WeeklySummaryHistory
                summaries={weeklySummaries}
                page={summariesPage}
                totalPages={summariesTotalPages}
                onPageChange={fetchWeeklySummaries}
                isLoading={isLoading}
              />
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {METRICS.map((metric) => {
            const value = latestSummary.metrics[metric.key];
            const change = metric.changeKey
              ? latestSummary.comparisons[metric.changeKey as keyof typeof latestSummary.comparisons]
              : undefined;
            const IconComponent = metric.icon;

            return (
              <div
                key={metric.key}
                className="p-3 rounded-lg border bg-card hover:shadow-sm transition-shadow"
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="p-1.5 rounded-md bg-primary/10">
                    <IconComponent className="h-4 w-4 text-primary" />
                  </div>
                  <span className="text-xs text-muted-foreground truncate">
                    {metric.label}
                  </span>
                </div>
                <div className="flex items-end justify-between">
                  <span className="text-xl font-semibold">
                    {metric.format ? metric.format(value) : value}
                  </span>
                  {change !== undefined && getChangeIndicator(change)}
                </div>
              </div>
            );
          })}
        </div>

        {/* Medicine Adherence */}
        {latestSummary.metrics.medicines_taken > 0 && (
          <div className="mt-4 p-3 rounded-lg border bg-muted/50">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Medicine Adherence</span>
              <Badge
                variant={
                  latestSummary.metrics.medicines_missed === 0
                    ? "default"
                    : "secondary"
                }
              >
                {latestSummary.metrics.medicines_taken} taken /{" "}
                {latestSummary.metrics.medicines_missed} missed
              </Badge>
            </div>
            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{
                  width: `${
                    (latestSummary.metrics.medicines_taken /
                      (latestSummary.metrics.medicines_taken +
                        latestSummary.metrics.medicines_missed)) *
                    100
                  }%`,
                }}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function WeeklySummaryHistory({
  summaries,
  page,
  totalPages,
  onPageChange,
  isLoading,
}: {
  summaries: WeeklySummary[];
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (summaries.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No past summaries available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {summaries.map((summary) => (
        <div key={summary.id} className="p-4 rounded-lg border">
          <div className="flex items-center justify-between mb-3">
            <span className="font-medium">
              {new Date(summary.week_start).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              })}{" "}
              -{" "}
              {new Date(summary.week_end).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Expenses:</span>{" "}
              ${summary.metrics.expenses_total.toFixed(2)}
            </div>
            <div>
              <span className="text-muted-foreground">Documents:</span>{" "}
              {summary.metrics.documents_added}
            </div>
            <div>
              <span className="text-muted-foreground">Health Records:</span>{" "}
              {summary.metrics.health_records_logged}
            </div>
          </div>
        </div>
      ))}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

function WeeklySummarySkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
          <Skeleton className="h-9 w-24" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="p-3 rounded-lg border">
              <Skeleton className="h-4 w-20 mb-2" />
              <Skeleton className="h-6 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
