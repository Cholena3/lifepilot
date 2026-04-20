"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bookmark, BookmarkCheck, Calendar, Building2, GraduationCap } from "lucide-react";
import { Exam, EXAM_TYPES } from "@/lib/api/exam";

interface ExamCardProps {
  exam: Exam;
  isBookmarked?: boolean;
  onBookmarkToggle?: (examId: string, isBookmarked: boolean) => void;
  onClick?: (examId: string) => void;
}

export function ExamCard({
  exam,
  isBookmarked = false,
  onBookmarkToggle,
  onClick,
}: ExamCardProps) {
  const examTypeInfo = EXAM_TYPES.find((t) => t.value === exam.exam_type);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "TBA";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getDaysUntil = (dateStr: string | null) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    const today = new Date();
    const diffTime = date.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const registrationDays = getDaysUntil(exam.registration_end);
  const isUrgent = registrationDays !== null && registrationDays <= 7 && registrationDays > 0;
  const isExpired = registrationDays !== null && registrationDays < 0;

  return (
    <Card
      className={`cursor-pointer hover:shadow-md transition-shadow ${
        isUrgent ? "border-orange-400" : ""
      } ${isExpired ? "opacity-60" : ""}`}
      onClick={() => onClick?.(exam.id)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate">{exam.name}</CardTitle>
            <div className="flex items-center gap-1 text-sm text-muted-foreground mt-1">
              <Building2 className="h-3 w-3" />
              <span className="truncate">{exam.organization}</span>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              onBookmarkToggle?.(exam.id, isBookmarked);
            }}
          >
            {isBookmarked ? (
              <BookmarkCheck className="h-5 w-5 text-primary" />
            ) : (
              <Bookmark className="h-5 w-5" />
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {/* Badges */}
          <div className="flex flex-wrap gap-2">
            <Badge
              variant="secondary"
              className={`${examTypeInfo?.color} text-white`}
            >
              {examTypeInfo?.label || exam.exam_type}
            </Badge>
            {isUrgent && (
              <Badge variant="destructive">
                {registrationDays} days left
              </Badge>
            )}
            {isExpired && <Badge variant="outline">Registration Closed</Badge>}
          </div>

          {/* Dates */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Calendar className="h-3 w-3" />
              <span>Deadline: {formatDate(exam.registration_end)}</span>
            </div>
            {exam.exam_date && (
              <div className="flex items-center gap-1 text-muted-foreground">
                <GraduationCap className="h-3 w-3" />
                <span>Exam: {formatDate(exam.exam_date)}</span>
              </div>
            )}
          </div>

          {/* Eligibility */}
          <div className="flex flex-wrap gap-2 text-xs">
            {exam.min_cgpa && (
              <Badge variant="outline">Min CGPA: {exam.min_cgpa}</Badge>
            )}
            {exam.max_backlogs !== null && (
              <Badge variant="outline">
                {exam.max_backlogs === 0
                  ? "No Backlogs"
                  : `Max ${exam.max_backlogs} Backlogs`}
              </Badge>
            )}
          </div>

          {/* Description preview */}
          {exam.description && (
            <p className="text-sm text-muted-foreground line-clamp-2">
              {exam.description}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
