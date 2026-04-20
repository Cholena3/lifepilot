"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useDocumentStore } from "@/store/document-store";
import { DOCUMENT_CATEGORIES, type DocumentCategory } from "@/lib/validations/documents";
import type { Document } from "@/lib/api/documents";

interface DocumentListProps {
  onSelectDocument: (document: Document) => void;
}

export function DocumentList({ onSelectDocument }: DocumentListProps) {
  const {
    documents,
    isLoading,
    pagination,
    filters,
    setCategoryFilter,
    setPage,
    fetchDocuments,
  } = useDocumentStore();

  React.useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-4">
      {/* Category Filter */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={!filters.category ? "default" : "outline"}
          size="sm"
          onClick={() => setCategoryFilter(undefined)}
        >
          All
        </Button>
        {DOCUMENT_CATEGORIES.map((cat) => (
          <Button
            key={cat.value}
            variant={filters.category === cat.value ? "default" : "outline"}
            size="sm"
            onClick={() => setCategoryFilter(cat.value)}
          >
            {cat.label}
          </Button>
        ))}
      </div>

      {/* Document Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : documents.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No documents found. Upload your first document to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => onSelectDocument(doc)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">{doc.title}</h3>
                    <p className="text-sm text-muted-foreground">
                      {formatFileSize(doc.file_size)} • {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1 items-end">
                    <Badge variant={getCategoryBadgeVariant(doc.category)}>
                      {doc.category}
                    </Badge>
                    {doc.is_expired && (
                      <Badge variant="expired">Expired</Badge>
                    )}
                  </div>
                </div>
                {doc.expiry_date && !doc.is_expired && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Expires: {formatDate(doc.expiry_date)}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(pagination.page - 1)}
            disabled={pagination.page <= 1}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {pagination.page} of {pagination.totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(pagination.page + 1)}
            disabled={pagination.page >= pagination.totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
