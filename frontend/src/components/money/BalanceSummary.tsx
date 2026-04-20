"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SplitGroupMember } from "@/lib/api/money";

interface BalanceSummaryProps {
  members: SplitGroupMember[];
}

export function BalanceSummary({ members }: BalanceSummaryProps) {
  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(Math.abs(amount));
  };

  const acceptedMembers = members.filter((m) => m.status === "accepted");

  // Sort by balance (highest owed first, then highest owing)
  const sortedMembers = [...acceptedMembers].sort((a, b) => b.balance - a.balance);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Member Balances</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sortedMembers.map((member) => (
            <div
              key={member.id}
              className="flex items-center justify-between py-2 border-b last:border-0"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center font-medium">
                  {member.user_name.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium">{member.user_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {member.user_email}
                  </p>
                </div>
              </div>
              <div className="text-right">
                {member.balance === 0 ? (
                  <p className="text-muted-foreground">Settled up</p>
                ) : member.balance > 0 ? (
                  <div>
                    <p className="text-green-500 font-medium">
                      gets back {formatAmount(member.balance)}
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-orange-500 font-medium">
                      owes {formatAmount(member.balance)}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {acceptedMembers.length === 0 && (
          <p className="text-center text-muted-foreground py-4">
            No members in this group yet.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
