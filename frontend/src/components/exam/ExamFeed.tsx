"use client";

import { useEffect } from "react";
import { useExamStore } from "@/store/exam-store";
import { ExamFilters } from "./ExamFilters";
import { ExamCard } from "./ExamCard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EXAM_TYPES } from "@/lib/api/exam";

interface ExamFeedProps {
  onExamSelect: (examId: string) => void;
}

export function ExamFeed({ onExamSelect }: ExamFeedProps) {
  const {
    exams,
    examsTotal,
    examsPage,
    examsLoading,
    examsError,
    filters,
    bookmarks,
    fetchExams,
    fetchBookmarks,
    setFilters,
    clearFilters,
    toggleBookmark,
  } = useExamStore();

  useEffect(() => {
    fetchExams();
    fetchBookmarks();
  }, [fetchExams, fetchBookmarks]);

  const bookmarkedIds = new Set(bookmarks.map((b) => b.exam_id));

  const handleApplyFilters = () => {
    fetchExams(filters, 1);
  };

  const handleClearFilters = () => {
    clearFilters();
    fetchExams({ upcoming_only: true }, 1);
  };

  const handleBookmarkToggle = async (examId: string, isBookmarked: boolean) => {
    try {
      await toggleBookmark(examId, isBookmarked);
    } catch (error) {
      console.error("Failed to toggle bookmark:", error);
    }
  };

  const handleLoadMore = () => {
    fetchExams(filters, examsPage + 1);
  };

  if (examsLoading && exams.length === 0) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (examsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading exams: {examsError}</p>
        <Button onClick={() => fetchExams()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <ExamFilters
        filters={filters}
        onFiltersChange={setFilters}
        onApply={handleApplyFilters}
        onClear={handleClearFilters}
      />

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Showing {exams.length} of {examsTotal} exams
        </p>
      </div>

      {/* Exam Grid */}
      {exams.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No exams found matching your criteria.</p>
            <p className="text-sm mt-1">Try adjusting your filters.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {exams.map((exam) => (
              <ExamCard
                key={exam.id}
                exam={exam}
                isBookmarked={bookmarkedIds.has(exam.id)}
                onBookmarkToggle={handleBookmarkToggle}
                onClick={onExamSelect}
              />
            ))}
          </div>

          {/* Load More */}
          {exams.length < examsTotal && (
            <div className="flex justify-center">
              <Button
                variant="outline"
                onClick={handleLoadMore}
                disabled={examsLoading}
              >
                {examsLoading ? "Loading..." : "Load More"}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function ExamFeedGrouped({ onExamSelect }: ExamFeedProps) {
  const {
    examsGrouped,
    examsLoading,
    examsError,
    filters,
    bookmarks,
    fetchExamsGrouped,
    fetchBookmarks,
    setFilters,
    clearFilters,
    toggleBookmark,
  } = useExamStore();

  useEffect(() => {
    fetchExamsGrouped();
    fetchBookmarks();
  }, [fetchExamsGrouped, fetchBookmarks]);

  const bookmarkedIds = new Set(bookmarks.map((b) => b.exam_id));

  const handleApplyFilters = () => {
    fetchExamsGrouped(filters);
  };

  const handleClearFilters = () => {
    clearFilters();
    fetchExamsGrouped({ upcoming_only: true });
  };

  const handleBookmarkToggle = async (examId: string, isBookmarked: boolean) => {
    try {
      await toggleBookmark(examId, isBookmarked);
    } catch (error) {
      console.error("Failed to toggle bookmark:", error);
    }
  };

  if (examsLoading && !examsGrouped) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Array.from({ length: 2 }).map((_, j) => (
                  <Skeleton key={j} className="h-48 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (examsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading exams: {examsError}</p>
        <Button onClick={() => fetchExamsGrouped()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <ExamFilters
        filters={filters}
        onFiltersChange={setFilters}
        onApply={handleApplyFilters}
        onClear={handleClearFilters}
      />

      {/* Results Summary */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {examsGrouped?.total_exams || 0} exams found
        </p>
      </div>

      {/* Grouped Exams */}
      {!examsGrouped || examsGrouped.groups.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No exams found matching your criteria.</p>
            <p className="text-sm mt-1">Try adjusting your filters.</p>
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue={examsGrouped.groups[0]?.exam_type}>
          <TabsList className="flex-wrap h-auto gap-1">
            {examsGrouped.groups.map((group) => {
              const typeInfo = EXAM_TYPES.find((t) => t.value === group.exam_type);
              return (
                <TabsTrigger key={group.exam_type} value={group.exam_type}>
                  {typeInfo?.label || group.exam_type} ({group.count})
                </TabsTrigger>
              );
            })}
          </TabsList>

          {examsGrouped.groups.map((group) => (
            <TabsContent key={group.exam_type} value={group.exam_type}>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {group.exams.map((exam) => (
                  <ExamCard
                    key={exam.id}
                    exam={exam}
                    isBookmarked={bookmarkedIds.has(exam.id)}
                    onBookmarkToggle={handleBookmarkToggle}
                    onClick={onExamSelect}
                  />
                ))}
              </div>
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}
