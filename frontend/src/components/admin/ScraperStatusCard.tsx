"use client";

/**
 * Scraper Status Card component for admin dashboard.
 * 
 * Displays scraper job status including last run times,
 * success rates, and overall scraper health.
 * 
 * Validates: Requirements 38.4
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
  Bot,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  FileText,
} from "lucide-react";
import type { ScraperStatus, ScraperJobStatus } from "@/lib/api/admin";

interface ScraperStatusCardProps {
  status: ScraperStatus | null;
  isLoading: boolean;
}

export function ScraperStatusCard({ status, isLoading }: ScraperStatusCardProps) {
  if (isLoading && !status) {
    return <ScraperStatusCardSkeleton />;
  }

  if (!status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Scraper Status</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Scraper Status
            </CardTitle>
            <CardDescription>
              Exam data scraper job status and health
            </CardDescription>
          </div>
          <HealthBadge health={status.scraper_health} />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="p-3 bg-muted rounded-lg text-center">
            <div className="text-2xl font-bold text-primary">
              {status.total_exams_scraped.toLocaleString()}
            </div>
            <div className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <FileText className="h-3 w-3" />
              Total Exams Scraped
            </div>
          </div>
          <div className="p-3 bg-muted rounded-lg text-center">
            <div className="text-2xl font-bold">
              {status.scrapers.length}
            </div>
            <div className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <Bot className="h-3 w-3" />
              Active Scrapers
            </div>
          </div>
          <div className="p-3 bg-muted rounded-lg text-center col-span-2 md:col-span-1">
            <div className="text-sm font-medium">
              {status.last_successful_scrape
                ? formatRelativeTime(new Date(status.last_successful_scrape))
                : "Never"}
            </div>
            <div className="text-xs text-muted-foreground flex items-center justify-center gap-1">
              <Clock className="h-3 w-3" />
              Last Successful Scrape
            </div>
          </div>
        </div>

        {/* Scraper Jobs List */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Scraper Jobs</h4>
          <div className="space-y-3">
            {status.scrapers.map((scraper) => (
              <ScraperJobCard key={scraper.source} job={scraper} />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function HealthBadge({ health }: { health: "healthy" | "degraded" | "unhealthy" }) {
  if (health === "healthy") {
    return (
      <Badge variant="default" className="bg-green-500 hover:bg-green-600">
        <CheckCircle className="h-3 w-3 mr-1" />
        Healthy
      </Badge>
    );
  }
  if (health === "degraded") {
    return (
      <Badge variant="secondary" className="bg-yellow-500 text-white hover:bg-yellow-600">
        <AlertTriangle className="h-3 w-3 mr-1" />
        Degraded
      </Badge>
    );
  }
  return (
    <Badge variant="destructive">
      <XCircle className="h-3 w-3 mr-1" />
      Unhealthy
    </Badge>
  );
}

function ScraperJobCard({ job }: { job: ScraperJobStatus }) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">{job.source}</span>
        </div>
        {job.last_run_success ? (
          <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-100">
            <CheckCircle className="h-3 w-3 mr-1" />
            Success
          </Badge>
        ) : (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Failed
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <div className="text-muted-foreground text-xs">Last Run</div>
          <div className="font-mono">
            {job.last_run_at
              ? formatRelativeTime(new Date(job.last_run_at))
              : "Never"}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Exams Found</div>
          <div className="font-mono">{job.exams_found}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Created</div>
          <div className="font-mono text-green-600">+{job.exams_created}</div>
        </div>
        <div>
          <div className="text-muted-foreground text-xs">Updated</div>
          <div className="font-mono text-blue-600">{job.exams_updated}</div>
        </div>
      </div>

      {job.next_scheduled_run && (
        <div className="mt-3 pt-3 border-t flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="h-3 w-3" />
          Next run: {formatDateTime(new Date(job.next_scheduled_run))}
        </div>
      )}

      {job.error_message && (
        <div className="mt-3 pt-3 border-t">
          <div className="flex items-start gap-2 text-sm text-red-600">
            <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span className="break-all">{job.error_message}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function formatDateTime(date: Date): string {
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function ScraperStatusCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
          <Skeleton className="h-6 w-20" />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
