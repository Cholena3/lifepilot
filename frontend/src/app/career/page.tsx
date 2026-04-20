"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Code2, BookOpen, Briefcase, FileText } from "lucide-react";
import {
  SkillInventory,
  CourseTracking,
  JobApplicationKanban,
  ResumeBuilder,
} from "@/components/career";

export default function CareerPage() {
  const [activeTab, setActiveTab] = useState("skills");

  return (
    <div className="container mx-auto py-6 px-4">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Career</h1>
        <p className="text-muted-foreground">
          Track your skills, learning progress, job applications, and build resumes
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="skills" className="flex items-center gap-2">
            <Code2 className="h-4 w-4" />
            Skills
          </TabsTrigger>
          <TabsTrigger value="courses" className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Courses
          </TabsTrigger>
          <TabsTrigger value="applications" className="flex items-center gap-2">
            <Briefcase className="h-4 w-4" />
            Applications
          </TabsTrigger>
          <TabsTrigger value="resumes" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Resumes
          </TabsTrigger>
        </TabsList>

        <TabsContent value="skills">
          <SkillInventory />
        </TabsContent>

        <TabsContent value="courses">
          <CourseTracking />
        </TabsContent>

        <TabsContent value="applications">
          <JobApplicationKanban />
        </TabsContent>

        <TabsContent value="resumes">
          <ResumeBuilder />
        </TabsContent>
      </Tabs>
    </div>
  );
}
