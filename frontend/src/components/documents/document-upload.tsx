"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  documentUploadSchema,
  type DocumentUploadFormData,
  DOCUMENT_CATEGORIES,
} from "@/lib/validations/documents";
import { useDocumentStore } from "@/store/document-store";
import { cn } from "@/lib/utils";

interface DocumentUploadProps {
  onSuccess?: () => void;
}

export function DocumentUpload({ onSuccess }: DocumentUploadProps) {
  const [uploadTab, setUploadTab] = React.useState("file");
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [cameraStream, setCameraStream] = React.useState<MediaStream | null>(null);
  const [capturedImage, setCapturedImage] = React.useState<string | null>(null);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);

  const { uploadDocument, uploadCameraCapture, isUploading, error } =
    useDocumentStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<DocumentUploadFormData>({
    resolver: zodResolver(documentUploadSchema),
    defaultValues: {
      title: "",
      category: "identity",
      expiryDate: null,
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      setCameraStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error("Failed to access camera:", err);
    }
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach((track) => track.stop());
      setCameraStream(null);
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.drawImage(video, 0, 0);
        const imageData = canvas.toDataURL("image/jpeg", 0.8);
        setCapturedImage(imageData);
        stopCamera();
      }
    }
  };

  const retakePhoto = () => {
    setCapturedImage(null);
    startCamera();
  };

  React.useEffect(() => {
    if (uploadTab === "camera" && !capturedImage) {
      startCamera();
    } else {
      stopCamera();
    }
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uploadTab]);

  const onSubmit = async (data: DocumentUploadFormData) => {
    try {
      const metadata = {
        title: data.title,
        category: data.category,
        expiry_date: data.expiryDate || undefined,
      };

      if (uploadTab === "file" && selectedFile) {
        await uploadDocument(selectedFile, metadata);
      } else if (uploadTab === "camera" && capturedImage) {
        await uploadCameraCapture(capturedImage, metadata);
      } else {
        return;
      }

      reset();
      setSelectedFile(null);
      setCapturedImage(null);
      onSuccess?.();
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Document</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={uploadTab} onValueChange={setUploadTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="file">File Upload</TabsTrigger>
            <TabsTrigger value="camera">Camera Capture</TabsTrigger>
          </TabsList>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-4 space-y-4">
            <TabsContent value="file">
              <div className="space-y-2">
                <Label htmlFor="file">Select File</Label>
                <Input
                  id="file"
                  type="file"
                  accept="image/*,.pdf,.doc,.docx"
                  onChange={handleFileChange}
                  className="cursor-pointer"
                />
                {selectedFile && (
                  <p className="text-sm text-muted-foreground">
                    Selected: {selectedFile.name} (
                    {(selectedFile.size / 1024).toFixed(1)} KB)
                  </p>
                )}
              </div>
            </TabsContent>

            <TabsContent value="camera">
              <div className="space-y-2">
                {!capturedImage ? (
                  <>
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      className="w-full rounded-md bg-muted"
                    />
                    <Button
                      type="button"
                      onClick={capturePhoto}
                      disabled={!cameraStream}
                      className="w-full"
                    >
                      Capture Photo
                    </Button>
                  </>
                ) : (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={capturedImage}
                      alt="Captured document"
                      className="w-full rounded-md"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={retakePhoto}
                      className="w-full"
                    >
                      Retake Photo
                    </Button>
                  </>
                )}
                <canvas ref={canvasRef} className="hidden" />
              </div>
            </TabsContent>

            <div className="space-y-2">
              <Label htmlFor="title">Document Title</Label>
              <Input
                id="title"
                placeholder="Enter document title"
                {...register("title")}
                className={cn(errors.title && "border-destructive")}
              />
              {errors.title && (
                <p className="text-sm text-destructive">{errors.title.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <Select id="category" {...register("category")}>
                {DOCUMENT_CATEGORIES.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </Select>
              {errors.category && (
                <p className="text-sm text-destructive">{errors.category.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="expiryDate">Expiry Date (Optional)</Label>
              <Input
                id="expiryDate"
                type="date"
                {...register("expiryDate")}
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={
                isUploading ||
                (uploadTab === "file" && !selectedFile) ||
                (uploadTab === "camera" && !capturedImage)
              }
            >
              {isUploading ? "Uploading..." : "Upload Document"}
            </Button>
          </form>
        </Tabs>
      </CardContent>
    </Card>
  );
}
