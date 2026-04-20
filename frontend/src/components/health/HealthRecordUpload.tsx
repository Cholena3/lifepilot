"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useHealthStore } from "@/store/health-store";
import { HEALTH_RECORD_CATEGORIES } from "@/lib/api/health";
import { Upload, X } from "lucide-react";

const uploadSchema = z.object({
  title: z.string().min(1, "Title is required"),
  category: z.string().min(1, "Category is required"),
  family_member_id: z.string().optional(),
  record_date: z.string().optional(),
  doctor_name: z.string().optional(),
  hospital_name: z.string().optional(),
  notes: z.string().optional(),
});

type UploadFormData = z.infer<typeof uploadSchema>;

interface HealthRecordUploadProps {
  onSuccess?: () => void;
}

export function HealthRecordUpload({ onSuccess }: HealthRecordUploadProps) {
  const { familyMembers, isSubmitting, uploadHealthRecord, fetchFamilyMembers } =
    useHealthStore();
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    fetchFamilyMembers();
  }, [fetchFamilyMembers]);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<UploadFormData>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      category: "",
      family_member_id: "",
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onSubmit = async (data: UploadFormData) => {
    if (!selectedFile) {
      return;
    }

    try {
      await uploadHealthRecord(selectedFile, {
        title: data.title,
        category: data.category,
        family_member_id: data.family_member_id || undefined,
        record_date: data.record_date || undefined,
        doctor_name: data.doctor_name || undefined,
        hospital_name: data.hospital_name || undefined,
        notes: data.notes || undefined,
      });
      reset();
      setSelectedFile(null);
      onSuccess?.();
    } catch (error) {
      // Error is handled by the store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Health Record</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* File Upload */}
          <div
            className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors"
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept="image/*,.pdf"
              onChange={handleFileChange}
            />
            {selectedFile ? (
              <div className="flex items-center justify-center gap-2">
                <span className="text-sm">{selectedFile.name}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Click or drag file to upload
                </p>
                <p className="text-xs text-muted-foreground">
                  Supports images and PDF files
                </p>
              </div>
            )}
          </div>

          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              placeholder="e.g., Blood Test Report - March 2024"
              {...register("title")}
            />
            {errors.title && (
              <p className="text-sm text-destructive">{errors.title.message}</p>
            )}
          </div>

          {/* Category */}
          <div className="space-y-2">
            <Label>Category *</Label>
            <Select
              value={watch("category")}
              onValueChange={(value) => setValue("category", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {HEALTH_RECORD_CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category && (
              <p className="text-sm text-destructive">{errors.category.message}</p>
            )}
          </div>

          {/* Family Member */}
          <div className="space-y-2">
            <Label>Family Member</Label>
            <Select
              value={watch("family_member_id") || ""}
              onValueChange={(value) => setValue("family_member_id", value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Self (default)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Self</SelectItem>
                {familyMembers.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.name} ({member.relationship})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Record Date */}
          <div className="space-y-2">
            <Label htmlFor="record_date">Record Date</Label>
            <Input id="record_date" type="date" {...register("record_date")} />
          </div>

          {/* Doctor Name */}
          <div className="space-y-2">
            <Label htmlFor="doctor_name">Doctor Name</Label>
            <Input
              id="doctor_name"
              placeholder="Dr. Smith"
              {...register("doctor_name")}
            />
          </div>

          {/* Hospital Name */}
          <div className="space-y-2">
            <Label htmlFor="hospital_name">Hospital/Clinic</Label>
            <Input
              id="hospital_name"
              placeholder="City Hospital"
              {...register("hospital_name")}
            />
          </div>

          {/* Notes */}
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              placeholder="Any additional notes..."
              {...register("notes")}
            />
          </div>

          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting || !selectedFile}
          >
            {isSubmitting ? "Uploading..." : "Upload Record"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
