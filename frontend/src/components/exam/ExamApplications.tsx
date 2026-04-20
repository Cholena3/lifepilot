"use client";

import { useEffect, useState } from "react";
import { useExamStore } from "@/store/exam-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Building2, Calendar, Pencil, Trash2 } from "lucide-react";
import {
  ApplicationStatus,
  APPLICATION_STATUSES,
  EXAM_TYPES,
} from "@/lib/api/exam";

interface ExamApplicationsProps {
  onExamSelect: (examId: string) => void;
}

export function ExamApplications({ onExamSelect }: ExamApplicationsProps) {
  const {
    applications,
    applicationsTotal,
    applicationsLoading,
    fetchApplications,
    updateApplication,
    deleteApplication,
  } = useExamStore();

  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "all">("all");
  const [editingApp, setEditingApp] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState<ApplicationStatus>("applied");
  const [editNotes, setEditNotes] = useState("");
  const [updateLoading, setUpdateLoading] = useState(false);

  useEffect(() => {
    fetchApplications(statusFilter === "all" ? undefined : statusFilter);
  }, [fetchApplications, statusFilter]);

  const handleStatusFilterChange = (value: string) => {
    setStatusFilter(value as ApplicationStatus | "all");
  };

  const handleEditClick = (appId: string, currentStatus: ApplicationStatus, currentNotes: string | null) => {
    setEditingApp(appId);
    setEditStatus(currentStatus);
    setEditNotes(currentNotes || "");
  };

  const handleUpdateApplication = async () => {
    if (!editingApp) return;
    setUpdateLoading(true);
    try {
      await updateApplication(editingApp, {
        status: editStatus,
        notes: editNotes || undefined,
      });
      setEditingApp(null);
    } catch (error) {
      console.error("Failed to update application:", error);
    } finally {
      setUpdateLoading(false);
    }
  };

  const handleDeleteApplication = async (appId: string) => {
    if (!confirm("Are you sure you want to delete this application record?")) return;
    try {
      await deleteApplication(appId);
    } catch (error) {
      console.error("Failed to delete application:", error);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  if (applicationsLoading && applications.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-48" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filter */}
      <div className="flex items-center gap-4">
        <Label>Filter by status:</Label>
        <Select value={statusFilter} onValueChange={handleStatusFilterChange}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Applications</SelectItem>
            {APPLICATION_STATUSES.map((status) => (
              <SelectItem key={status.value} value={status.value}>
                {status.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Summary */}
      <p className="text-sm text-muted-foreground">
        {applicationsTotal} application{applicationsTotal !== 1 ? "s" : ""}
      </p>

      {/* Applications List */}
      {applications.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No applications found.</p>
            <p className="text-sm mt-1">
              Mark exams as applied to track your applications here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {applications.map((app) => {
            const statusInfo = APPLICATION_STATUSES.find((s) => s.value === app.status);
            const examTypeInfo = app.exam
              ? EXAM_TYPES.find((t) => t.value === app.exam?.exam_type)
              : null;

            return (
              <Card key={app.id} className="hover:shadow-md transition-shadow">
                <CardContent className="py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div
                      className="flex-1 cursor-pointer"
                      onClick={() => app.exam && onExamSelect(app.exam_id)}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-semibold">
                          {app.exam?.name || "Unknown Exam"}
                        </h3>
                        <Badge className={`${statusInfo?.color} text-white`}>
                          {statusInfo?.label}
                        </Badge>
                      </div>

                      {app.exam && (
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Building2 className="h-3 w-3" />
                            {app.exam.organization}
                          </span>
                          {examTypeInfo && (
                            <Badge variant="outline" className="text-xs">
                              {examTypeInfo.label}
                            </Badge>
                          )}
                        </div>
                      )}

                      <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          Applied: {formatDate(app.applied_date)}
                        </span>
                      </div>

                      {app.notes && (
                        <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                          {app.notes}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEditClick(app.id, app.status, app.notes)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDeleteApplication(app.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingApp} onOpenChange={(open) => !open && setEditingApp(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Application</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={editStatus}
                onValueChange={(v) => setEditStatus(v as ApplicationStatus)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPLICATION_STATUSES.map((status) => (
                    <SelectItem key={status.value} value={status.value}>
                      {status.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                placeholder="Any notes about this application..."
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditingApp(null)}>
                Cancel
              </Button>
              <Button onClick={handleUpdateApplication} disabled={updateLoading}>
                {updateLoading ? "Saving..." : "Update"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
