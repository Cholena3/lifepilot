"use client";

import * as React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { SplitGroup } from "@/lib/api/money";

interface SplitGroupCardProps {
  group: SplitGroup;
  onClick?: () => void;
}

export function SplitGroupCard({ group, onClick }: SplitGroupCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
    }).format(Math.abs(amount));
  };

  const acceptedMembers = group.members.filter((m) => m.status === "accepted");
  const pendingMembers = group.members.filter((m) => m.status === "pending");

  // Calculate total owed/owing for the group
  const totalOwed = group.members.reduce(
    (sum, m) => (m.balance > 0 ? sum + m.balance : sum),
    0
  );

  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-shadow"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h3 className="font-medium text-lg">{group.name}</h3>
            {group.description && (
              <p className="text-sm text-muted-foreground">{group.description}</p>
            )}
          </div>
          <Badge variant="outline">{acceptedMembers.length} members</Badge>
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          {acceptedMembers.slice(0, 4).map((member) => (
            <div
              key={member.id}
              className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium"
              title={member.user_name}
            >
              {member.user_name.charAt(0).toUpperCase()}
            </div>
          ))}
          {acceptedMembers.length > 4 && (
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs">
              +{acceptedMembers.length - 4}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Created {formatDate(group.created_at)}
          </span>
          {totalOwed > 0 && (
            <span className="text-orange-500 font-medium">
              {formatAmount(totalOwed)} unsettled
            </span>
          )}
        </div>

        {pendingMembers.length > 0 && (
          <p className="text-xs text-muted-foreground mt-2">
            {pendingMembers.length} pending invitation
            {pendingMembers.length !== 1 && "s"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
