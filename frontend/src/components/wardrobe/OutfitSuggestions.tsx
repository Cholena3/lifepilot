"use client";

import { useEffect } from "react";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { OCCASIONS } from "@/lib/api/wardrobe";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sparkles, Shirt, Save, ThermometerSun } from "lucide-react";
import { useState } from "react";

export function OutfitSuggestions() {
  const { suggestions, suggestionsLoading, fetchSuggestions, createOutfit } = useWardrobeStore();
  const [selectedOccasion, setSelectedOccasion] = useState<string>("");
  const [savingIndex, setSavingIndex] = useState<number | null>(null);

  useEffect(() => {
    fetchSuggestions(selectedOccasion || undefined);
  }, [fetchSuggestions, selectedOccasion]);

  const handleSaveOutfit = async (index: number) => {
    const suggestion = suggestions[index];
    if (!suggestion) return;

    setSavingIndex(index);
    try {
      await createOutfit({
        name: `Suggested Outfit ${new Date().toLocaleDateString()}`,
        occasion: suggestion.occasion || undefined,
        item_ids: suggestion.items.map((item) => item.id),
      });
      alert("Outfit saved!");
    } catch (error) {
      console.error("Failed to save outfit:", error);
      alert("Failed to save outfit");
    } finally {
      setSavingIndex(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Outfit Suggestions</h3>
        </div>
        <Select value={selectedOccasion} onValueChange={setSelectedOccasion}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Any occasion" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Any occasion</SelectItem>
            {OCCASIONS.map((occasion) => (
              <SelectItem key={occasion.value} value={occasion.value}>
                {occasion.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {suggestionsLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : suggestions.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Shirt className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No suggestions available.</p>
            <p className="text-sm mt-1">Add more items to your wardrobe to get suggestions!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {suggestions.map((suggestion, index) => (
            <Card key={index}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-base">Suggestion {index + 1}</CardTitle>
                    <Badge variant="outline">Score: {suggestion.score.toFixed(0)}</Badge>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleSaveOutfit(index)}
                    disabled={savingIndex === index}
                  >
                    <Save className="h-4 w-4 mr-1" />
                    {savingIndex === index ? "Saving..." : "Save"}
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {suggestion.weather && (
                  <div className="flex items-center gap-2 mb-3 text-sm text-muted-foreground">
                    <ThermometerSun className="h-4 w-4" />
                    <span>
                      {suggestion.weather.temperature}°C - {suggestion.weather.condition}
                    </span>
                  </div>
                )}
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {suggestion.items.map((item) => (
                    <div key={item.id} className="flex-shrink-0">
                      <div className="w-20 h-20 bg-muted rounded-lg overflow-hidden">
                        {item.image_url ? (
                          <img
                            src={item.processed_image_url || item.image_url}
                            alt={item.name || item.item_type}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Shirt className="h-8 w-8 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-center mt-1 truncate w-20">
                        {item.name || item.item_type}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
