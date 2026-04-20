"use client";

import { useEffect, useState } from "react";
import { useCareerStore } from "@/store/career-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Trash2, Lightbulb } from "lucide-react";
import {
  Skill,
  SkillCategory,
  ProficiencyLevel,
  PROFICIENCY_LEVELS,
  SKILL_CATEGORIES,
} from "@/lib/api/career";

const proficiencyToProgress: Record<ProficiencyLevel, number> = {
  beginner: 25,
  intermediate: 50,
  advanced: 75,
  expert: 100,
};

interface SkillFormProps {
  skill?: Skill;
  onSubmit: (data: {
    name: string;
    category: SkillCategory;
    proficiency: ProficiencyLevel;
  }) => Promise<void>;
  onClose: () => void;
}

function SkillForm({ skill, onSubmit, onClose }: SkillFormProps) {
  const [name, setName] = useState(skill?.name || "");
  const [category, setCategory] = useState<SkillCategory>(skill?.category || "other");
  const [proficiency, setProficiency] = useState<ProficiencyLevel>(
    skill?.proficiency || "beginner"
  );
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      await onSubmit({ name: name.trim(), category, proficiency });
      onClose();
    } catch (error) {
      console.error("Failed to save skill:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Skill Name</Label>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Python, React, Project Management"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="category">Category</Label>
        <Select value={category} onValueChange={(v) => setCategory(v as SkillCategory)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SKILL_CATEGORIES.map((cat) => (
              <SelectItem key={cat.value} value={cat.value}>
                {cat.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="proficiency">Proficiency Level</Label>
        <Select
          value={proficiency}
          onValueChange={(v) => setProficiency(v as ProficiencyLevel)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROFICIENCY_LEVELS.map((level) => (
              <SelectItem key={level.value} value={level.value}>
                {level.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading || !name.trim()}>
          {loading ? "Saving..." : skill ? "Update" : "Add Skill"}
        </Button>
      </div>
    </form>
  );
}

interface SkillCardProps {
  skill: Skill;
  onEdit: (skill: Skill) => void;
  onDelete: (skillId: string) => void;
}

function SkillCard({ skill, onEdit, onDelete }: SkillCardProps) {
  const proficiencyInfo = PROFICIENCY_LEVELS.find((p) => p.value === skill.proficiency);

  return (
    <div className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate">{skill.name}</span>
          <Badge variant="secondary" className="text-xs">
            {proficiencyInfo?.label}
          </Badge>
        </div>
        <div className="mt-2">
          <Progress
            value={proficiencyToProgress[skill.proficiency]}
            className="h-2"
          />
        </div>
      </div>
      <div className="flex items-center gap-1 ml-4">
        <Button variant="ghost" size="icon" onClick={() => onEdit(skill)}>
          <Pencil className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(skill.id)}
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export function SkillInventory() {
  const {
    skillsGrouped,
    skillSuggestions,
    skillsLoading,
    skillsError,
    fetchSkillsGrouped,
    fetchSkillSuggestions,
    createSkill,
    updateSkill,
    deleteSkill,
  } = useCareerStore();

  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    fetchSkillsGrouped();
    fetchSkillSuggestions();
  }, [fetchSkillsGrouped, fetchSkillSuggestions]);

  const handleAddSkill = async (data: {
    name: string;
    category: SkillCategory;
    proficiency: ProficiencyLevel;
  }) => {
    await createSkill(data);
  };

  const handleUpdateSkill = async (data: {
    name: string;
    category: SkillCategory;
    proficiency: ProficiencyLevel;
  }) => {
    if (editingSkill) {
      await updateSkill(editingSkill.id, data);
    }
  };

  const handleDeleteSkill = async (skillId: string) => {
    if (confirm("Are you sure you want to delete this skill?")) {
      await deleteSkill(skillId);
    }
  };

  const handleAddSuggestion = async (suggestion: { name: string; category: string }) => {
    await createSkill({
      name: suggestion.name,
      category: suggestion.category as SkillCategory,
      proficiency: "beginner",
    });
  };

  if (skillsLoading && !skillsGrouped) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, j) => (
                  <Skeleton key={j} className="h-16 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (skillsError) {
    return (
      <div className="text-center py-8 text-destructive">
        <p>Error loading skills: {skillsError}</p>
        <Button onClick={() => fetchSkillsGrouped()} className="mt-4">
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
          <h2 className="text-xl font-semibold">Skill Inventory</h2>
          <p className="text-sm text-muted-foreground">
            {skillsGrouped?.total_skills || 0} skills tracked
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowSuggestions(!showSuggestions)}
          >
            <Lightbulb className="h-4 w-4 mr-2" />
            Suggestions
          </Button>
          <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Add Skill
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Skill</DialogTitle>
              </DialogHeader>
              <SkillForm
                onSubmit={handleAddSkill}
                onClose={() => setShowAddDialog(false)}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Skill Suggestions */}
      {showSuggestions && skillSuggestions && skillSuggestions.suggestions.length > 0 && (
        <Card className="border-dashed border-2 border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-500" />
              Recommended Skills
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {skillSuggestions.suggestions.map((suggestion, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                  onClick={() => handleAddSuggestion(suggestion)}
                >
                  <Plus className="h-3 w-3 mr-1" />
                  {suggestion.name}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Skills by Category */}
      {skillsGrouped?.groups.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>No skills added yet.</p>
            <p className="text-sm mt-1">Add your first skill to start tracking your expertise!</p>
          </CardContent>
        </Card>
      ) : (
        skillsGrouped?.groups.map((group) => {
          const categoryInfo = SKILL_CATEGORIES.find((c) => c.value === group.category);
          return (
            <Card key={group.category}>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{categoryInfo?.label || group.category}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {group.skills.map((skill) => (
                    <SkillCard
                      key={skill.id}
                      skill={skill}
                      onEdit={setEditingSkill}
                      onDelete={handleDeleteSkill}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          );
        })
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingSkill} onOpenChange={(open) => !open && setEditingSkill(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Skill</DialogTitle>
          </DialogHeader>
          {editingSkill && (
            <SkillForm
              skill={editingSkill}
              onSubmit={handleUpdateSkill}
              onClose={() => setEditingSkill(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
