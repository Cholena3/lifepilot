"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Shirt, Sparkles, Calendar, BarChart3, Luggage } from "lucide-react";
import {
  WardrobeItemGrid,
  WardrobeItemForm,
  OutfitList,
  OutfitSuggestions,
  WardrobeStats,
  PackingListView,
} from "@/components/wardrobe";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { CLOTHING_TYPES, OCCASIONS, WardrobeItem } from "@/lib/api/wardrobe";

export default function WardrobePage() {
  const [showAddForm, setShowAddForm] = useState(false);
  const [activeTab, setActiveTab] = useState("items");
  const { setFilters, fetchItems, filters } = useWardrobeStore();

  const handleFilterChange = (key: string, value: string | undefined) => {
    const newFilters = { ...filters, [key]: value || undefined };
    setFilters(newFilters);
    fetchItems(newFilters);
  };

  const handleEditItem = (item: WardrobeItem) => {
    // TODO: Implement edit functionality
    console.log("Edit item:", item);
  };

  return (
    <div className="container mx-auto py-6 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Wardrobe</h1>
          <p className="text-muted-foreground">Manage your clothing and plan outfits</p>
        </div>
        <Button onClick={() => setShowAddForm(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Item
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="items" className="flex items-center gap-2">
            <Shirt className="h-4 w-4" />
            Items
          </TabsTrigger>
          <TabsTrigger value="suggestions" className="flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Suggestions
          </TabsTrigger>
          <TabsTrigger value="outfits" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Outfits
          </TabsTrigger>
          <TabsTrigger value="stats" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Statistics
          </TabsTrigger>
          <TabsTrigger value="packing" className="flex items-center gap-2">
            <Luggage className="h-4 w-4" />
            Packing
          </TabsTrigger>
        </TabsList>

        <TabsContent value="items">
          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <Select
              value={filters.item_type || ""}
              onValueChange={(value) => handleFilterChange("item_type", value)}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All types</SelectItem>
                {CLOTHING_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.occasion || ""}
              onValueChange={(value) => handleFilterChange("occasion", value)}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All occasions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All occasions</SelectItem>
                {OCCASIONS.map((occasion) => (
                  <SelectItem key={occasion.value} value={occasion.value}>
                    {occasion.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={filters.in_laundry === undefined ? "" : String(filters.in_laundry)}
              onValueChange={(value) =>
                handleFilterChange(
                  "in_laundry",
                  value === "" ? undefined : value === "true" ? "true" : "false"
                )
              }
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All items" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All items</SelectItem>
                <SelectItem value="false">Available</SelectItem>
                <SelectItem value="true">In laundry</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <WardrobeItemGrid onEdit={handleEditItem} />
        </TabsContent>

        <TabsContent value="suggestions">
          <OutfitSuggestions />
        </TabsContent>

        <TabsContent value="outfits">
          <OutfitList />
        </TabsContent>

        <TabsContent value="stats">
          <WardrobeStats />
        </TabsContent>

        <TabsContent value="packing">
          <PackingListView />
        </TabsContent>
      </Tabs>

      <WardrobeItemForm open={showAddForm} onClose={() => setShowAddForm(false)} />
    </div>
  );
}
