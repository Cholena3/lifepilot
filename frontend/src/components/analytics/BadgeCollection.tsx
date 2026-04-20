"use client";

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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Trophy,
  Star,
  Award,
  Medal,
  Crown,
  Zap,
  Target,
  Flame,
  Lock,
} from "lucide-react";
import { useAnalyticsStore } from "@/store/analytics-store";
import type { BadgeDefinition } from "@/lib/api/analytics";

const BADGE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  trophy: Trophy,
  star: Star,
  award: Award,
  medal: Medal,
  crown: Crown,
  zap: Zap,
  target: Target,
  flame: Flame,
};

const CATEGORY_LABELS: Record<string, string> = {
  profile: "Profile",
  exam: "Exams",
  document: "Documents",
  money: "Money",
  health: "Health",
  wardrobe: "Wardrobe",
  career: "Career",
  streak: "Streaks",
  milestone: "Milestones",
};

export function BadgeCollection() {
  const { allBadges, isLoading, fetchAllBadges } = useAnalyticsStore();
  const [selectedCategory, setSelectedCategory] = React.useState<string>("");

  React.useEffect(() => {
    fetchAllBadges();
  }, [fetchAllBadges]);

  const earnedCount = allBadges.filter((b) => b.earned).length;
  const totalCount = allBadges.length;

  const categories = React.useMemo(() => {
    const cats = new Set(allBadges.map((b) => b.category));
    return Array.from(cats);
  }, [allBadges]);

  // Set default category when badges load
  React.useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0]);
    }
  }, [categories, selectedCategory]);

  const getBadgesByCategory = (category: string) => {
    return allBadges.filter((b) => b.category === category);
  };

  if (isLoading && allBadges.length === 0) {
    return <BadgeCollectionSkeleton />;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Badge Collection</CardTitle>
            <CardDescription>Your achievements and milestones</CardDescription>
          </div>
          <Badge variant="secondary" className="text-lg px-3 py-1">
            {earnedCount} / {totalCount}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {categories.length > 0 && selectedCategory ? (
          <Tabs value={selectedCategory} onValueChange={setSelectedCategory} className="w-full">
            <TabsList className="w-full flex-wrap h-auto gap-1 mb-4">
              {categories.map((category) => {
                const badges = getBadgesByCategory(category);
                const earned = badges.filter((b) => b.earned).length;
                return (
                  <TabsTrigger
                    key={category}
                    value={category}
                    className="flex-1 min-w-fit"
                  >
                    {CATEGORY_LABELS[category] || category}
                    <span className="ml-1 text-xs text-muted-foreground">
                      ({earned}/{badges.length})
                    </span>
                  </TabsTrigger>
                );
              })}
            </TabsList>
            {categories.map((category) => (
              <TabsContent key={category} value={category}>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {getBadgesByCategory(category).map((badge) => (
                    <BadgeItem key={badge.badge_type} badge={badge} />
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            No badges available yet. Start using LifePilot to earn badges!
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BadgeItem({ badge }: { badge: BadgeDefinition }) {
  const IconComponent = BADGE_ICONS[badge.icon] || Award;

  return (
    <div
      className={`relative p-4 rounded-lg border text-center transition-all ${
        badge.earned
          ? "bg-card hover:shadow-md"
          : "bg-muted/50 opacity-60"
      }`}
    >
      {!badge.earned && (
        <div className="absolute top-2 right-2">
          <Lock className="h-4 w-4 text-muted-foreground" />
        </div>
      )}
      <div
        className={`mx-auto w-12 h-12 rounded-full flex items-center justify-center mb-2 ${
          badge.earned
            ? "bg-primary/10 text-primary"
            : "bg-muted text-muted-foreground"
        }`}
      >
        <IconComponent className="h-6 w-6" />
      </div>
      <h4 className="font-medium text-sm truncate">{badge.name}</h4>
      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
        {badge.description}
      </p>
      {badge.earned && badge.earned_at && (
        <p className="text-xs text-primary mt-2">
          Earned {new Date(badge.earned_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}

function BadgeCollectionSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48 mt-2" />
          </div>
          <Skeleton className="h-8 w-16" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-10 w-full mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
            <div key={i} className="p-4 rounded-lg border">
              <Skeleton className="w-12 h-12 rounded-full mx-auto mb-2" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-full mt-1" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
