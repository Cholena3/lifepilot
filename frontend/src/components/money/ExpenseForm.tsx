"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CategorySelect } from "./CategorySelect";
import { useMoneyStore } from "@/store/money-store";
import { moneyApi, type ReceiptData } from "@/lib/api/money";
import { cn } from "@/lib/utils";

const expenseSchema = z.object({
  category_id: z.string().min(1, "Category is required"),
  amount: z.number().positive("Amount must be positive"),
  description: z.string().min(1, "Description is required"),
  expense_date: z.string().min(1, "Date is required"),
});

type ExpenseFormData = z.infer<typeof expenseSchema>;

interface ExpenseFormProps {
  onSuccess?: () => void;
  editExpense?: {
    id: string;
    category_id: string;
    amount: number;
    description: string;
    expense_date: string;
  };
}

export function ExpenseForm({ onSuccess, editExpense }: ExpenseFormProps) {
  const { createExpense, updateExpense, isSubmitting, error } = useMoneyStore();
  const [isProcessingReceipt, setIsProcessingReceipt] = React.useState(false);
  const [receiptPreview, setReceiptPreview] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<ExpenseFormData>({
    resolver: zodResolver(expenseSchema),
    defaultValues: editExpense
      ? {
          category_id: editExpense.category_id,
          amount: editExpense.amount,
          description: editExpense.description,
          expense_date: editExpense.expense_date.split("T")[0],
        }
      : {
          category_id: "",
          amount: 0,
          description: "",
          expense_date: new Date().toISOString().split("T")[0],
        },
  });

  const categoryId = watch("category_id");

  const handleReceiptChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setReceiptPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Process receipt with OCR
    setIsProcessingReceipt(true);
    try {
      const receiptData: ReceiptData = await moneyApi.processReceipt(file);
      if (receiptData.amount) {
        setValue("amount", receiptData.amount);
      }
      if (receiptData.merchant_name) {
        setValue("description", receiptData.merchant_name);
      }
      if (receiptData.date) {
        setValue("expense_date", receiptData.date);
      }
    } catch (err) {
      console.error("Failed to process receipt:", err);
    } finally {
      setIsProcessingReceipt(false);
    }
  };

  const onSubmit = async (data: ExpenseFormData) => {
    try {
      if (editExpense) {
        await updateExpense(editExpense.id, data);
      } else {
        await createExpense(data);
      }
      reset();
      setReceiptPreview(null);
      onSuccess?.();
    } catch {
      // Error handled by store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{editExpense ? "Edit Expense" : "Log Expense"}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Receipt Upload */}
          <div className="space-y-2">
            <Label htmlFor="receipt">Receipt (Optional)</Label>
            <Input
              id="receipt"
              type="file"
              accept="image/*"
              onChange={handleReceiptChange}
              className="cursor-pointer"
            />
            {isProcessingReceipt && (
              <p className="text-sm text-muted-foreground">
                Processing receipt...
              </p>
            )}
            {receiptPreview && (
              <div className="mt-2">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={receiptPreview}
                  alt="Receipt preview"
                  className="max-h-32 rounded-md"
                />
              </div>
            )}
          </div>

          {/* Category */}
          <CategorySelect
            value={categoryId}
            onChange={(value) => setValue("category_id", value)}
            error={errors.category_id?.message}
          />

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
            {isSubmitting
              ? editExpense
                ? "Updating..."
                : "Logging..."
              : editExpense
                ? "Update Expense"
                : "Log Expense"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
