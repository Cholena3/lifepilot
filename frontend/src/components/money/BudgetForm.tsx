"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CategorySelect } from "./CategorySelect";
import { useMoneyStore } from "@/store/money-store";
import { cn } from "@/lib/utils";

const budgetSchema = z.object({
  category_id: z.string().min(1, "Category is required"),
  amount: z.number().positive("Amount must be positive"),
  period: z.enum(["weekly", "monthly"]),
});

type BudgetFormData = z.infer<typeof budgetSchema>;

interface BudgetFormProps {
  onSuccess?: () => void;
  editBudget?: {
    id: string;
    category_id: string;
    amount: number;
    period: "weekly" | "monthly";
  };
}

export function BudgetForm({ onSuccess, editBudget }: BudgetFormProps) {
  const { createBudget, updateBudget, isSubmitting, error } = useMoneyStore();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<BudgetFormData>({
    resolver: zodResolver(budgetSchema),
    defaultValues: editBudget
      ? {
          category_id: editBudget.category_id,
          amount: editBudget.amount,
          period: editBudget.period,
        }
      : {
          category_id: "",
          amount: 0,
          period: "monthly",
        },
  });

  const categoryId = watch("category_id");

  const onSubmit = async (data: BudgetFormData) => {
    try {
      if (editBudget) {
        await updateBudget(editBudget.id, {
          amount: data.amount,
          period: data.period,
        });
      } else {
        await createBudget(data);
      }
      reset();
      onSuccess?.();
    } catch {
      // Error handled by store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{editBudget ? "Edit Budget" : "Create Budget"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Category */}
          {!editBudget && (
            <CategorySelect
              value={categoryId}
              onChange={(value) => setValue("category_id", value)}
              error={errors.category_id?.message}
            />
          )}

          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Budget Amount (₹)</Label>
            <Input
              id="amount"
              type="number"
              step="0.01"
              placeholder="0.00"
              {...register("amount", { valueAsNumber: true })}
              className={cn(errors.amount && "border-destructive")}
            />
            {errors.amount && (
              <p className="text-sm text-destructive">{errors.amount.message}</p>
            )}
          </div>

          {/* Period */}
          <div className="space-y-2">
            <Label htmlFor="period">Budget Period</Label>
            <Select id="period" {...register("period")}>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </Select>
            {errors.period && (
              <p className="text-sm text-destructive">{errors.period.message}</p>
            )}
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting
              ? editBudget
                ? "Updating..."
                : "Creating..."
              : editBudget
                ? "Update Budget"
                : "Create Budget"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
