"use client";

import { useState } from "react";
import Image from "next/image";
import { WardrobeItem } from "@/lib/api/wardrobe";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreVertical, Shirt, Trash2, Edit, WashingMachine, Check } from "lucide-react";

interface WardrobeItemCardProps {
  item: WardrobeItem;
  onEdit?: (item: WardrobeItem) => void;
  onSelect?: (item: WardrobeItem) => void;
  selected?: boolean;
}

export function WardrobeItemCard({ item, onEdit, onSelect, selected }: WardrobeItemCardProps) {
  const { deleteItem, setLaundryStatus, markWorn } = useWardrobeStore();
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this item?")) {
      setIsDeleting(true);
      try {
        await deleteItem(item.id);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const handleLaundryToggle = async () => {
    await setLaundryStatus(item.id, !item.in_laundry);
  };

  const handleMarkWorn = async () => {
    const today = new Date().toISOString().split("T")[0];
    await markWorn(item.id, today);
  };

  return (
    <Card
      className={`overflow-hidden cursor-pointer transition-all ${
        selected ? "ring-2 ring-primary" : "hover:shadow-md"
      } ${item.in_laundry ? "opacity-60" : ""}`}
      onClick={() => onSelect?.(item)}
    >
      <div className="relative aspect-square bg-muted">
        {item.image_url ? (
          <Image
            src={item.processed_image_url || item.image_url}
            alt={item.name || item.item_type}
            fill
            className="object-cover"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Shirt className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
        {item.in_laundry && (
          <Badge variant="secondary" className="absolute top-2 left-2">
            <WashingMachine className="h-3 w-3 mr-1" />
            In Laundry
          </Badge>
        )}
        {selected && (
          <div className="absolute top-2 right-2 bg-primary text-primary-foreground rounded-full p-1">
            <Check className="h-4 w-4" />
          </div>
        )}
      </div>
      <CardContent className="p-3">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{item.name || item.item_type}</p>
            <div className="flex items-center gap-2 mt-1">
              {item.primary_color && (
                <div
                  className="w-4 h-4 rounded-full border"
                  style={{ backgroundColor: item.primary_color }}
                  title={item.primary_color}
                />
              )}
              <span className="text-sm text-muted-foreground capitalize">
                {item.item_type.replace("_", " ")}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Worn {item.wear_count} times
            </p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit?.(item)}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleMarkWorn}>
                <Check className="h-4 w-4 mr-2" />
                Mark as Worn
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleLaundryToggle}>
                <WashingMachine className="h-4 w-4 mr-2" />
                {item.in_laundry ? "Remove from Laundry" : "Add to Laundry"}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleDelete}
                disabled={isDeleting}
                className="text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
}
