"use client";

import { useEffect } from "react";
import { useExamStore } from "@/store/exam-store";
import { ExamCard } from "./ExamCard";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Bookmark } from "lucide-react";

interface BookmarkedExamsProps {
  onExamSelect: (examId: string) => void;
}

export function BookmarkedExams({ onExamSelect }: BookmarkedExamsProps) {
  const {
    bookmarks,
    bookmarksTotal,
    bookmarksLoading,
    fetchBookmarks,
    toggleBookmark,
  } = useExamStore();

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  const handleBookmarkToggle = async (examId: string, isBookmarked: boolean) => {
    try {
      await toggleBookmark(examId, isBookmarked);
    } catch (error) {
      console.error("Failed to toggle bookmark:", error);
    }
  };

  if (bookmarksLoading && bookmarks.length === 0) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    );
  }

  if (bookmarks.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <Bookmark className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No bookmarked exams yet.</p>
          <p className="text-sm mt-1">
            Bookmark exams from the feed to save them here for quick access.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {bookmarksTotal} bookmarked exam{bookmarksTotal !== 1 ? "s" : ""}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {bookmarks.map((bookmark) =>
          bookmark.exam ? (
            <ExamCard
              key={bookmark.id}
              exam={bookmark.exam}
              isBookmarked={true}
              onBookmarkToggle={handleBookmarkToggle}
              onClick={onExamSelect}
            />
          ) : null
        )}
      </div>
    </div>
  );
}
