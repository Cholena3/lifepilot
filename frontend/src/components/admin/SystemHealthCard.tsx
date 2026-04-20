"use client";

/**
 * System Health Card component for admin dashboard.
 * 
 * Displays system performance metrics including response times,
 * error rates, and infrastructure health status.
 * 
 * Validates: Requirements 38.3
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
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Database,
  Server,
} from "lucide-react";
import type { SystemPerformance, EndpointPerformance } from "@/lib/api/admin";

interface SystemHealthCardProps {
  performance: SystemPerformance | null;
  isLoading: boolean;
}

export function SystemHealthCard({ performance, isLoading }: SystemHealthCardProps) {
  if (isLoading && !performance) {
    return <SystemHealthCardSkeleton />;
  }

  if (!performance) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
          <CardDescription>No data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const errorRateStatus = getErrorRateStatus(Number(performance.error_rate_24h));
  const responseTimeStatus = getResponseTimeStatus(Number(performance.avg_response_time_ms));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          System Health
        </CardTitle>
        <CardDescription>
          Performance metrics and infrastructure status
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Infrastructure Status */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Infrastructure Status</h4>
          <div className="grid grid-cols-2 gap-4">
            <StatusIndicator
              icon={<Database className="h-4 w-4" />}
              label="Database Pool"
              value={`${performance.database_connection_pool_size} connections`}
              status="healthy"
            />
            <StatusIndicator
              icon={<Server className="h-4 w-4" />}
              label="Redis Cache"
              value={performance.redis_connected ? "Connected" : "Disconnected"}
              status={performance.redis_connected ? "healthy" : "unhealthy"}
            />
          </div>
        </div>

        {/* Response Time Metrics */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Response Times
          </h4>
          <div className="grid grid-cols-3 gap-4">
            <MetricCard
              label="Average"
              value={`${Number(performance.avg_response_time_ms).toFixed(0)}ms`}
              status={responseTimeStatus}
            />
            <MetricCard
              label="P95"
              value={`${Number(performance.p95_response_time_ms).toFixed(0)}ms`}
              status={getResponseTimeStatus(Number(performance.p95_response_time_ms))}
            />
            <MetricCard
              label="P99"
              value={`${Number(performance.p99_response_time_ms).toFixed(0)}ms`}
              status={getResponseTimeStatus(Number(performance.p99_response_time_ms))}
            />
          </div>
        </div>

        {/* Request & Error Stats */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Last 24 Hours</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold">
                {performance.total_requests_24h.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Total Requests</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className="text-2xl font-bold text-red-500">
                {performance.total_errors_24h.toLocaleString()}
              </div>
              <div className="text-xs text-muted-foreground">Total Errors</div>
            </div>
            <div className="p-3 bg-muted rounded-lg text-center">
              <div className={`text-2xl font-bold ${getErrorRateColor(errorRateStatus)}`}>
                {Number(performance.error_rate_24h).toFixed(2)}%
              </div>
              <div className="text-xs text-muted-foreground">Error Rate</div>
            </div>
          </div>
        </div>

        {/* Error Rate Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Error Rate</span>
            <Badge variant={errorRateStatus === "healthy" ? "default" : "destructive"}>
              {errorRateStatus}
            </Badge>
          </div>
          <Progress
            value={Math.min(Number(performance.error_rate_24h), 100)}
            max={100}
            className={`h-2 ${getErrorRateProgressColor(errorRateStatus)}`}
          />
        </div>

        {/* Slowest Endpoints */}
        {performance.slowest_endpoints.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              Slowest Endpoints
            </h4>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-2 font-medium">Endpoint</th>
                    <th className="text-right p-2 font-medium">Avg</th>
                    <th className="text-right p-2 font-medium">P95</th>
                    <th className="text-right p-2 font-medium">Requests</th>
                  </tr>
                </thead>
                <tbody>
                  {performance.slowest_endpoints.slice(0, 5).map((endpoint, index) => (
                    <EndpointRow key={index} endpoint={endpoint} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Highest Error Endpoints */}
        {performance.highest_error_endpoints.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-500" />
              Highest Error Rate Endpoints
            </h4>
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-2 font-medium">Endpoint</th>
                    <th className="text-right p-2 font-medium">Errors</th>
                    <th className="text-right p-2 font-medium">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {performance.highest_error_endpoints.slice(0, 5).map((endpoint, index) => (
                    <tr key={index} className="border-t">
                      <td className="p-2">
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">
                          {endpoint.method} {endpoint.endpoint}
                        </code>
                      </td>
                      <td className="text-right p-2 font-mono text-red-500">
                        {endpoint.error_count}
                      </td>
                      <td className="text-right p-2 font-mono">
                        {Number(endpoint.error_rate).toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function StatusIndicator({
  icon,
  label,
  value,
  status,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  status: "healthy" | "degraded" | "unhealthy";
}) {
  const statusIcon = status === "healthy" ? (
    <CheckCircle className="h-4 w-4 text-green-500" />
  ) : status === "degraded" ? (
    <AlertTriangle className="h-4 w-4 text-yellow-500" />
  ) : (
    <XCircle className="h-4 w-4 text-red-500" />
  );

  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="flex items-center gap-2">
        {icon}
        <div>
          <div className="text-sm font-medium">{label}</div>
          <div className="text-xs text-muted-foreground">{value}</div>
        </div>
      </div>
      {statusIcon}
    </div>
  );
}

function MetricCard({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: "healthy" | "degraded" | "unhealthy";
}) {
  const bgColor =
    status === "healthy"
      ? "bg-green-50 border-green-200"
      : status === "degraded"
      ? "bg-yellow-50 border-yellow-200"
      : "bg-red-50 border-red-200";

  return (
    <div className={`p-3 rounded-lg border ${bgColor}`}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  );
}

function EndpointRow({ endpoint }: { endpoint: EndpointPerformance }) {
  return (
    <tr className="border-t">
      <td className="p-2">
        <code className="text-xs bg-muted px-1 py-0.5 rounded">
          {endpoint.method} {endpoint.endpoint}
        </code>
      </td>
      <td className="text-right p-2 font-mono">
        {Number(endpoint.avg_response_time_ms).toFixed(0)}ms
      </td>
      <td className="text-right p-2 font-mono">
        {Number(endpoint.p95_response_time_ms).toFixed(0)}ms
      </td>
      <td className="text-right p-2 font-mono">
        {endpoint.request_count.toLocaleString()}
      </td>
    </tr>
  );
}

function getErrorRateStatus(rate: number): "healthy" | "degraded" | "unhealthy" {
  if (rate < 1) return "healthy";
  if (rate < 5) return "degraded";
  return "unhealthy";
}

function getResponseTimeStatus(ms: number): "healthy" | "degraded" | "unhealthy" {
  if (ms < 500) return "healthy";
  if (ms < 2000) return "degraded";
  return "unhealthy";
}

function getErrorRateColor(status: "healthy" | "degraded" | "unhealthy"): string {
  if (status === "healthy") return "text-green-500";
  if (status === "degraded") return "text-yellow-500";
  return "text-red-500";
}

function getErrorRateProgressColor(status: "healthy" | "degraded" | "unhealthy"): string {
  if (status === "healthy") return "[&>div]:bg-green-500";
  if (status === "degraded") return "[&>div]:bg-yellow-500";
  return "[&>div]:bg-red-500";
}

function SystemHealthCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-4 w-64 mt-2" />
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
        <Skeleton className="h-48 w-full" />
      </CardContent>
    </Card>
  );
}
