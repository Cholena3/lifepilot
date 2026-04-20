"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { SplitGroupCard } from "./SplitGroupCard";
import { useMoneyStore } from "@/store/money-store";
import { cn } from "@/lib/utils";

const createGroupSchema = z.object({
  name: z.string().min(1, "Group name is required"),
  description: z.string().optional(),
  member_emails: z.string().min(1, "At least one member email is required"),
});

type CreateGroupFormData = z.infer<typeof createGroupSchema>;

export function SplitGroupList() {
  const router = useRouter();
  const { splitGroups, isLoading, fetchSplitGroups, createSplitGroup, isSubmitting } =
    useMoneyStore();
  const [isDialogOpen, setIsDialogOpen] = React.useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateGroupFormData>({
    resolver: zodResolver(createGroupSchema),
    defaultValues: {
      name: "",
      description: "",
      member_emails: "",
    },
  });

  React.useEffect(() => {
    fetchSplitGroups();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSubmit = async (data: CreateGroupFormData) => {
    try {
      const emails = data.member_emails
        .split(",")
        .map((e) => e.trim())
        .filter((e) => e);
      await createSplitGroup({
        name: data.name,
        description: data.description || undefined,
        member_emails: emails,
      });
      reset();
      setIsDialogOpen(false);
    } catch {
      // Error handled by store
    }
  };

  const handleGroupClick = (groupId: string) => {
    router.push(`/money/splits/${groupId}`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Create Group Button */}
      <div className="flex justify-end">
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button>Create Split Group</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Split Group</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="name">Group Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Trip to Goa"
                  {...register("name")}
                  className={cn(errors.name && "border-destructive")}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description (Optional)</Label>
                <Input
                  id="description"
                  placeholder="What's this group for?"
                  {...register("description")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="member_emails">Member Emails</Label>
                <Input
                  id="member_emails"
                  placeholder="email1@example.com, email2@example.com"
                  {...register("member_emails")}
                  className={cn(errors.member_emails && "border-destructive")}
                />
                <p className="text-xs text-muted-foreground">
                  Separate multiple emails with commas
                </p>
                {errors.member_emails && (
                  <p className="text-sm text-destructive">
                    {errors.member_emails.message}
                  </p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create Group"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Group List */}
      {splitGroups.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No split groups yet. Create one to start splitting expenses with
            friends.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {splitGroups.map((group) => (
            <SplitGroupCard
              key={group.id}
              group={group}
              onClick={() => handleGroupClick(group.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
