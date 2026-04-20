"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  shareLinkCreateSchema,
  type ShareLinkCreateFormData,
} from "@/lib/validations/documents";
import { useDocumentStore } from "@/store/document-store";
import type { Document } from "@/lib/api/documents";
import { cn } from "@/lib/utils";

interface ShareLinkManagerProps {
  document: Document;
}

export function ShareLinkManager({ document }: ShareLinkManagerProps) {
  const [showCreateDialog, setShowCreateDialog] = React.useState(false);
  const [showQRDialog, setShowQRDialog] = React.useState(false);
  const [copiedUrl, setCopiedUrl] = React.useState(false);

  const {
    shareLinks,
    currentShareLinkResponse,
    isLoading,
    fetchShareLinks,
    createShareLink,
    revokeShareLink,
    clearShareLinkResponse,
  } = useDocumentStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<ShareLinkCreateFormData>({
    resolver: zodResolver(shareLinkCreateSchema),
    defaultValues: {
      expiresInHours: 24,
      password: null,
    },
  });

  React.useEffect(() => {
    fetchShareLinks(document.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [document.id]);

  const onSubmit = async (data: ShareLinkCreateFormData) => {
    try {
      await createShareLink(document.id, {
        expires_in_hours: data.expiresInHours,
        password: data.password || null,
      });
      setShowCreateDialog(false);
      setShowQRDialog(true);
      reset();
    } catch {
      // Error handled by store
    }
  };

  const handleCopyUrl = async () => {
    if (currentShareLinkResponse?.share_url) {
      await navigator.clipboard.writeText(currentShareLinkResponse.share_url);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    }
  };

  const handleRevoke = async (linkId: string) => {
    if (confirm("Are you sure you want to revoke this share link?")) {
      await revokeShareLink(document.id, linkId);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const isExpired = (expiresAt: string) => {
    return new Date(expiresAt) < new Date();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Share Links</h3>
        <Button size="sm" onClick={() => setShowCreateDialog(true)}>
          Create Share Link
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
        </div>
      ) : shareLinks.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No share links created yet.
        </p>
      ) : (
        <div className="space-y-2">
          {shareLinks.map((link) => (
            <Card key={link.id}>
              <CardContent className="p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-muted px-2 py-1 rounded truncate max-w-[200px]">
                        {link.link_token}
                      </code>
                      {link.has_password && (
                        <Badge variant="secondary">Password Protected</Badge>
                      )}
                      {link.is_revoked ? (
                        <Badge variant="destructive">Revoked</Badge>
                      ) : isExpired(link.expires_at) ? (
                        <Badge variant="expired">Expired</Badge>
                      ) : (
                        <Badge variant="default">Active</Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Expires: {formatDate(link.expires_at)} • {link.access_count} access
                      {link.access_count !== 1 ? "es" : ""}
                    </p>
                  </div>
                  {!link.is_revoked && !isExpired(link.expires_at) && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleRevoke(link.id)}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Share Link Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Share Link</DialogTitle>
            <DialogDescription>
              Generate a temporary link to share this document.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="expiresInHours">Link Expires In (hours)</Label>
              <Input
                id="expiresInHours"
                type="number"
                min={1}
                max={720}
                {...register("expiresInHours", { valueAsNumber: true })}
                className={cn(errors.expiresInHours && "border-destructive")}
              />
              {errors.expiresInHours && (
                <p className="text-sm text-destructive">
                  {errors.expiresInHours.message}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                Maximum: 720 hours (30 days)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password (Optional)</Label>
              <Input
                id="password"
                type="password"
                placeholder="Leave empty for no password"
                {...register("password")}
                className={cn(errors.password && "border-destructive")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? "Creating..." : "Create Link"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* QR Code Dialog */}
      <Dialog
        open={showQRDialog}
        onOpenChange={(open) => {
          setShowQRDialog(open);
          if (!open) clearShareLinkResponse();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Share Link Created</DialogTitle>
            <DialogDescription>
              Share this link or scan the QR code to access the document.
            </DialogDescription>
          </DialogHeader>

          {currentShareLinkResponse && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={currentShareLinkResponse.share_url}
                  className="flex-1"
                />
                <Button onClick={handleCopyUrl}>
                  {copiedUrl ? "Copied!" : "Copy"}
                </Button>
              </div>

              <div className="flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={currentShareLinkResponse.qr_code_data_url}
                  alt="QR Code for share link"
                  className="w-48 h-48 border rounded-md"
                />
              </div>

              {currentShareLinkResponse.share_link.has_password && (
                <p className="text-sm text-muted-foreground text-center">
                  This link is password protected. Share the password separately.
                </p>
              )}
            </div>
          )}

          <DialogFooter>
            <Button onClick={() => setShowQRDialog(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
