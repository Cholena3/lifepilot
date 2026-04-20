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
import { Skeleton } from "@/components/ui/skeleton";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useAnalyticsStore } from "@/store/analytics-store";
import type { LifeScoreTrend, ModuleScores } from "@/lib/api/analytics";

const MODULE_COLORS: Record<keyof ModuleScores, string> = {
  exam: "#3b82f6",
  document: "#10b981",
  money: "#f59e0b",
  health: "#ef4444",
  wardrobe: "#8b5cf6",
  career: "#06b6d4",
};

const MODULE_LABELS: Record<keyof ModuleScores, string> = {
  exam: "Exams",
  document: "Documents",
  money: "Money",
  health: "Health",
  wardrobe: "Wardrobe",
  career: "Career",
};

export function LifeScoreCard() {
  const {
    currentScore,
    scoreTrend,
    scoreBreakdown,
    trendDays,
    isLoading,
    fetchCurrentScore,
    fetchScoreTrend,
    fetchScoreBreakdown,
    setTrendDays,
  } = useAnalyticsStore();

  React.useEffect(() => {
    fetchCurrentScore();
    fetchScoreTrend();
    fetchScoreBreakdown();
  }, [fetchCurrentScore, fetchScoreTrend, fetchScoreBreakdown]);

  const getTrendIndicator = () => {
    if (scoreTrend.length < 2) return null;
    const latest = scoreTrend[scoreTrend.length - 1]?.score || 0;
    const previous = scoreTrend[scoreTrend.length - 2]?.score || 0;
    const diff = latest - previous;

    if (diff > 0) {
      return (
        <span className="flex items-center text-green-600 text-sm">
          <TrendingUp className="h-4 w-4 mr-1" />
          +{diff.toFixed(1)}
        </span>
      );
    } else if (diff < 0) {
      return (
        <span className="flex items-center text-red-600 text-sm">
          <TrendingDown className="h-4 w-4 mr-1" />
          {diff.toFixed(1)}
        </span>
      );
    }
    return (
      <span className="flex items-center text-muted-foreground text-sm">
        <Minus className="h-4 w-4 mr-1" />
        No change
      </span>
    );
  };

  const formatChartData = (data: LifeScoreTrend[]) => {
    return data.map((item) => ({
      date: new Date(item.date).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      }),
      score: item.score,
    }));
  };

  if (isLoading && !currentScore) {
    return <LifeScoreCardSkeleton />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Life Score</CardTitle>
            <CardDescription>Your overall engagement score</CardDescription>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold text-primary">
              {currentScore?.total_score?.toFixed(0) || 0}
            </div>
            {getTrendIndicator()}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Trend Chart */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-medium">Score Trend</h4>
            <div className="flex gap-1">
              {[7, 14, 30].map((days) => (
                <Button
                  key={days}
                  variant={trendDays === days ? "default" : "outline"}
                  size="sm"
                  onClick={() => setTrendDays(days)}
                >
                  {days}d
                </Button>
              ))}
            </div>
          </div>
          <div className="h-48">
            {scoreTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={formatChartData(scoreTrend)}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    className="text-muted-foreground"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fontSize: 12 }}
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
                    dataKey="score"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                No trend data available
              </div>
            )}
          </div>
        </div>

        {/* Module Breakdown */}
        {scoreBreakdown && (
          <div>
            <h4 className="text-sm font-medium mb-4">Score Breakdown</h4>
            <div className="space-y-3">
              {(Object.keys(scoreBreakdown.module_scores) as Array<keyof ModuleScores>).map(
                (module) => {
                  const score = scoreBreakdown.module_scores[module];
                  const weight = scoreBreakdown.module_weights[module];
                  const contribution = (score * weight) / 100;

                  return (
                    <div key={module} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: MODULE_COLORS[module] }}
                          />
                          {MODULE_LABELS[module]}
                        </span>
                        <span className="text-muted-foreground">
                          {score.toFixed(0)} pts ({contribution.toFixed(1)} contribution)
                        </span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${score}%`,
                            backgroundColor: MODULE_COLORS[module],
                          }}
                        />
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function LifeScoreCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-6 w-24" />
            <Skeleton className="h-4 w-40 mt-2" />
          </div>
          <Skeleton className="h-12 w-16" />
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <Skeleton className="h-48 w-full" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="space-y-1">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-2 w-full" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
