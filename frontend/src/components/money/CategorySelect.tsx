"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMoneyStore } from "@/store/money-store";

interface CategorySelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
}

const DEFAULT_COLORS = [
  "#ef4444", // red
  "#f97316", // orange
  "#eab308", // yellow
  "#22c55e", // green
  "#06b6d4", // cyan
  "#3b82f6", // blue
  "#8b5cf6", // violet
  "#ec4899", // pink
];

const DEFAULT_ICONS = ["🍔", "🚗", "🏠", "💊", "🎬", "🛒", "✈️", "📚", "💼", "🎁"];

export function CategorySelect({ value, onChange, error }: CategorySelectProps) {
  const { categories, fetchCategories, createCategory, isSubmitting } =
    useMoneyStore();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [newCategoryName, setNewCategoryName] = React.useState("");
  const [newCategoryIcon, setNewCategoryIcon] = React.useState("🏷️");
  const [newCategoryColor, setNewCategoryColor] = React.useState(DEFAULT_COLORS[0]);

  React.useEffect(() => {
    if (categories.length === 0) {
      fetchCategories();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) return;

    try {
      const category = await createCategory({
        name: newCategoryName.trim(),
        icon: newCategoryIcon,
        color: newCategoryColor,
      });
      onChange(category.id);
      setIsDialogOpen(false);
      setNewCategoryName("");
      setNewCategoryIcon("🏷️");
      setNewCategoryColor(DEFAULT_COLORS[0]);
    } catch {
      // Error handled by store
    }
  };

  return (
    <div className="space-y-2">
      <Label htmlFor="category">Category</Label>
      <div className="flex gap-2">
        <Select
          id="category"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1"
        >
          <option value="">Select a category</option>
          {categories.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.icon} {cat.name}
            </option>
          ))}
        </Select>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button type="button" variant="outline" size="icon">
              +
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Category</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="categoryName">Category Name</Label>
                <Input
                  id="categoryName"
                  value={newCategoryName}
                  onChange={(e) => setNewCategoryName(e.target.value)}
                  placeholder="e.g., Groceries"
                />
              </div>

              <div className="space-y-2">
                <Label>Icon</Label>
                <div className="flex flex-wrap gap-2">
                  {DEFAULT_ICONS.map((icon) => (
                    <Button
                      key={icon}
                      type="button"
                      variant={newCategoryIcon === icon ? "default" : "outline"}
                      size="icon"
                      onClick={() => setNewCategoryIcon(icon)}
                    >
                      {icon}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label>Color</Label>
                <div className="flex flex-wrap gap-2">
                  {DEFAULT_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      className={`w-8 h-8 rounded-full border-2 ${
                        newCategoryColor === color
                          ? "border-foreground"
                          : "border-transparent"
                      }`}
                      style={{ backgroundColor: color }}
                      onClick={() => setNewCategoryColor(color)}
                    />
                  ))}
                </div>
              </div>

              <Button
                onClick={handleCreateCategory}
                disabled={!newCategoryName.trim() || isSubmitting}
                className="w-full"
              >
                {isSubmitting ? "Creating..." : "Create Category"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
