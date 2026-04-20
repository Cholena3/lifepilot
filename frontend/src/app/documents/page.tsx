"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DocumentUpload,
  DocumentList,
  DocumentSearch,
  DocumentDetail,
} from "@/components/documents";
import { useAuthStore } from "@/store/auth-store";
import { useDocumentStore } from "@/store/document-store";
import type { Document } from "@/lib/api/documents";

export default function DocumentsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { selectedDocument, selectDocument, error, clearError } =
    useDocumentStore();
  const [activeTab, setActiveTab] = React.useState("browse");

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

  const handleSelectDocument = (document: Document) => {
    selectDocument(document);
  };

  const handleCloseDetail = () => {
    selectDocument(null);
  };

  const handleUploadSuccess = () => {
    setActiveTab("browse");
  };

  if (!isAuthenticated || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-2xl font-bold text-primary">
              LifePilot
            </Link>
            <span className="text-muted-foreground">/</span>
            <span className="font-medium">Document Vault</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user.email}</span>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {error && (
          <Card className="mb-4 border-destructive bg-destructive/10">
            <CardContent className="py-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-destructive">{error}</p>
                <Button variant="ghost" size="sm" onClick={clearError}>
                  Dismiss
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {selectedDocument ? (
          <DocumentDetail
            document={selectedDocument}
            onClose={handleCloseDetail}
          />
        ) : (
          <>
            <div className="mb-8">
              <h1 className="text-3xl font-bold">Document Vault</h1>
              <p className="text-muted-foreground mt-2">
                Securely store, organize, and share your important documents
              </p>
            </div>

            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-6">
                <TabsTrigger value="browse">Browse</TabsTrigger>
                <TabsTrigger value="search">Search</TabsTrigger>
                <TabsTrigger value="upload">Upload</TabsTrigger>
              </TabsList>

              <TabsContent value="browse">
                <DocumentList onSelectDocument={handleSelectDocument} />
              </TabsContent>

              <TabsContent value="search">
                <Card>
                  <CardHeader>
                    <CardTitle>Search Documents</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <DocumentSearch onSelectDocument={handleSelectDocument} />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="upload">
                <div className="max-w-xl">
                  <DocumentUpload onSuccess={handleUploadSuccess} />
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </main>
    </div>
  );
}
