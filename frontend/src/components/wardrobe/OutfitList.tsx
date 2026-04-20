"use client";

import { useEffect } from "react";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { Outfit } from "@/lib/api/wardrobe";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Trash2, Calendar, Shirt } from "lucide-react";

interface OutfitListProps {
  onPlanOutfit?: (outfit: Outfit) => void;
}

export function OutfitList({ onPlanOutfit }: OutfitListProps) {
  const { outfits, outfitsLoading, outfitsError, fetchOutfits, deleteOutfit } = useWardrobeStore();

  useEffect(() => {
    fetchOutfits();
  }, [fetchOutfits]);

  const handleDelete = async (outfitId: string) => {
    if (confirm("Are you sure you want to delete this outfit?")) {
      await deleteOutfit(outfitId);
    }
  };

  if (outfitsLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    );
  }

  if (outfitsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading outfits: {outfitsError}</p>
      </div>
    );
  }

  if (outfits.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Shirt className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No saved outfits yet.</p>
        <p className="text-sm mt-1">Create an outfit from your wardrobe items!</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {outfits.map((outfit) => (
        <Card key={outfit.id}>
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg">{outfit.name}</CardTitle>
                {outfit.occasion && (
                  <Badge variant="secondary" className="mt-1">
                    {outfit.occasion}
                  </Badge>
                )}
              </div>
              <div className="flex gap-2">
                {onPlanOutfit && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onPlanOutfit(outfit)}
                  >
                    <Calendar className="h-4 w-4 mr-1" />
                    Plan
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-destructive"
                  onClick={() => handleDelete(outfit.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {outfit.items.map((item) => (
                <div
                  key={item.id}
                  className="flex-shrink-0 w-16 h-16 bg-muted rounded-lg overflow-hidden"
                >
                  {item.wardrobe_item?.image_url ? (
                    <img
                      src={item.wardrobe_item.processed_image_url || item.wardrobe_item.image_url}
                      alt={item.wardrobe_item.name || "Item"}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Shirt className="h-6 w-6 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}
            </div>
            {outfit.notes && (
              <p className="text-sm text-muted-foreground mt-2">{outfit.notes}</p>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
