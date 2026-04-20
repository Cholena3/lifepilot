"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useHealthStore } from "@/store/health-store";
import { VITAL_TYPES } from "@/lib/api/health";

const vitalSchema = z.object({
  vital_type: z.string().min(1, "Vital type is required"),
  value: z.number().positive("Value must be positive"),
  recorded_at: z.string().optional(),
  notes: z.string().optional(),
});

type VitalFormData = z.infer<typeof vitalSchema>;

interface VitalFormProps {
  onSuccess?: () => void;
}

export function VitalForm({ onSuccess }: VitalFormProps) {
  const { isSubmitting, createVital, setSelectedVitalType } = useHealthStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<VitalFormData>({
    resolver: zodResolver(vitalSchema),
  });

  const selectedType = watch("vital_type");
  const selectedVitalInfo = VITAL_TYPES.find((v) => v.value === selectedType);

  const onSubmit = async (data: VitalFormData) => {
    try {
      await createVital({
        vital_type: data.vital_type,
        value: data.value,
        unit: selectedVitalInfo?.unit || "",
        recorded_at: data.recorded_at || undefined,
        notes: data.notes || undefined,
      });
      
      // Update the selected vital type to refresh the list
      setSelectedVitalType(data.vital_type);
      
      reset();
      onSuccess?.();
    } catch (error) {
      // Error is handled by the store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Record Vital</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Vital Type */}
          <div className="space-y-2">
            <Label>Vital Type *</Label>
            <Select
              value={selectedType}
              onValueChange={(value) => setValue("vital_type", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select vital type" />
              </SelectTrigger>
              <SelectContent>
                {VITAL_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.vital_type && (
              <p className="text-sm text-destructive">{errors.vital_type.message}</p>
            )}
          </div>

          {/* Value */}
          <div className="space-y-2">
            <Label htmlFor="value">
              Value {selectedVitalInfo && `(${selectedVitalInfo.unit})`} *
            </Label>
            <Input
              id="value"
              type="number"
              step="0.1"
              placeholder={selectedVitalInfo ? `e.g., 120` : "Enter value"}
              {...register("value", { valueAsNumber: true })}
            />
            {errors.value && (
              <p className="text-sm text-destructive">{errors.value.message}</p>
            )}
          </div>

          {/* Recorded At */}
          <div className="space-y-2">
            <Label htmlFor="recorded_at">Date & Time (optional)</Label>
            <Input
              id="recorded_at"
              type="datetime-local"
              {...register("recorded_at")}
            />
            <p className="text-xs text-muted-foreground">
              Leave empty to use current time
            </p>
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="Any additional notes..."
              {...register("notes")}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Recording..." : "Record Vital"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
