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
  FileText,
  Download,
  Pencil,
  Trash2,
  RefreshCw,
  Eye,
  Layout,
} from "lucide-react";
import {
  Resume,
  ResumeSummary,
  ResumeTemplate,
  RESUME_TEMPLATES,
} from "@/lib/api/career";

interface ResumeFormProps {
  resume?: Resume;
  onSubmit: (data: {
    name: string;
    template?: ResumeTemplate;
    populate_from_profile?: boolean;
  }) => Promise<void>;
  onClose: () => void;
}

function ResumeForm({ resume, onSubmit, onClose }: ResumeFormProps) {
  const [name, setName] = useState(resume?.name || "");
  const [template, setTemplate] = useState<ResumeTemplate>(resume?.template || "classic");
  const [populateFromProfile, setPopulateFromProfile] = useState(!resume);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      await onSubmit({
        name: name.trim(),
        template,
        populate_from_profile: populateFromProfile,
      });
      onClose();
    } catch (error) {
      console.error("Failed to save resume:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Resume Name</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Software Engineer Resume"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="template">Template</Label>
        <Select value={template} onValueChange={(v) => setTemplate(v as ResumeTemplate)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RESUME_TEMPLATES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                <div>
                  <div className="font-medium">{t.label}</div>
                  <div className="text-xs text-muted-foreground">{t.description}</div>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {!resume && (
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="populateFromProfile"
            checked={populateFromProfile}
            onChange={(e) => setPopulateFromProfile(e.target.checked)}
            className="rounded"
          />
          <Label htmlFor="populateFromProfile">
            Populate from profile, skills, and achievements
          </Label>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || !name.trim()}>
          {loading ? "Saving..." : resume ? "Update" : "Create Resume"}
        </Button>
      </div>
    </form>
  );
}

interface ResumePreviewProps {
  resume: Resume;
  onClose: () => void;
}

function ResumePreview({ resume, onClose }: ResumePreviewProps) {
  const content = resume.content;

  return (
    <div className="max-h-[70vh] overflow-y-auto">
      <div className="bg-white text-black p-8 rounded-lg shadow-lg">
        {/* Personal Info */}
        {content.personal_info && (
          <div className="text-center mb-6 border-b pb-4">
            <h1 className="text-2xl font-bold">{content.personal_info.full_name}</h1>
            <div className="flex items-center justify-center gap-4 mt-2 text-sm text-gray-600">
              {content.personal_info.email && <span>{content.personal_info.email}</span>}
              {content.personal_info.phone && <span>{content.personal_info.phone}</span>}
              {content.personal_info.location && <span>{content.personal_info.location}</span>}
            </div>
            <div className="flex items-center justify-center gap-4 mt-1 text-sm text-blue-600">
              {content.personal_info.linkedin_url && (
                <a href={content.personal_info.linkedin_url} target="_blank" rel="noopener noreferrer">
                  LinkedIn
                </a>
              )}
              {content.personal_info.github_url && (
                <a href={content.personal_info.github_url} target="_blank" rel="noopener noreferrer">
                  GitHub
                </a>
              )}
              {content.personal_info.portfolio_url && (
                <a href={content.personal_info.portfolio_url} target="_blank" rel="noopener noreferrer">
                  Portfolio
                </a>
              )}
            </div>
          </div>
        )}

        {/* Summary */}
        {content.summary && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Summary</h2>
            <p className="text-sm text-gray-700">{content.summary}</p>
          </div>
        )}

        {/* Experience */}
        {content.experience && content.experience.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Experience</h2>
            <div className="space-y-4">
              {content.experience.map((exp, idx) => (
                <div key={idx}>
                  <div className="flex justify-between">
                    <div>
                      <h3 className="font-medium">{exp.role}</h3>
                      <p className="text-sm text-gray-600">{exp.company}</p>
                    </div>
                    <div className="text-sm text-gray-500">
                      {exp.start_date} - {exp.is_current ? "Present" : exp.end_date}
                    </div>
                  </div>
                  {exp.description && (
                    <p className="text-sm text-gray-700 mt-1">{exp.description}</p>
                  )}
                  {exp.highlights && exp.highlights.length > 0 && (
                    <ul className="list-disc list-inside text-sm text-gray-700 mt-1">
                      {exp.highlights.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Education */}
        {content.education && content.education.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Education</h2>
            <div className="space-y-2">
              {content.education.map((edu, idx) => (
                <div key={idx} className="flex justify-between">
                  <div>
                    <h3 className="font-medium">{edu.degree}</h3>
                    <p className="text-sm text-gray-600">{edu.institution}</p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {edu.start_date} - {edu.end_date}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills */}
        {content.skills && content.skills.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Skills</h2>
            <div className="flex flex-wrap gap-2">
              {content.skills.map((skill, idx) => (
                <span
                  key={idx}
                  className="px-2 py-1 bg-gray-100 rounded text-sm"
                >
                  {skill.name}
                  {skill.proficiency && (
                    <span className="text-gray-500 ml-1">({skill.proficiency})</span>
                  )}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Achievements */}
        {content.achievements && content.achievements.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Achievements</h2>
            <div className="space-y-2">
              {content.achievements.map((achievement, idx) => (
                <div key={idx}>
                  <h3 className="font-medium">{achievement.title}</h3>
                  {achievement.description && (
                    <p className="text-sm text-gray-700">{achievement.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Projects */}
        {content.projects && content.projects.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-semibold border-b mb-2">Projects</h2>
            <div className="space-y-2">
              {content.projects.map((project, idx) => (
                <div key={idx}>
                  <h3 className="font-medium">{project.name}</h3>
                  {project.description && (
                    <p className="text-sm text-gray-700">{project.description}</p>
                  )}
                  {project.technologies && project.technologies.length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      Technologies: {project.technologies.join(", ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end mt-4">
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>
    </div>
  );
}

interface ResumeCardProps {
  resume: ResumeSummary;
  onView: (resumeId: string) => void;
  onEdit: (resumeId: string) => void;
  onDelete: (resumeId: string) => void;
  onExport: (resumeId: string) => void;
  onPopulate: (resumeId: string) => void;
}

function ResumeCard({
  resume,
  onView,
  onEdit,
  onDelete,
  onExport,
  onPopulate,
}: ResumeCardProps) {
  const templateInfo = RESUME_TEMPLATES.find((t) => t.value === resume.template);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <FileText className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h3 className="font-medium">{resume.name}</h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-xs">
                  <Layout className="h-3 w-3 mr-1" />
                  {templateInfo?.label}
                </Badge>
                <span className="text-xs text-muted-foreground">v{resume.version}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 text-xs text-muted-foreground">
          Last updated: {new Date(resume.updated_at).toLocaleDateString()}
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={() => onView(resume.id)}>
            <Eye className="h-4 w-4 mr-1" />
            Preview
          </Button>
          <Button variant="outline" size="sm" onClick={() => onExport(resume.id)}>
            <Download className="h-4 w-4 mr-1" />
            PDF
          </Button>
          <Button variant="outline" size="sm" onClick={() => onPopulate(resume.id)}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
          <Button variant="ghost" size="sm" onClick={() => onEdit(resume.id)}>
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(resume.id)}
            className="text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function ResumeBuilder() {
  const {
    resumes,
    selectedResume,
    resumeTemplates,
    resumesLoading,
    resumesError,
    fetchResumes,
    fetchResume,
    fetchTemplates,
    createResume,
    updateResume,
    deleteResume,
    populateResume,
    exportResumePdf,
  } = useCareerStore();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingResumeId, setEditingResumeId] = useState<string | null>(null);
  const [viewingResume, setViewingResume] = useState<Resume | null>(null);

  useEffect(() => {
    fetchResumes();
    fetchTemplates();
  }, [fetchResumes, fetchTemplates]);

  const handleCreateResume = async (data: {
    name: string;
    template?: ResumeTemplate;
    populate_from_profile?: boolean;
  }) => {
    await createResume(data);
  };

  const handleViewResume = async (resumeId: string) => {
    await fetchResume(resumeId);
    // Wait for the store to update
    setTimeout(() => {
      const { selectedResume } = useCareerStore.getState();
      if (selectedResume) {
        setViewingResume(selectedResume);
      }
    }, 100);
  };

  const handleEditResume = async (resumeId: string) => {
    setEditingResumeId(resumeId);
    await fetchResume(resumeId);
  };

  const handleDeleteResume = async (resumeId: string) => {
    if (confirm("Are you sure you want to delete this resume?")) {
      await deleteResume(resumeId);
    }
  };

  const handleExportPdf = async (resumeId: string) => {
    try {
      await exportResumePdf(resumeId);
    } catch (error) {
      console.error("Failed to export PDF:", error);
      alert("Failed to export PDF. Please try again.");
    }
  };

  const handlePopulateResume = async (resumeId: string) => {
    try {
      await populateResume(resumeId);
      alert("Resume refreshed with latest profile data!");
    } catch (error) {
      console.error("Failed to populate resume:", error);
    }
  };

  if (resumesLoading && resumes.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (resumesError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading resumes: {resumesError}</p>
        <Button onClick={() => fetchResumes()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Resume Builder</h2>
          <p className="text-sm text-muted-foreground">
            Create and manage multiple resume versions
          </p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Resume
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Resume</DialogTitle>
            </DialogHeader>
            <ResumeForm
              onSubmit={handleCreateResume}
              onClose={() => setShowAddDialog(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {/* Template Selection Info */}
      {resumeTemplates && (
        <Card className="bg-muted/30">
          <CardContent className="pt-4">
            <h3 className="font-medium mb-2">Available Templates</h3>
            <div className="flex flex-wrap gap-2">
              {resumeTemplates.templates.map((template) => (
                <Badge key={template.id} variant="outline">
                  {template.name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resume Grid */}
      {resumes.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No resumes created yet.</p>
            <p className="text-sm mt-1">
              Create your first resume to get started!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumes.map((resume) => (
            <ResumeCard
              key={resume.id}
              resume={resume}
              onView={handleViewResume}
              onEdit={handleEditResume}
              onDelete={handleDeleteResume}
              onExport={handleExportPdf}
              onPopulate={handlePopulateResume}
            />
          ))}
        </div>
      )}

      {/* Preview Dialog */}
      <Dialog open={!!viewingResume} onOpenChange={(open) => !open && setViewingResume(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Resume Preview</DialogTitle>
          </DialogHeader>
          {viewingResume && (
            <ResumePreview
              resume={viewingResume}
              onClose={() => setViewingResume(null)}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={!!editingResumeId}
        onOpenChange={(open) => !open && setEditingResumeId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Resume</DialogTitle>
          </DialogHeader>
          {selectedResume && editingResumeId === selectedResume.id && (
            <ResumeForm
              resume={selectedResume}
              onSubmit={async (data) => {
                await updateResume(editingResumeId, data);
              }}
              onClose={() => setEditingResumeId(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
