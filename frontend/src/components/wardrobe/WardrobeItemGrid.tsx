"use client";

import { useEffect } from "react";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { WardrobeItemCard } from "./WardrobeItemCard";
import { WardrobeItem } from "@/lib/api/wardrobe";
import { Skeleton } from "@/components/ui/skeleton";

interface WardrobeItemGridProps {
  onEdit?: (item: WardrobeItem) => void;
  onSelect?: (item: WardrobeItem) => void;
  selectedIds?: string[];
  selectable?: boolean;
}

export function WardrobeItemGrid({
  onEdit,
  onSelect,
  selectedIds = [],
  selectable = false,
}: WardrobeItemGridProps) {
  const { items, itemsLoading, itemsError, fetchItems } = useWardrobeStore();

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  if (itemsLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="aspect-square rounded-lg" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    );
  }

  if (itemsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading wardrobe items: {itemsError}</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <p>No items in your wardrobe yet.</p>
        <p className="text-sm mt-1">Add your first item to get started!</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {items.map((item) => (
        <WardrobeItemCard
          key={item.id}
          item={item}
          onEdit={onEdit}
          onSelect={selectable ? onSelect : undefined}
          selected={selectedIds.includes(item.id)}
        />
      ))}
    </div>
  );
}
