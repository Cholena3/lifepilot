"use client";

import * as React from "react";
import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useHealthStore } from "@/store/health-store";
import { Share2, Link, Trash2, Ban, Copy, Check, Clock, Eye } from "lucide-react";

export function HealthShareList() {
  const {
    healthShares,
    healthRecords,
    isLoading,
    isSubmitting,
    fetchHealthShares,
    fetchHealthRecords,
    createHealthShare,
    revokeHealthShare,
    deleteHealthShare,
  } = useHealthStore();

  const [isDialogOpen, setIsDialogOpen] = React.useState(false);
  const [selectedRecords, setSelectedRecords] = React.useState<string[]>([]);
  const [doctorName, setDoctorName] = React.useState("");
  const [doctorEmail, setDoctorEmail] = React.useState("");
  const [purpose, setPurpose] = React.useState("");
  const [expiresInHours, setExpiresInHours] = React.useState(72);
  const [notes, setNotes] = React.useState("");
  const [copiedId, setCopiedId] = React.useState<string | null>(null);

  useEffect(() => {
    fetchHealthShares();
    fetchHealthRecords();
  }, [fetchHealthShares, fetchHealthRecords]);

  const handleCreateShare = async () => {
    if (selectedRecords.length === 0) return;

    try {
      await createHealthShare({
        record_ids: selectedRecords,
        doctor_name: doctorName || undefined,
        doctor_email: doctorEmail || undefined,
        purpose: purpose || undefined,
        expires_in_hours: expiresInHours,
        notes: notes || undefined,
      });
      setIsDialogOpen(false);
      resetForm();
    } catch (error) {
      // Error is handled by the store
    }
  };

  const resetForm = () => {
    setSelectedRecords([]);
    setDoctorName("");
    setDoctorEmail("");
    setPurpose("");
    setExpiresInHours(72);
    setNotes("");
  };

  const toggleRecord = (recordId: string) => {
    if (selectedRecords.includes(recordId)) {
      setSelectedRecords(selectedRecords.filter((id) => id !== recordId));
    } else {
      setSelectedRecords([...selectedRecords, recordId]);
    }
  };

  const copyShareLink = async (token: string, shareId: string) => {
    const url = `${window.location.origin}/health/shared/${token}`;
    await navigator.clipboard.writeText(url);
    setCopiedId(shareId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const getStatusBadge = (share: typeof healthShares[0]) => {
    if (share.is_revoked) {
      return <Badge variant="destructive">Revoked</Badge>;
    }
    if (share.is_expired) {
      return <Badge variant="secondary">Expired</Badge>;
    }
    return <Badge variant="default">Active</Badge>;
  };

  return (
    <div className="space-y-4">
      {/* Create Share Button */}
      <Card>
        <CardContent className="pt-4">
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="w-full">
                <Share2 className="h-4 w-4 mr-2" />
                Share Records with Doctor
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create Share Link</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-4">
                {/* Select Records */}
                <div className="space-y-2">
                  <Label>Select Records to Share *</Label>
                  <div className="border rounded-lg max-h-48 overflow-y-auto p-2 space-y-2">
                    {healthRecords.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No health records available
                      </p>
                    ) : (
                      healthRecords.map((record) => (
                        <div
                          key={record.id}
                          className="flex items-center gap-2 p-2 hover:bg-muted rounded"
                        >
                          <Checkbox
                            id={record.id}
                            checked={selectedRecords.includes(record.id)}
                            onCheckedChange={() => toggleRecord(record.id)}
                          />
                          <Label
                            htmlFor={record.id}
                            className="flex-1 cursor-pointer font-normal"
                          >
                            <span className="font-medium">{record.title}</span>
                            <span className="text-muted-foreground ml-2">
                              ({record.category})
                            </span>
                          </Label>
                        </div>
                      ))
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {selectedRecords.length} record(s) selected
                  </p>
                </div>

                {/* Doctor Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="doctorName">Doctor Name</Label>
                    <Input
                      id="doctorName"
                      placeholder="Dr. Smith"
                      value={doctorName}
                      onChange={(e) => setDoctorName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="doctorEmail">Doctor Email</Label>
                    <Input
                      id="doctorEmail"
                      type="email"
                      placeholder="doctor@hospital.com"
                      value={doctorEmail}
                      onChange={(e) => setDoctorEmail(e.target.value)}
                    />
                  </div>
                </div>

                {/* Purpose */}
                <div className="space-y-2">
                  <Label htmlFor="purpose">Purpose</Label>
                  <Input
                    id="purpose"
                    placeholder="e.g., Consultation, Second Opinion"
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value)}
                  />
                </div>

                {/* Expiry */}
                <div className="space-y-2">
                  <Label htmlFor="expiresInHours">Link Expires In (hours)</Label>
                  <Input
                    id="expiresInHours"
                    type="number"
                    min={1}
                    max={720}
                    value={expiresInHours}
                    onChange={(e) => setExpiresInHours(parseInt(e.target.value) || 72)}
                  />
                  <p className="text-sm text-muted-foreground">
                    Maximum 30 days (720 hours)
                  </p>
                </div>

                {/* Notes */}
                <div className="space-y-2">
                  <Label htmlFor="notes">Notes for Doctor</Label>
                  <Textarea
                    id="notes"
                    placeholder="Any additional information..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                  />
                </div>

                <Button
                  onClick={handleCreateShare}
                  disabled={isSubmitting || selectedRecords.length === 0}
                  className="w-full"
                >
                  {isSubmitting ? "Creating..." : "Create Share Link"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>

      {/* Shares List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Share Links</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : healthShares.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              No share links created yet
            </p>
          ) : (
            <div className="space-y-4">
              {healthShares.map((share) => (
                <div key={share.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Link className="h-4 w-4 text-muted-foreground" />
                        {share.doctor_name ? (
                          <span className="font-medium">
                            Shared with {share.doctor_name}
                          </span>
                        ) : (
                          <span className="font-medium">Share Link</span>
                        )}
                        {getStatusBadge(share)}
                      </div>
                      {share.purpose && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Purpose: {share.purpose}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      {share.is_valid && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => copyShareLink(share.public_token, share.id)}
                        >
                          {copiedId === share.id ? (
                            <Check className="h-4 w-4 mr-1" />
                          ) : (
                            <Copy className="h-4 w-4 mr-1" />
                          )}
                          {copiedId === share.id ? "Copied!" : "Copy Link"}
                        </Button>
                      )}
                      {share.is_valid && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => revokeHealthShare(share.id)}
                        >
                          <Ban className="h-4 w-4 mr-1" />
                          Revoke
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteHealthShare(share.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Expires: {formatDate(share.expires_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="h-3 w-3" />
                      Accessed: {share.access_count} times
                    </span>
                    <span>Records: {share.record_ids.length}</span>
                  </div>

                  {share.last_accessed_at && (
                    <p className="text-xs text-muted-foreground">
                      Last accessed: {formatDate(share.last_accessed_at)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
