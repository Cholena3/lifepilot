"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { GraduationCap, Bookmark, FileText, LayoutGrid } from "lucide-react";
import {
  ExamFeed,
  ExamFeedGrouped,
  ExamDetail,
  BookmarkedExams,
  ExamApplications,
} from "@/components/exam";

type ViewMode = "feed" | "grouped" | "bookmarks" | "applications";

export default function ExamPage() {
  const [activeTab, setActiveTab] = useState<ViewMode>("feed");
  const [selectedExamId, setSelectedExamId] = useState<string | null>(null);

  const handleExamSelect = (examId: string) => {
    setSelectedExamId(examId);
  };

  const handleBack = () => {
    setSelectedExamId(null);
  };

  // Show detail view if an exam is selected
  if (selectedExamId) {
    return (
      <div className="container mx-auto py-6 px-4">
        <ExamDetail examId={selectedExamId} onBack={handleBack} />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Exams</h1>
        <p className="text-muted-foreground">
          Discover and track exams, placements, and opportunities
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as ViewMode)}>
        <TabsList className="mb-6">
          <TabsTrigger value="feed" className="flex items-center gap-2">
            <GraduationCap className="h-4 w-4" />
            Feed
          </TabsTrigger>
          <TabsTrigger value="grouped" className="flex items-center gap-2">
            <LayoutGrid className="h-4 w-4" />
            By Category
          </TabsTrigger>
          <TabsTrigger value="bookmarks" className="flex items-center gap-2">
            <Bookmark className="h-4 w-4" />
            Bookmarks
          </TabsTrigger>
          <TabsTrigger value="applications" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Applications
          </TabsTrigger>
        </TabsList>

        <TabsContent value="feed">
          <ExamFeed onExamSelect={handleExamSelect} />
        </TabsContent>

        <TabsContent value="grouped">
          <ExamFeedGrouped onExamSelect={handleExamSelect} />
        </TabsContent>

        <TabsContent value="bookmarks">
          <BookmarkedExams onExamSelect={handleExamSelect} />
        </TabsContent>

        <TabsContent value="applications">
          <ExamApplications onExamSelect={handleExamSelect} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
