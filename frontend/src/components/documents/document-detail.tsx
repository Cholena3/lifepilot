"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ShareLinkManager } from "./share-link-manager";
import { useDocumentStore } from "@/store/document-store";
import { documentsApi, type Document } from "@/lib/api/documents";
import type { DocumentCategory } from "@/lib/validations/documents";

interface DocumentDetailProps {
  document: Document;
  onClose: () => void;
}

export function DocumentDetail({ document, onClose }: DocumentDetailProps) {
  const { deleteDocument, isLoading } = useDocumentStore();
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false);

  const getCategoryBadgeVariant = (category: DocumentCategory) => {
    const variants: Record<DocumentCategory, "identity" | "education" | "career" | "finance"> = {
      identity: "identity",
      education: "education",
      career: "career",
      finance: "finance",
    };
    return variants[category];
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleDownload = () => {
    const url = documentsApi.getDocumentDownloadUrl(document.id);
    window.open(url, "_blank");
  };

  const handleDelete = async () => {
    try {
      await deleteDocument(document.id);
      onClose();
    } catch {
      // Error handled by store
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={onClose}>
          ← Back to Documents
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="text-xl">{document.title}</CardTitle>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant={getCategoryBadgeVariant(document.category)}>
                  {document.category}
                </Badge>
                {document.is_expired && (
                  <Badge variant="expired">Expired</Badge>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleDownload}>Download</Button>
              <Button
                variant="destructive"
                onClick={() => setShowDeleteConfirm(true)}
              >
                Delete
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">File Size</p>
              <p className="font-medium">{formatFileSize(document.file_size)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Content Type</p>
              <p className="font-medium">{document.content_type}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Uploaded</p>
              <p className="font-medium">{formatDate(document.created_at)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Last Updated</p>
              <p className="font-medium">{formatDate(document.updated_at)}</p>
            </div>
            {document.expiry_date && (
              <div>
                <p className="text-muted-foreground">Expiry Date</p>
                <p className="font-medium">
                  {formatDate(document.expiry_date)}
                </p>
              </div>
            )}
          </div>

          {document.ocr_text && (
            <div>
              <p className="text-muted-foreground text-sm mb-2">
                Extracted Text (OCR)
              </p>
              <div className="bg-muted p-3 rounded-md text-sm max-h-40 overflow-y-auto">
                {document.ocr_text}
              </div>
            </div>
          )}

          {document.extracted_fields &&
            Object.keys(document.extracted_fields).length > 0 && (
              <div>
                <p className="text-muted-foreground text-sm mb-2">
                  Extracted Fields
                </p>
                <div className="bg-muted p-3 rounded-md text-sm">
                  <dl className="grid grid-cols-2 gap-2">
                    {Object.entries(document.extracted_fields).map(
                      ([key, value]) => (
                        <React.Fragment key={key}>
                          <dt className="text-muted-foreground capitalize">
                            {key.replace(/_/g, " ")}
                          </dt>
                          <dd className="font-medium">{String(value)}</dd>
                        </React.Fragment>
                      )
                    )}
                  </dl>
                </div>
              </div>
            )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Sharing</CardTitle>
        </CardHeader>
        <CardContent>
          <ShareLinkManager document={document} />
        </CardContent>
      </Card>

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setShowDeleteConfirm(false)}
          />
          <Card className="relative z-50 w-full max-w-md">
            <CardHeader>
              <CardTitle>Delete Document</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p>
                Are you sure you want to delete &quot;{document.title}&quot;? This action
                cannot be undone.
              </p>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={isLoading}
                >
                  {isLoading ? "Deleting..." : "Delete"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
