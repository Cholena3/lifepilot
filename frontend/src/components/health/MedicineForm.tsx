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
import { Plus, X } from "lucide-react";

const medicineSchema = z.object({
  name: z.string().min(1, "Medicine name is required"),
  dosage: z.string().min(1, "Dosage is required"),
  frequency: z.string().min(1, "Frequency is required"),
  times_per_day: z.number().min(1).max(10),
  start_date: z.string().min(1, "Start date is required"),
  end_date: z.string().optional(),
  current_stock: z.number().min(0).optional(),
  refill_threshold: z.number().min(0).optional(),
  instructions: z.string().optional(),
});

type MedicineFormData = z.infer<typeof medicineSchema>;

interface MedicineFormProps {
  onSuccess?: () => void;
}

const FREQUENCY_OPTIONS = [
  { value: "daily", label: "Daily" },
  { value: "twice_daily", label: "Twice Daily" },
  { value: "three_times_daily", label: "Three Times Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "as_needed", label: "As Needed" },
];

export function MedicineForm({ onSuccess }: MedicineFormProps) {
  const { isSubmitting, createMedicine } = useHealthStore();
  const [reminderTimes, setReminderTimes] = React.useState<string[]>(["08:00"]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<MedicineFormData>({
    resolver: zodResolver(medicineSchema),
    defaultValues: {
      times_per_day: 1,
      current_stock: 30,
      refill_threshold: 5,
    },
  });

  const timesPerDay = watch("times_per_day");

  React.useEffect(() => {
    // Adjust reminder times array when times_per_day changes
    if (timesPerDay > reminderTimes.length) {
      const newTimes = [...reminderTimes];
      while (newTimes.length < timesPerDay) {
        const lastTime = newTimes[newTimes.length - 1] || "08:00";
        const [hours] = lastTime.split(":");
        const newHour = (parseInt(hours) + 6) % 24;
        newTimes.push(`${newHour.toString().padStart(2, "0")}:00`);
      }
      setReminderTimes(newTimes);
    } else if (timesPerDay < reminderTimes.length) {
      setReminderTimes(reminderTimes.slice(0, timesPerDay));
    }
  }, [timesPerDay, reminderTimes]);

  const handleTimeChange = (index: number, value: string) => {
    const newTimes = [...reminderTimes];
    newTimes[index] = value;
    setReminderTimes(newTimes);
  };

  const onSubmit = async (data: MedicineFormData) => {
    try {
      await createMedicine({
        ...data,
        reminder_times: reminderTimes,
        current_stock: data.current_stock || 30,
        refill_threshold: data.refill_threshold || 5,
      });
      reset();
      setReminderTimes(["08:00"]);
      onSuccess?.();
    } catch (error) {
      // Error is handled by the store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add Medicine</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Medicine Name */}
          <div className="space-y-2">
            <Label htmlFor="name">Medicine Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Metformin"
              {...register("name")}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Dosage */}
          <div className="space-y-2">
            <Label htmlFor="dosage">Dosage *</Label>
            <Input
              id="dosage"
              placeholder="e.g., 500mg"
              {...register("dosage")}
            />
            {errors.dosage && (
              <p className="text-sm text-destructive">{errors.dosage.message}</p>
            )}
          </div>

          {/* Frequency */}
          <div className="space-y-2">
            <Label>Frequency *</Label>
            <Select
              value={watch("frequency")}
              onValueChange={(value) => setValue("frequency", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select frequency" />
              </SelectTrigger>
              <SelectContent>
                {FREQUENCY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.frequency && (
              <p className="text-sm text-destructive">{errors.frequency.message}</p>
            )}
          </div>

          {/* Times Per Day */}
          <div className="space-y-2">
            <Label htmlFor="times_per_day">Times Per Day</Label>
            <Input
              id="times_per_day"
              type="number"
              min={1}
              max={10}
              {...register("times_per_day", { valueAsNumber: true })}
            />
          </div>

          {/* Reminder Times */}
          <div className="space-y-2">
            <Label>Reminder Times</Label>
            <div className="space-y-2">
              {reminderTimes.map((time, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    type="time"
                    value={time}
                    onChange={(e) => handleTimeChange(index, e.target.value)}
                    className="flex-1"
                  />
                  <span className="text-sm text-muted-foreground">
                    Dose {index + 1}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Start Date */}
          <div className="space-y-2">
            <Label htmlFor="start_date">Start Date *</Label>
            <Input id="start_date" type="date" {...register("start_date")} />
            {errors.start_date && (
              <p className="text-sm text-destructive">{errors.start_date.message}</p>
            )}
          </div>

          {/* End Date */}
          <div className="space-y-2">
            <Label htmlFor="end_date">End Date (optional)</Label>
            <Input id="end_date" type="date" {...register("end_date")} />
          </div>

          {/* Stock Management */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="current_stock">Current Stock</Label>
              <Input
                id="current_stock"
                type="number"
                min={0}
                {...register("current_stock", { valueAsNumber: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="refill_threshold">Refill Threshold</Label>
              <Input
                id="refill_threshold"
                type="number"
                min={0}
                {...register("refill_threshold", { valueAsNumber: true })}
              />
            </div>
          </div>

          {/* Instructions */}
          <div className="space-y-2">
            <Label htmlFor="instructions">Instructions</Label>
            <Textarea
              id="instructions"
              placeholder="e.g., Take with food"
              {...register("instructions")}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Adding..." : "Add Medicine"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
