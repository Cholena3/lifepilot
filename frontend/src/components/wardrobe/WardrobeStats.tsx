"use client";

import { useEffect } from "react";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Shirt, DollarSign, TrendingUp, WashingMachine, AlertCircle } from "lucide-react";

export function WardrobeStats() {
  const { stats, statsLoading, fetchStats } = useWardrobeStore();

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (statsLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Shirt className="h-5 w-5 text-primary" />
              <div>
                <p className="text-2xl font-bold">{stats.total_items}</p>
                <p className="text-sm text-muted-foreground">Total Items</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-green-500" />
              <div>
                <p className="text-2xl font-bold">${stats.total_value.toFixed(0)}</p>
                <p className="text-sm text-muted-foreground">Total Value</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">
                  ${stats.average_cost_per_wear?.toFixed(2) || "N/A"}
                </p>
                <p className="text-sm text-muted-foreground">Avg Cost/Wear</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <WashingMachine className="h-5 w-5 text-orange-500" />
              <div>
                <p className="text-2xl font-bold">{stats.items_in_laundry}</p>
                <p className="text-sm text-muted-foreground">In Laundry</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Items by Type */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Items by Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.items_by_type).map(([type, count]) => (
              <div
                key={type}
                className="flex items-center gap-2 bg-muted px-3 py-1.5 rounded-full"
              >
                <span className="capitalize">{type.replace("_", " ")}</span>
                <span className="font-semibold">{count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Items by Color */}
      {Object.keys(stats.items_by_color).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Items by Color</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.items_by_color).map(([color, count]) => (
                <div
                  key={color}
                  className="flex items-center gap-2 bg-muted px-3 py-1.5 rounded-full"
                >
                  <div
                    className="w-4 h-4 rounded-full border"
                    style={{ backgroundColor: color }}
                  />
                  <span className="capitalize">{color}</span>
                  <span className="font-semibold">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Most Worn Items */}
      {stats.most_worn_items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Most Worn Items</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {stats.most_worn_items.map((item) => (
                <div key={item.id} className="flex-shrink-0 text-center">
                  <div className="w-16 h-16 bg-muted rounded-lg overflow-hidden">
                    {item.image_url ? (
                      <img
                        src={item.processed_image_url || item.image_url}
                        alt={item.name || item.item_type}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Shirt className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                  <p className="text-xs mt-1">{item.wear_count} wears</p>
                  {item.cost_per_wear && (
                    <p className="text-xs text-muted-foreground">
                      ${item.cost_per_wear.toFixed(2)}/wear
                    </p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Unworn Items Alert */}
      {stats.unworn_items.length > 0 && (
        <Card className="border-orange-200 bg-orange-50 dark:bg-orange-950/20">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              Unworn Items (6+ months)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-3">
              You have {stats.unworn_items.length} items that haven&apos;t been worn in over 6 months.
              Consider donating or selling them!
            </p>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {stats.unworn_items.slice(0, 5).map((item) => (
                <div key={item.id} className="flex-shrink-0">
                  <div className="w-16 h-16 bg-muted rounded-lg overflow-hidden">
                    {item.image_url ? (
                      <img
                        src={item.processed_image_url || item.image_url}
                        alt={item.name || item.item_type}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Shirt className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {stats.unworn_items.length > 5 && (
                <div className="flex-shrink-0 w-16 h-16 bg-muted rounded-lg flex items-center justify-center">
                  <span className="text-sm text-muted-foreground">
                    +{stats.unworn_items.length - 5}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
