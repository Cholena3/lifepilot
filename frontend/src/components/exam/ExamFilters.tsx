"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Search, Filter, X } from "lucide-react";
import {
  ExamFilters as ExamFiltersType,
  ExamType,
  EXAM_TYPES,
  COMMON_DEGREES,
  COMMON_BRANCHES,
} from "@/lib/api/exam";

interface ExamFiltersProps {
  filters: ExamFiltersType;
  onFiltersChange: (filters: ExamFiltersType) => void;
  onApply: () => void;
  onClear: () => void;
}

export function ExamFilters({
  filters,
  onFiltersChange,
  onApply,
  onClear,
}: ExamFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleChange = (key: keyof ExamFiltersType, value: unknown) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const hasActiveFilters =
    filters.exam_type ||
    filters.degree ||
    filters.branch ||
    filters.cgpa !== undefined ||
    filters.backlogs !== undefined ||
    filters.search;

  return (
    <Card>
      <CardContent className="pt-4">
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search exams by name or organization..."
              value={filters.search || ""}
              onChange={(e) => handleChange("search", e.target.value || undefined)}
              className="pl-10"
            />
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <Select
                value={filters.exam_type || "all"}
                onValueChange={(v) =>
                  handleChange("exam_type", v === "all" ? undefined : (v as ExamType))
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Exam Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Exam Types</SelectItem>
                  {EXAM_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="upcoming"
                checked={filters.upcoming_only ?? true}
                onCheckedChange={(checked) => handleChange("upcoming_only", checked)}
              />
              <Label htmlFor="upcoming" className="text-sm cursor-pointer">
                Upcoming only
              </Label>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              <Filter className="h-4 w-4 mr-2" />
              {showAdvanced ? "Hide" : "More"} Filters
            </Button>

            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={onClear}>
                <X className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>

          {/* Advanced Filters */}
          {showAdvanced && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t">
              <div className="space-y-2">
                <Label>Degree</Label>
                <Select
                  value={filters.degree || "all"}
                  onValueChange={(v) =>
                    handleChange("degree", v === "all" ? undefined : v)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select degree" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Degrees</SelectItem>
                    {COMMON_DEGREES.map((degree) => (
                      <SelectItem key={degree} value={degree}>
                        {degree}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Branch</Label>
                <Select
                  value={filters.branch || "all"}
                  onValueChange={(v) =>
                    handleChange("branch", v === "all" ? undefined : v)
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select branch" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Branches</SelectItem>
                    {COMMON_BRANCHES.map((branch) => (
                      <SelectItem key={branch} value={branch}>
                        {branch}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>CGPA (Your CGPA)</Label>
                <Input
                  type="number"
                  min="0"
                  max="10"
                  step="0.1"
                  placeholder="e.g., 7.5"
                  value={filters.cgpa ?? ""}
                  onChange={(e) =>
                    handleChange(
                      "cgpa",
                      e.target.value ? parseFloat(e.target.value) : undefined
                    )
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>Backlogs (Your count)</Label>
                <Input
                  type="number"
                  min="0"
                  placeholder="e.g., 0"
                  value={filters.backlogs ?? ""}
                  onChange={(e) =>
                    handleChange(
                      "backlogs",
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                />
              </div>
            </div>
          )}

          {/* Apply Button */}
          <div className="flex justify-end">
            <Button onClick={onApply}>Apply Filters</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
