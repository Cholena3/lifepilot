"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SpendingChart } from "./SpendingChart";
import { TrendChart } from "./TrendChart";
import { useMoneyStore } from "@/store/money-store";

export function AnalyticsDashboard() {
  const {
    analytics,
    analyticsDateRange,
    isLoading,
    fetchAnalytics,
    setAnalyticsDateRange,
  } = useMoneyStore();

  const [localDateRange, setLocalDateRange] = React.useState(analyticsDateRange);

  React.useEffect(() => {
    fetchAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleDateChange = (field: "start_date" | "end_date", value: string) => {
    setLocalDateRange((prev) => ({ ...prev, [field]: value }));
  };

  const applyDateRange = () => {
    setAnalyticsDateRange(localDateRange);
  };

  const setPresetRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    const range = {
      start_date: start.toISOString().split("T")[0],
      end_date: end.toISOString().split("T")[0],
    };
    setLocalDateRange(range);
    setAnalyticsDateRange(range);
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    const sign = value >= 0 ? "+" : "";
    return `${sign}${value.toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Date Range Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="startDate">From</Label>
              <Input
                id="startDate"
                type="date"
                value={localDateRange.start_date}
                onChange={(e) => handleDateChange("start_date", e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">To</Label>
              <Input
                id="endDate"
                type="date"
                value={localDateRange.end_date}
                onChange={(e) => handleDateChange("end_date", e.target.value)}
              />
            </div>
            <Button onClick={applyDateRange}>Apply</Button>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPresetRange(7)}>
                7 Days
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPresetRange(30)}>
                30 Days
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPresetRange(90)}>
                90 Days
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      {analytics && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Spent
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {formatAmount(analytics.total_spent)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Previous Period
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {formatAmount(analytics.comparison.previous_period)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Change
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p
                className={`text-2xl font-bold ${
                  analytics.comparison.change_percentage > 0
                    ? "text-destructive"
                    : analytics.comparison.change_percentage < 0
                      ? "text-green-500"
                      : ""
                }`}
              >
                {formatPercentage(analytics.comparison.change_percentage)}
              </p>
              <p className="text-sm text-muted-foreground">
                {analytics.comparison.change_percentage > 0
                  ? "More than last period"
                  : analytics.comparison.change_percentage < 0
                    ? "Less than last period"
                    : "Same as last period"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      {analytics && (
        <div className="grid gap-6 lg:grid-cols-2">
          <SpendingChart data={analytics.by_category} />
          <TrendChart data={analytics.trends} />
        </div>
      )}

      {/* Category Breakdown Table */}
      {analytics && analytics.by_category.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {analytics.by_category.map((cat) => (
                <div
                  key={cat.category_id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: cat.category_color }}
                    />
                    <span className="font-medium">{cat.category_name}</span>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{formatAmount(cat.amount)}</p>
                    <p className="text-sm text-muted-foreground">
                      {cat.percentage.toFixed(1)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {!analytics && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No analytics data available. Start logging expenses to see insights.
          </CardContent>
        </Card>
      )}
    </div>
  );
}
