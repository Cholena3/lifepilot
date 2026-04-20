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
import { useMoneyStore } from "@/store/money-store";
import { cn } from "@/lib/utils";

const addExpenseSchema = z.object({
  amount: z.number().positive("Amount must be positive"),
  description: z.string().min(1, "Description is required"),
  split_type: z.enum(["equal", "percentage", "exact"]),
  expense_date: z.string().min(1, "Date is required"),
});

type AddExpenseFormData = z.infer<typeof addExpenseSchema>;

interface AddExpenseFormProps {
  groupId: string;
  onSuccess?: () => void;
}

export function AddExpenseForm({ groupId, onSuccess }: AddExpenseFormProps) {
  const { addGroupExpense, isSubmitting, error } = useMoneyStore();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AddExpenseFormData>({
    resolver: zodResolver(addExpenseSchema),
    defaultValues: {
      amount: 0,
      description: "",
      split_type: "equal",
      expense_date: new Date().toISOString().split("T")[0],
    },
  });

  const onSubmit = async (data: AddExpenseFormData) => {
    try {
      await addGroupExpense(groupId, {
        amount: data.amount,
        description: data.description,
        split_type: data.split_type,
        expense_date: data.expense_date,
      });
      reset();
      onSuccess?.();
    } catch {
      // Error handled by store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add Shared Expense</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Amount */}
          <div className="space-y-2">
            <Label htmlFor="amount">Amount (₹)</Label>
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

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              placeholder="What was this expense for?"
              {...register("description")}
              className={cn(errors.description && "border-destructive")}
            />
            {errors.description && (
              <p className="text-sm text-destructive">
                {errors.description.message}
              </p>
            )}
          </div>

          {/* Split Type */}
          <div className="space-y-2">
            <Label htmlFor="split_type">Split Type</Label>
            <Select id="split_type" {...register("split_type")}>
              <option value="equal">Equal Split</option>
              <option value="percentage">By Percentage</option>
              <option value="exact">Exact Amounts</option>
            </Select>
            <p className="text-xs text-muted-foreground">
              Equal split divides the amount evenly among all members
            </p>
          </div>

          {/* Date */}
          <div className="space-y-2">
            <Label htmlFor="expense_date">Date</Label>
            <Input
              id="expense_date"
              type="date"
              {...register("expense_date")}
              className={cn(errors.expense_date && "border-destructive")}
            />
            {errors.expense_date && (
              <p className="text-sm text-destructive">
                {errors.expense_date.message}
              </p>
            )}
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Adding..." : "Add Expense"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
