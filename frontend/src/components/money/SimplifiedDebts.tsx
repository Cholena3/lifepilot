"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useMoneyStore } from "@/store/money-store";
import type { SimplifiedDebt } from "@/lib/api/money";

interface SimplifiedDebtsProps {
  groupId: string;
  debts: SimplifiedDebt[];
  currentUserId?: string;
}

export function SimplifiedDebts({
  groupId,
  debts,
  currentUserId,
}: SimplifiedDebtsProps) {
  const { settleDebt, isSubmitting } = useMoneyStore();
  const [settlingDebt, setSettlingDebt] = React.useState<SimplifiedDebt | null>(
    null
  );

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(amount);
  };

  const handleSettle = async (debt: SimplifiedDebt) => {
    try {
      await settleDebt(groupId, {
        to_user_id: debt.to_user_id,
        amount: debt.amount,
      });
      setSettlingDebt(null);
    } catch {
      // Error handled by store
    }
  };

  const handleUPIClick = (upiLink: string) => {
    window.open(upiLink, "_blank");
  };

  if (debts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Simplified Debts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">
            <p className="text-green-500 font-medium text-lg">All settled up! 🎉</p>
            <p className="text-muted-foreground text-sm mt-1">
              No outstanding debts in this group.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Simplified Debts</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          These are the minimum transactions needed to settle all debts.
        </p>
        <div className="space-y-3">
          {debts.map((debt, index) => {
            const isCurrentUserOwing = debt.from_user_id === currentUserId;
            const isCurrentUserOwed = debt.to_user_id === currentUserId;

            return (
              <div
                key={index}
                className="flex items-center justify-between py-3 border-b last:border-0"
              >
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-sm font-medium text-orange-600">
                    {debt.from_user_name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-muted-foreground">→</span>
                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-sm font-medium text-green-600">
                    {debt.to_user_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="ml-2">
                    <p className="text-sm">
                      <span className="font-medium">{debt.from_user_name}</span>
                      <span className="text-muted-foreground"> owes </span>
                      <span className="font-medium">{debt.to_user_name}</span>
                    </p>
                    <p className="text-lg font-semibold">
                      {formatAmount(debt.amount)}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2">
                  {debt.upi_link && isCurrentUserOwing && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUPIClick(debt.upi_link!)}
                    >
                      Pay via UPI
                    </Button>
                  )}

                  {(isCurrentUserOwing || isCurrentUserOwed) && (
                    <Dialog
                      open={settlingDebt === debt}
                      onOpenChange={(open) => !open && setSettlingDebt(null)}
                    >
                      <DialogTrigger asChild>
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => setSettlingDebt(debt)}
                        >
                          Mark Settled
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Confirm Settlement</DialogTitle>
                        </DialogHeader>
                        <div className="py-4">
                          <p className="text-muted-foreground">
                            Confirm that{" "}
                            <span className="font-medium text-foreground">
                              {debt.from_user_name}
                            </span>{" "}
                            has paid{" "}
                            <span className="font-medium text-foreground">
                              {formatAmount(debt.amount)}
                            </span>{" "}
                            to{" "}
                            <span className="font-medium text-foreground">
                              {debt.to_user_name}
                            </span>
                            ?
                          </p>
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            onClick={() => setSettlingDebt(null)}
                          >
                            Cancel
                          </Button>
                          <Button
                            onClick={() => handleSettle(debt)}
                            disabled={isSubmitting}
                          >
                            {isSubmitting ? "Settling..." : "Confirm"}
                          </Button>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
