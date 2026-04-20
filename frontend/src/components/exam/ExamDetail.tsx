"use client";

import { useEffect, useState } from "react";
import { useExamStore } from "@/store/exam-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  Calendar,
  CalendarPlus,
  CalendarX,
  Building2,
  ExternalLink,
  FileText,
  Link2,
  CheckCircle,
} from "lucide-react";
import { EXAM_TYPES, APPLICATION_STATUSES } from "@/lib/api/exam";

interface ExamDetailProps {
  examId: string;
  onBack: () => void;
}

export function ExamDetail({ examId, onBack }: ExamDetailProps) {
  const {
    selectedExam,
    calendarStatus,
    calendarSyncStatuses,
    fetchExamDetails,
    fetchCalendarStatus,
    fetchCalendarSyncStatus,
    toggleBookmark,
    markApplied,
    syncToCalendar,
    removeFromCalendar,
    getCalendarAuthUrl,
    clearSelection,
  } = useExamStore();

  const [showApplyDialog, setShowApplyDialog] = useState(false);
  const [applyDate, setApplyDate] = useState(
    new Date().toISOString().split("T")[0]
  );
  const [applyNotes, setApplyNotes] = useState("");
  const [applyLoading, setApplyLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);

  useEffect(() => {
    fetchExamDetails(examId);
    fetchCalendarStatus();
    fetchCalendarSyncStatus(examId);

    return () => {
      clearSelection();
    };
  }, [examId, fetchExamDetails, fetchCalendarStatus, fetchCalendarSyncStatus, clearSelection]);

  const syncStatus = calendarSyncStatuses[examId];
  const examTypeInfo = EXAM_TYPES.find((t) => t.value === selectedExam?.exam_type);
  const applicationStatusInfo = APPLICATION_STATUSES.find(
    (s) => s.value === selectedExam?.application_status
  );

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "TBA";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  };

  const handleBookmarkToggle = async () => {
    if (!selectedExam) return;
    try {
      await toggleBookmark(selectedExam.id, selectedExam.is_bookmarked);
    } catch (error) {
      console.error("Failed to toggle bookmark:", error);
    }
  };

  const handleMarkApplied = async () => {
    if (!selectedExam) return;
    setApplyLoading(true);
    try {
      await markApplied(selectedExam.id, applyDate, applyNotes || undefined);
      setShowApplyDialog(false);
      setApplyNotes("");
    } catch (error) {
      console.error("Failed to mark as applied:", error);
    } finally {
      setApplyLoading(false);
    }
  };

  const handleCalendarSync = async () => {
    if (!selectedExam) return;
    setCalendarLoading(true);
    try {
      if (!calendarStatus?.is_connected) {
        const authUrl = await getCalendarAuthUrl();
        window.open(authUrl, "_blank");
      } else if (syncStatus?.is_synced) {
        await removeFromCalendar(selectedExam.id);
      } else {
        await syncToCalendar(selectedExam.id);
      }
    } catch (error) {
      console.error("Failed to sync calendar:", error);
    } finally {
      setCalendarLoading(false);
    }
  };

  if (!selectedExam) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{selectedExam.name}</h1>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span>{selectedExam.organization}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={selectedExam.is_bookmarked ? "default" : "outline"}
          onClick={handleBookmarkToggle}
        >
          {selectedExam.is_bookmarked ? (
            <>
              <BookmarkCheck className="h-4 w-4 mr-2" />
              Bookmarked
            </>
          ) : (
            <>
              <Bookmark className="h-4 w-4 mr-2" />
              Bookmark
            </>
          )}
        </Button>

        {selectedExam.is_applied ? (
          <Button variant="secondary" disabled>
            <CheckCircle className="h-4 w-4 mr-2" />
            Applied ({applicationStatusInfo?.label})
          </Button>
        ) : (
          <Dialog open={showApplyDialog} onOpenChange={setShowApplyDialog}>
            <DialogTrigger asChild>
              <Button>
                <FileText className="h-4 w-4 mr-2" />
                Mark as Applied
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Mark as Applied</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="applyDate">Application Date</Label>
                  <Input
                    id="applyDate"
                    type="date"
                    value={applyDate}
                    onChange={(e) => setApplyDate(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="applyNotes">Notes (optional)</Label>
                  <Textarea
                    id="applyNotes"
                    placeholder="Any notes about your application..."
                    value={applyNotes}
                    onChange={(e) => setApplyNotes(e.target.value)}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setShowApplyDialog(false)}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleMarkApplied} disabled={applyLoading}>
                    {applyLoading ? "Saving..." : "Confirm"}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}

        <Button
          variant="outline"
          onClick={handleCalendarSync}
          disabled={calendarLoading}
        >
          {!calendarStatus?.is_connected ? (
            <>
              <Calendar className="h-4 w-4 mr-2" />
              Connect Calendar
            </>
          ) : syncStatus?.is_synced ? (
            <>
              <CalendarX className="h-4 w-4 mr-2" />
              Remove from Calendar
            </>
          ) : (
            <>
              <CalendarPlus className="h-4 w-4 mr-2" />
              Add to Calendar
            </>
          )}
        </Button>

        {selectedExam.source_url && (
          <Button variant="outline" asChild>
            <a
              href={selectedExam.source_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Official Website
            </a>
          </Button>
        )}
      </div>

      {/* Main Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview Card */}
          <Card>
            <CardHeader>
              <CardTitle>Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <Badge
                  className={`${examTypeInfo?.color} text-white`}
                >
                  {examTypeInfo?.label || selectedExam.exam_type}
                </Badge>
                {!selectedExam.is_active && (
                  <Badge variant="destructive">Inactive</Badge>
                )}
              </div>

              {selectedExam.description && (
                <p className="text-muted-foreground">{selectedExam.description}</p>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground">Registration Opens</p>
                  <p className="font-medium">{formatDate(selectedExam.registration_start)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Registration Deadline</p>
                  <p className="font-medium">{formatDate(selectedExam.registration_end)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Exam Date</p>
                  <p className="font-medium">{formatDate(selectedExam.exam_date)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Syllabus Card */}
          {selectedExam.syllabus && (
            <Card>
              <CardHeader>
                <CardTitle>Syllabus</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-lg">
                    {selectedExam.syllabus}
                  </pre>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Cutoffs Card */}
          {selectedExam.cutoffs && Object.keys(selectedExam.cutoffs).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Previous Cutoffs</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(selectedExam.cutoffs).map(([key, value]) => (
                    <div key={key} className="flex justify-between py-2 border-b last:border-0">
                      <span className="text-muted-foreground">{key}</span>
                      <span className="font-medium">{String(value)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Resources Card */}
          {selectedExam.resources && selectedExam.resources.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Resources</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {selectedExam.resources.map((resource, idx) => (
                    <a
                      key={idx}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 p-3 rounded-lg border hover:bg-muted transition-colors"
                    >
                      <Link2 className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1">{resource.title}</span>
                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column - Eligibility */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Eligibility Criteria</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {selectedExam.min_cgpa && (
                <div>
                  <p className="text-sm text-muted-foreground">Minimum CGPA</p>
                  <p className="font-medium">{selectedExam.min_cgpa}</p>
                </div>
              )}

              {selectedExam.max_backlogs !== null && (
                <div>
                  <p className="text-sm text-muted-foreground">Maximum Backlogs</p>
                  <p className="font-medium">
                    {selectedExam.max_backlogs === 0
                      ? "No backlogs allowed"
                      : `Up to ${selectedExam.max_backlogs}`}
                  </p>
                </div>
              )}

              {selectedExam.eligible_degrees && selectedExam.eligible_degrees.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Eligible Degrees</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedExam.eligible_degrees.map((degree) => (
                      <Badge key={degree} variant="outline">
                        {degree}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {selectedExam.eligible_branches && selectedExam.eligible_branches.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Eligible Branches</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedExam.eligible_branches.map((branch) => (
                      <Badge key={branch} variant="outline">
                        {branch}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {(selectedExam.graduation_year_min || selectedExam.graduation_year_max) && (
                <div>
                  <p className="text-sm text-muted-foreground">Graduation Year</p>
                  <p className="font-medium">
                    {selectedExam.graduation_year_min && selectedExam.graduation_year_max
                      ? `${selectedExam.graduation_year_min} - ${selectedExam.graduation_year_max}`
                      : selectedExam.graduation_year_min
                      ? `${selectedExam.graduation_year_min} onwards`
                      : `Up to ${selectedExam.graduation_year_max}`}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Calendar Status */}
          {calendarStatus?.is_connected && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Calendar Sync</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Connected to:</span>
                  </div>
                  <p className="font-medium">{calendarStatus.email}</p>
                  {syncStatus?.is_synced && (
                    <Badge variant="secondary" className="mt-2">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Synced to Calendar
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
