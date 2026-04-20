"use client";

import { useEffect, useState } from "react";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { PackingList } from "@/lib/api/wardrobe";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Luggage, Trash2, Plus, MapPin, Calendar, Shirt } from "lucide-react";

interface PackingListViewProps {
  onCreateNew?: () => void;
}

export function PackingListView({ onCreateNew }: PackingListViewProps) {
  const {
    packingLists,
    packingListsLoading,
    packingListsError,
    fetchPackingLists,
    deletePackingList,
    toggleItemPacked,
  } = useWardrobeStore();

  const [expandedList, setExpandedList] = useState<string | null>(null);

  useEffect(() => {
    fetchPackingLists(false); // Fetch non-template lists
  }, [fetchPackingLists]);

  const handleDelete = async (listId: string) => {
    if (confirm("Are you sure you want to delete this packing list?")) {
      await deletePackingList(listId);
    }
  };

  const handleTogglePacked = async (listId: string, itemId: string, currentStatus: boolean) => {
    await toggleItemPacked(listId, itemId, !currentStatus);
  };

  const getPackedProgress = (list: PackingList) => {
    if (list.items.length === 0) return 0;
    const packed = list.items.filter((item) => item.is_packed).length;
    return Math.round((packed / list.items.length) * 100);
  };

  if (packingListsLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-full" />
        ))}
      </div>
    );
  }

  if (packingListsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading packing lists: {packingListsError}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Luggage className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Packing Lists</h3>
        </div>
        {onCreateNew && (
          <Button variant="outline" size="sm" onClick={onCreateNew}>
            <Plus className="h-4 w-4 mr-1" />
            New List
          </Button>
        )}
      </div>

      {packingLists.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Luggage className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No packing lists yet.</p>
            <p className="text-sm mt-1">Create a list for your next trip!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {packingLists.map((list) => (
            <Card key={list.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() =>
                      setExpandedList(expandedList === list.id ? null : list.id)
                    }
                  >
                    <CardTitle className="text-lg">{list.name}</CardTitle>
                    <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                      {list.destination && (
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {list.destination}
                        </span>
                      )}
                      {list.trip_start && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {new Date(list.trip_start).toLocaleDateString()}
                          {list.trip_end &&
                            ` - ${new Date(list.trip_end).toLocaleDateString()}`}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={getPackedProgress(list) === 100 ? "default" : "secondary"}>
                      {getPackedProgress(list)}% packed
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive"
                      onClick={() => handleDelete(list.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>

              {expandedList === list.id && (
                <CardContent>
                  {list.items.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No items in this list.</p>
                  ) : (
                    <div className="space-y-2">
                      {list.items.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted"
                        >
                          <Checkbox
                            checked={item.is_packed}
                            onCheckedChange={() =>
                              handleTogglePacked(list.id, item.id, item.is_packed)
                            }
                          />
                          {item.wardrobe_item ? (
                            <>
                              <div className="w-10 h-10 bg-muted rounded overflow-hidden flex-shrink-0">
                                {item.wardrobe_item.image_url ? (
                                  <img
                                    src={
                                      item.wardrobe_item.processed_image_url ||
                                      item.wardrobe_item.image_url
                                    }
                                    alt={item.wardrobe_item.name || "Item"}
                                    className="w-full h-full object-cover"
                                  />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center">
                                    <Shirt className="h-4 w-4 text-muted-foreground" />
                                  </div>
                                )}
                              </div>
                              <span
                                className={
                                  item.is_packed ? "line-through text-muted-foreground" : ""
                                }
                              >
                                {item.wardrobe_item.name || item.wardrobe_item.item_type}
                              </span>
                            </>
                          ) : (
                            <span
                              className={
                                item.is_packed ? "line-through text-muted-foreground" : ""
                              }
                            >
                              {item.custom_item_name || "Unknown item"}
                            </span>
                          )}
                          {item.quantity > 1 && (
                            <Badge variant="outline" className="ml-auto">
                              x{item.quantity}
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
