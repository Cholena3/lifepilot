"use client";

import { useEffect, useState } from "react";
import { useCareerStore } from "@/store/career-store";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
  Plus,
  Pencil,
  Trash2,
  Play,
  CheckCircle,
  Clock,
  Flame,
  BookOpen,
  ExternalLink,
} from "lucide-react";
import { Course } from "@/lib/api/career";

interface CourseFormProps {
  course?: Course;
  onSubmit: (data: {
    title: string;
    platform?: string;
    url?: string;
    total_hours?: number;
  }) => Promise<void>;
  onClose: () => void;
}

function CourseForm({ course, onSubmit, onClose }: CourseFormProps) {
  const [title, setTitle] = useState(course?.title || "");
  const [platform, setPlatform] = useState(course?.platform || "");
  const [url, setUrl] = useState(course?.url || "");
  const [totalHours, setTotalHours] = useState(course?.total_hours?.toString() || "");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    try {
      await onSubmit({
        title: title.trim(),
        platform: platform.trim() || undefined,
        url: url.trim() || undefined,
        total_hours: totalHours ? parseFloat(totalHours) : undefined,
      });
      onClose();
    } catch (error) {
      console.error("Failed to save course:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="title">Course Title</Label>
        <Input
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Complete Python Bootcamp"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="platform">Platform</Label>
        <Input
          id="platform"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          placeholder="e.g., Udemy, Coursera, YouTube"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="url">Course URL</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="totalHours">Total Duration (hours)</Label>
        <Input
          id="totalHours"
          type="number"
          min="0"
          step="0.5"
          value={totalHours}
          onChange={(e) => setTotalHours(e.target.value)}
          placeholder="e.g., 40"
        />
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || !title.trim()}>
          {loading ? "Saving..." : course ? "Update" : "Add Course"}
        </Button>
      </div>
    </form>
  );
}

interface LogSessionFormProps {
  onSubmit: (data: { duration_minutes: number; notes?: string }) => Promise<void>;
  onClose: () => void;
}

function LogSessionForm({ onSubmit, onClose }: LogSessionFormProps) {
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!duration) return;

    setLoading(true);
    try {
      await onSubmit({
        duration_minutes: parseInt(duration),
        notes: notes.trim() || undefined,
      });
      onClose();
    } catch (error) {
      console.error("Failed to log session:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="duration">Duration (minutes)</Label>
        <Input
          id="duration"
          type="number"
          min="1"
          max="1440"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
          placeholder="e.g., 60"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">Notes (optional)</Label>
        <Input
          id="notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What did you learn?"
        />
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || !duration}>
          {loading ? "Logging..." : "Log Session"}
        </Button>
      </div>
    </form>
  );
}

interface CourseCardProps {
  course: Course;
  onEdit: (course: Course) => void;
  onDelete: (courseId: string) => void;
  onLogSession: (courseId: string) => void;
  onMarkComplete: (courseId: string) => void;
}

function CourseCard({
  course,
  onEdit,
  onDelete,
  onLogSession,
  onMarkComplete,
}: CourseCardProps) {
  return (
    <Card className={course.is_completed ? "border-green-500/50 bg-green-50/50 dark:bg-green-950/20" : ""}>
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-medium truncate">{course.title}</h3>
              {course.is_completed && (
                <Badge variant="default" className="bg-green-500">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Completed
                </Badge>
              )}
            </div>
            {course.platform && (
              <p className="text-sm text-muted-foreground mt-1">{course.platform}</p>
            )}
          </div>
          <div className="flex items-center gap-1 ml-2">
            {course.url && (
              <Button variant="ghost" size="icon" asChild>
                <a href={course.url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={() => onEdit(course)}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(course.id)}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{course.completion_percentage}%</span>
          </div>
          <Progress value={course.completion_percentage} className="h-2" />
        </div>

        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            <span>
              {Number(course.completed_hours).toFixed(1)} / {Number(course.total_hours).toFixed(1)} hrs
            </span>
          </div>
          {course.last_activity_at && (
            <span>
              Last activity: {new Date(course.last_activity_at).toLocaleDateString()}
            </span>
          )}
        </div>

        {!course.is_completed && (
          <div className="mt-4 flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onLogSession(course.id)}
            >
              <Play className="h-4 w-4 mr-1" />
              Log Session
            </Button>
            <Button
              variant="default"
              size="sm"
              className="flex-1"
              onClick={() => onMarkComplete(course.id)}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Mark Complete
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function CourseTracking() {
  const {
    courses,
    learningStats,
    coursesLoading,
    coursesError,
    fetchCourses,
    fetchLearningStats,
    createCourse,
    updateCourse,
    deleteCourse,
    logLearningSession,
    markCourseComplete,
  } = useCareerStore();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingCourse, setEditingCourse] = useState<Course | null>(null);
  const [loggingSessionFor, setLoggingSessionFor] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "in_progress" | "completed">("all");

  useEffect(() => {
    fetchCourses();
    fetchLearningStats();
  }, [fetchCourses, fetchLearningStats]);

  const handleAddCourse = async (data: {
    title: string;
    platform?: string;
    url?: string;
    total_hours?: number;
  }) => {
    await createCourse(data);
  };

  const handleUpdateCourse = async (data: {
    title: string;
    platform?: string;
    url?: string;
    total_hours?: number;
  }) => {
    if (editingCourse) {
      await updateCourse(editingCourse.id, data);
    }
  };

  const handleDeleteCourse = async (courseId: string) => {
    if (confirm("Are you sure you want to delete this course?")) {
      await deleteCourse(courseId);
    }
  };

  const handleLogSession = async (data: { duration_minutes: number; notes?: string }) => {
    if (loggingSessionFor) {
      await logLearningSession(loggingSessionFor, data);
    }
  };

  const handleMarkComplete = async (courseId: string) => {
    await markCourseComplete(courseId);
  };

  const filteredCourses = courses.filter((course) => {
    if (filter === "in_progress") return !course.is_completed;
    if (filter === "completed") return course.is_completed;
    return true;
  });

  if (coursesLoading && courses.length === 0) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (coursesError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading courses: {coursesError}</p>
        <Button onClick={() => fetchCourses()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {learningStats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <BookOpen className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{learningStats.total_courses}</p>
                  <p className="text-sm text-muted-foreground">Total Courses</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{learningStats.completed_courses}</p>
                  <p className="text-sm text-muted-foreground">Completed</p>
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
                    {Number(learningStats.total_hours_invested).toFixed(1)}h
                  </p>
                  <p className="text-sm text-muted-foreground">Hours Invested</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-orange-100 dark:bg-orange-900 rounded-lg">
                  <Flame className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{learningStats.current_streak_days}</p>
                  <p className="text-sm text-muted-foreground">Day Streak</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-semibold">Courses</h2>
          <div className="flex gap-1">
            {(["all", "in_progress", "completed"] as const).map((f) => (
              <Button
                key={f}
                variant={filter === f ? "default" : "ghost"}
                size="sm"
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f === "in_progress" ? "In Progress" : "Completed"}
              </Button>
            ))}
          </div>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Course
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Course</DialogTitle>
            </DialogHeader>
            <CourseForm
              onSubmit={handleAddCourse}
              onClose={() => setShowAddDialog(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Course Grid */}
      {filteredCourses.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No courses found.</p>
            <p className="text-sm mt-1">Add a course to start tracking your learning!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredCourses.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              onEdit={setEditingCourse}
              onDelete={handleDeleteCourse}
              onLogSession={setLoggingSessionFor}
              onMarkComplete={handleMarkComplete}
            />
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingCourse} onOpenChange={(open) => !open && setEditingCourse(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Course</DialogTitle>
          </DialogHeader>
          {editingCourse && (
            <CourseForm
              course={editingCourse}
              onSubmit={handleUpdateCourse}
              onClose={() => setEditingCourse(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Log Session Dialog */}
      <Dialog
        open={!!loggingSessionFor}
        onOpenChange={(open) => !open && setLoggingSessionFor(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Log Learning Session</DialogTitle>
          </DialogHeader>
          {loggingSessionFor && (
            <LogSessionForm
              onSubmit={handleLogSession}
              onClose={() => setLoggingSessionFor(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
