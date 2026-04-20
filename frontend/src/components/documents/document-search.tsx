"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useDocumentStore } from "@/store/document-store";
import type { Document } from "@/lib/api/documents";
import type { DocumentCategory } from "@/lib/validations/documents";

interface DocumentSearchProps {
  onSelectDocument: (document: Document) => void;
}

export function DocumentSearch({ onSelectDocument }: DocumentSearchProps) {
  const [query, setQuery] = React.useState("");
  const { searchDocuments, searchResults, searchQuery, isSearching, clearSearch } =
    useDocumentStore();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      searchDocuments(query);
    }
  };

  const handleClear = () => {
    setQuery("");
    clearSearch();
  };

  const getCategoryBadgeVariant = (category: DocumentCategory) => {
    const variants: Record<DocumentCategory, "identity" | "education" | "career" | "finance"> = {
      identity: "identity",
      education: "education",
      career: "career",
      finance: "finance",
    };
    return variants[category];
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
      <form onSubmit={handleSearch} className="flex gap-2">
        <Input
          type="search"
          placeholder="Search documents by title or content..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" disabled={isSearching || !query.trim()}>
          {isSearching ? "Searching..." : "Search"}
        </Button>
        {searchQuery && (
          <Button type="button" variant="outline" onClick={handleClear}>
            Clear
          </Button>
        )}
      </form>

      {searchQuery && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {searchResults.length} result{searchResults.length !== 1 ? "s" : ""} for &quot;{searchQuery}&quot;
          </p>

          {searchResults.length === 0 ? (
            <Card>
              <CardContent className="py-6 text-center text-muted-foreground">
                No documents found matching your search.
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {searchResults.map((doc) => (
                <Card
                  key={doc.id}
                  className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => onSelectDocument(doc)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium truncate">{doc.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {formatDate(doc.created_at)}
                        </p>
                        {doc.ocr_text && (
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {doc.ocr_text.substring(0, 150)}...
                          </p>
                        )}
                      </div>
                      <Badge variant={getCategoryBadgeVariant(doc.category)}>
                        {doc.category}
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
