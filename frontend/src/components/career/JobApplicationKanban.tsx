"use client";

import { useEffect, useState } from "react";
import { useCareerStore } from "@/store/career-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Plus,
  Building2,
  MapPin,
  Calendar,
  ExternalLink,
  GripVertical,
  Briefcase,
  TrendingUp,
  Clock,
} from "lucide-react";
import {
  JobApplication,
  ApplicationStatus,
  ApplicationSource,
  APPLICATION_STATUSES,
  APPLICATION_SOURCES,
} from "@/lib/api/career";

interface ApplicationFormProps {
  application?: JobApplication;
  onSubmit: (data: {
    company: string;
    role: string;
    url?: string;
    source?: ApplicationSource;
    status?: ApplicationStatus;
    salary_min?: number;
    salary_max?: number;
    applied_date?: string;
    notes?: string;
    location?: string;
    is_remote?: boolean;
  }) => Promise<void>;
  onClose: () => void;
}

function ApplicationForm({ application, onSubmit, onClose }: ApplicationFormProps) {
  const [company, setCompany] = useState(application?.company || "");
  const [role, setRole] = useState(application?.role || "");
  const [url, setUrl] = useState(application?.url || "");
  const [source, setSource] = useState<ApplicationSource>(application?.source || "other");
  const [location, setLocation] = useState(application?.location || "");
  const [isRemote, setIsRemote] = useState(application?.is_remote || false);
  const [salaryMin, setSalaryMin] = useState(application?.salary_min?.toString() || "");
  const [salaryMax, setSalaryMax] = useState(application?.salary_max?.toString() || "");
  const [notes, setNotes] = useState(application?.notes || "");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !role.trim()) return;

    setLoading(true);
    try {
      await onSubmit({
        company: company.trim(),
        role: role.trim(),
        url: url.trim() || undefined,
        source,
        location: location.trim() || undefined,
        is_remote: isRemote,
        salary_min: salaryMin ? parseFloat(salaryMin) : undefined,
        salary_max: salaryMax ? parseFloat(salaryMax) : undefined,
        notes: notes.trim() || undefined,
      });
      onClose();
    } catch (error) {
      console.error("Failed to save application:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="company">Company</Label>
          <Input
            id="company"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g., Google"
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="role">Role</Label>
          <Input
            id="role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g., Software Engineer"
            required
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">Job Posting URL</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="source">Source</Label>
          <Select value={source} onValueChange={(v) => setSource(v as ApplicationSource)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {APPLICATION_SOURCES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="location">Location</Label>
          <Input
            id="location"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g., San Francisco, CA"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="isRemote"
          checked={isRemote}
          onChange={(e) => setIsRemote(e.target.checked)}
          className="rounded"
        />
        <Label htmlFor="isRemote">Remote position</Label>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="salaryMin">Salary Min</Label>
          <Input
            id="salaryMin"
            type="number"
            value={salaryMin}
            onChange={(e) => setSalaryMin(e.target.value)}
            placeholder="e.g., 100000"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="salaryMax">Salary Max</Label>
          <Input
            id="salaryMax"
            type="number"
            value={salaryMax}
            onChange={(e) => setSalaryMax(e.target.value)}
            placeholder="e.g., 150000"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">Notes</Label>
        <Input
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any additional notes..."
        />
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || !company.trim() || !role.trim()}>
          {loading ? "Saving..." : application ? "Update" : "Add Application"}
        </Button>
      </div>
    </form>
  );
}

interface ApplicationCardProps {
  application: JobApplication;
  onDragStart: (e: React.DragEvent, applicationId: string) => void;
}

function ApplicationCard({ application, onDragStart }: ApplicationCardProps) {
  const sourceInfo = APPLICATION_SOURCES.find((s) => s.value === application.source);

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, application.id)}
      className="bg-background border rounded-lg p-3 cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow"
    >
      <div className="flex items-start gap-2">
        <GripVertical className="h-4 w-4 text-muted-foreground mt-1 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="font-medium truncate">{application.role}</h4>
            {application.url && (
              <a
                href={application.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
          <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
            <Building2 className="h-3 w-3" />
            <span className="truncate">{application.company}</span>
          </div>
          {application.location && (
            <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
              <MapPin className="h-3 w-3" />
              <span className="truncate">
                {application.location}
                {application.is_remote && " (Remote)"}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between mt-2">
            <Badge variant="outline" className="text-xs">
              {sourceInfo?.label}
            </Badge>
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(application.applied_date).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

interface KanbanColumnProps {
  status: ApplicationStatus;
  applications: JobApplication[];
  onDragStart: (e: React.DragEvent, applicationId: string) => void;
  onDrop: (e: React.DragEvent, status: ApplicationStatus) => void;
}

function KanbanColumn({
  status,
  applications,
  onDragStart,
  onDrop,
}: KanbanColumnProps) {
  const statusInfo = APPLICATION_STATUSES.find((s) => s.value === status);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    onDrop(e, status);
  };

  return (
    <div
      className={`flex flex-col min-w-[280px] max-w-[320px] ${
        isDragOver ? "ring-2 ring-primary ring-offset-2" : ""
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className={`w-3 h-3 rounded-full ${statusInfo?.color}`} />
        <h3 className="font-medium">{statusInfo?.label}</h3>
        <Badge variant="secondary" className="ml-auto">
          {applications.length}
        </Badge>
      </div>
      <div className="flex-1 space-y-2 min-h-[200px] p-2 bg-muted/30 rounded-lg">
        {applications.map((app) => (
          <ApplicationCard
            key={app.id}
            application={app}
            onDragStart={onDragStart}
          />
        ))}
        {applications.length === 0 && (
          <div className="text-center py-8 text-muted-foreground text-sm">
            No applications
          </div>
        )}
      </div>
    </div>
  );
}

export function JobApplicationKanban() {
  const {
    kanbanBoard,
    applicationStats,
    applicationsLoading,
    applicationsError,
    fetchKanbanBoard,
    fetchApplicationStats,
    createApplication,
    updateApplicationStatus,
  } = useCareerStore();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [draggedApplicationId, setDraggedApplicationId] = useState<string | null>(null);

  useEffect(() => {
    fetchKanbanBoard();
    fetchApplicationStats();
  }, [fetchKanbanBoard, fetchApplicationStats]);

  const handleAddApplication = async (data: Parameters<typeof createApplication>[0]) => {
    await createApplication(data);
  };

  const handleDragStart = (e: React.DragEvent, applicationId: string) => {
    setDraggedApplicationId(applicationId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDrop = async (e: React.DragEvent, newStatus: ApplicationStatus) => {
    if (draggedApplicationId) {
      await updateApplicationStatus(draggedApplicationId, newStatus);
      setDraggedApplicationId(null);
    }
  };

  if (applicationsLoading && !kanbanBoard) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-64 min-w-[280px]" />
          ))}
        </div>
      </div>
    );
  }

  if (applicationsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading applications: {applicationsError}</p>
        <Button onClick={() => fetchKanbanBoard()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {applicationStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Briefcase className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{applicationStats.total_applications}</p>
                  <p className="text-sm text-muted-foreground">Total Applications</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{applicationStats.response_rate.toFixed(0)}%</p>
                  <p className="text-sm text-muted-foreground">Response Rate</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                  <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {applicationStats.average_days_to_response?.toFixed(0) || "-"}
                  </p>
                  <p className="text-sm text-muted-foreground">Avg Days to Response</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                  <Calendar className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{applicationStats.applications_this_week}</p>
                  <p className="text-sm text-muted-foreground">This Week</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Job Applications</h2>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Application
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Add Job Application</DialogTitle>
            </DialogHeader>
            <ApplicationForm
              onSubmit={handleAddApplication}
              onClose={() => setShowAddDialog(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-4">
        {APPLICATION_STATUSES.map((statusInfo) => {
          const column = kanbanBoard?.columns.find((c) => c.status === statusInfo.value);
          return (
            <KanbanColumn
              key={statusInfo.value}
              status={statusInfo.value}
              applications={column?.applications || []}
              onDragStart={handleDragStart}
              onDrop={handleDrop}
            />
          );
        })}
      </div>
    </div>
  );
}
