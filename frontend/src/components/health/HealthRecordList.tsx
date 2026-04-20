"use client";

import * as React from "react";
import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { useHealthStore } from "@/store/health-store";
import { HEALTH_RECORD_CATEGORIES } from "@/lib/api/health";
import { FileText, Trash2, Search, Calendar, User } from "lucide-react";

export function HealthRecordList() {
  const {
    healthRecords,
    familyMembers,
    recordFilters,
    recordPagination,
    isLoading,
    fetchHealthRecords,
    fetchFamilyMembers,
    deleteHealthRecord,
    setRecordFilters,
    searchHealthRecords,
  } = useHealthStore();

  const [searchQuery, setSearchQuery] = React.useState("");

  useEffect(() => {
    fetchHealthRecords();
    fetchFamilyMembers();
  }, [fetchHealthRecords, fetchFamilyMembers]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchHealthRecords(searchQuery);
    } else {
      fetchHealthRecords();
    }
  };

  const handleCategoryChange = (value: string) => {
    setRecordFilters({
      ...recordFilters,
      category: value === "all" ? undefined : value,
    });
  };

  const handleFamilyMemberChange = (value: string) => {
    setRecordFilters({
      ...recordFilters,
      family_member_id: value === "all" ? undefined : value,
    });
  };

  const getCategoryLabel = (category: string) => {
    return HEALTH_RECORD_CATEGORIES.find((c) => c.value === category)?.label || category;
  };

  const getFamilyMemberName = (memberId: string | null) => {
    if (!memberId) return "Self";
    const member = familyMembers.find((m) => m.id === memberId);
    return member?.name || "Unknown";
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4">
            <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search records..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </form>

            <Select
              value={recordFilters.category || "all"}
              onValueChange={handleCategoryChange}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {HEALTH_RECORD_CATEGORIES.map((cat) => (
                  <SelectItem key={cat.value} value={cat.value}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={recordFilters.family_member_id || "all"}
              onValueChange={handleFamilyMemberChange}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Family Member" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Members</SelectItem>
                <SelectItem value="self">Self</SelectItem>
                {familyMembers.map((member) => (
                  <SelectItem key={member.id} value={member.id}>
                    {member.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Records List */}
      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : healthRecords.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No health records found. Upload your first record to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {healthRecords.map((record) => (
            <Card key={record.id}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <FileText className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-medium">{record.title}</h3>
                      <div className="flex flex-wrap gap-2 mt-1">
                        <Badge variant="secondary">
                          {getCategoryLabel(record.category)}
                        </Badge>
                        <span className="text-sm text-muted-foreground flex items-center gap-1">
                          <User className="h-3 w-3" />
                          {getFamilyMemberName(record.family_member_id)}
                        </span>
                        {record.record_date && (
                          <span className="text-sm text-muted-foreground flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(record.record_date)}
                          </span>
                        )}
                      </div>
                      {record.doctor_name && (
                        <p className="text-sm text-muted-foreground mt-1">
                          Dr. {record.doctor_name}
                          {record.hospital_name && ` • ${record.hospital_name}`}
                        </p>
                      )}
                      {record.notes && (
                        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                          {record.notes}
                        </p>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteHealthRecord(record.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {recordPagination.totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={recordPagination.page <= 1}
            onClick={() => useHealthStore.getState().setRecordPage(recordPagination.page - 1)}
          >
            Previous
          </Button>
          <span className="flex items-center px-4 text-sm text-muted-foreground">
            Page {recordPagination.page} of {recordPagination.totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={recordPagination.page >= recordPagination.totalPages}
            onClick={() => useHealthStore.getState().setRecordPage(recordPagination.page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
