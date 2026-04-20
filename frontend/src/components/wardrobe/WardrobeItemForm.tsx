"use client";

import { useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useWardrobeStore } from "@/store/wardrobe-store";
import { CLOTHING_TYPES, CLOTHING_PATTERNS, OCCASIONS, COLORS } from "@/lib/api/wardrobe";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Camera, Upload, X } from "lucide-react";

const formSchema = z.object({
  item_type: z.string().min(1, "Item type is required"),
  name: z.string().optional(),
  primary_color: z.string().optional(),
  pattern: z.string().optional(),
  brand: z.string().optional(),
  price: z.number().min(0).optional(),
  purchase_date: z.string().optional(),
  occasions: z.array(z.string()).optional(),
  notes: z.string().optional(),
});

type FormData = z.infer<typeof formSchema>;

interface WardrobeItemFormProps {
  open: boolean;
  onClose: () => void;
}

export function WardrobeItemForm({ open, onClose }: WardrobeItemFormProps) {
  const { createItem, fetchItems } = useWardrobeStore();
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedOccasions, setSelectedOccasions] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      item_type: "",
      occasions: [],
    },
  });

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleOccasionToggle = (occasion: string) => {
    setSelectedOccasions((prev) =>
      prev.includes(occasion)
        ? prev.filter((o) => o !== occasion)
        : [...prev, occasion]
    );
  };

  const onSubmit = async (data: FormData) => {
    if (!imageFile) {
      alert("Please select an image");
      return;
    }

    setIsSubmitting(true);
    try {
      await createItem(imageFile, {
        ...data,
        occasions: selectedOccasions,
        price: data.price ? Number(data.price) : undefined,
      });
      await fetchItems();
      handleClose();
    } catch (error) {
      console.error("Failed to create item:", error);
      alert("Failed to create item. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    reset();
    setImageFile(null);
    setImagePreview(null);
    setSelectedOccasions([]);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add New Item</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Image Upload */}
          <div className="space-y-2">
            <Label>Photo</Label>
            <div className="flex gap-2">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                ref={fileInputRef}
                className="hidden"
              />
              {imagePreview ? (
                <div className="relative w-32 h-32">
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="w-full h-full object-cover rounded-lg"
                  />
                  <Button
                    type="button"
                    variant="destructive"
                    size="icon"
                    className="absolute -top-2 -right-2 h-6 w-6"
                    onClick={() => {
                      setImageFile(null);
                      setImagePreview(null);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Upload
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      // TODO: Implement camera capture
                      fileInputRef.current?.click();
                    }}
                  >
                    <Camera className="h-4 w-4 mr-2" />
                    Camera
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Item Type */}
          <div className="space-y-2">
            <Label htmlFor="item_type">Type *</Label>
            <Select
              onValueChange={(value) => setValue("item_type", value)}
              defaultValue={watch("item_type")}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {CLOTHING_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.item_type && (
              <p className="text-sm text-destructive">{errors.item_type.message}</p>
            )}
          </div>

          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input {...register("name")} placeholder="e.g., Blue Oxford Shirt" />
          </div>

          {/* Color and Pattern */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Color</Label>
              <Select onValueChange={(value) => setValue("primary_color", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select color" />
                </SelectTrigger>
                <SelectContent>
                  {COLORS.map((color) => (
                    <SelectItem key={color.value} value={color.value}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded-full border"
                          style={{ backgroundColor: color.value }}
                        />
                        {color.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Pattern</Label>
              <Select onValueChange={(value) => setValue("pattern", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select pattern" />
                </SelectTrigger>
                <SelectContent>
                  {CLOTHING_PATTERNS.map((pattern) => (
                    <SelectItem key={pattern.value} value={pattern.value}>
                      {pattern.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Brand and Price */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="brand">Brand</Label>
              <Input {...register("brand")} placeholder="e.g., Nike" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="price">Price</Label>
              <Input
                type="number"
                step="0.01"
                {...register("price", { valueAsNumber: true })}
                placeholder="0.00"
              />
            </div>
          </div>

          {/* Purchase Date */}
          <div className="space-y-2">
            <Label htmlFor="purchase_date">Purchase Date</Label>
            <Input type="date" {...register("purchase_date")} />
          </div>

          {/* Occasions */}
          <div className="space-y-2">
            <Label>Occasions</Label>
            <div className="flex flex-wrap gap-2">
              {OCCASIONS.map((occasion) => (
                <Button
                  key={occasion.value}
                  type="button"
                  variant={selectedOccasions.includes(occasion.value) ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleOccasionToggle(occasion.value)}
                >
                  {occasion.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea {...register("notes")} placeholder="Any additional notes..." />
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={handleClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !imageFile}>
              {isSubmitting ? "Adding..." : "Add Item"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
