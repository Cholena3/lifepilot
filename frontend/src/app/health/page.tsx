"use client";

import * as React from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  HealthRecordList,
  HealthRecordUpload,
  MedicineList,
  MedicineForm,
  VitalsList,
  VitalForm,
  EmergencyInfoCard,
  HealthShareList,
} from "@/components/health";
import { useAuthStore } from "@/store/auth-store";
import { useHealthStore } from "@/store/health-store";

export default function HealthPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const { error, clearError } = useHealthStore();
  const [activeTab, setActiveTab] = React.useState("records");
  const [showUploadForm, setShowUploadForm] = React.useState(false);
  const [showMedicineForm, setShowMedicineForm] = React.useState(false);
  const [showVitalForm, setShowVitalForm] = React.useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
    }
  }, [isAuthenticated, router]);

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
            <span className="font-medium">Health</span>
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

        <div className="mb-8">
          <h1 className="text-3xl font-bold">Health Manager</h1>
          <p className="text-muted-foreground mt-2">
            Manage health records, track medicines, monitor vitals, and store emergency info
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 flex-wrap">
            <TabsTrigger value="records">Records</TabsTrigger>
            <TabsTrigger value="medicines">Medicines</TabsTrigger>
            <TabsTrigger value="vitals">Vitals</TabsTrigger>
            <TabsTrigger value="emergency">Emergency</TabsTrigger>
            <TabsTrigger value="sharing">Sharing</TabsTrigger>
          </TabsList>

          {/* Health Records Tab */}
          <TabsContent value="records">
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button onClick={() => setShowUploadForm(!showUploadForm)}>
                  {showUploadForm ? "Hide Form" : "Upload Record"}
                </Button>
              </div>
              {showUploadForm && (
                <div className="max-w-xl">
                  <HealthRecordUpload
                    onSuccess={() => setShowUploadForm(false)}
                  />
                </div>
              )}
              <HealthRecordList />
            </div>
          </TabsContent>

          {/* Medicines Tab */}
          <TabsContent value="medicines">
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button onClick={() => setShowMedicineForm(!showMedicineForm)}>
                  {showMedicineForm ? "Hide Form" : "Add Medicine"}
                </Button>
              </div>
              {showMedicineForm && (
                <div className="max-w-xl">
                  <MedicineForm onSuccess={() => setShowMedicineForm(false)} />
                </div>
              )}
              <MedicineList />
            </div>
          </TabsContent>

          {/* Vitals Tab */}
          <TabsContent value="vitals">
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button onClick={() => setShowVitalForm(!showVitalForm)}>
                  {showVitalForm ? "Hide Form" : "Record Vital"}
                </Button>
              </div>
              <div className="grid gap-4 lg:grid-cols-3">
                {showVitalForm && (
                  <div className="lg:col-span-1">
                    <VitalForm onSuccess={() => setShowVitalForm(false)} />
                  </div>
                )}
                <div className={showVitalForm ? "lg:col-span-2" : "lg:col-span-3"}>
                  <VitalsList />
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Emergency Info Tab */}
          <TabsContent value="emergency">
            <div className="max-w-2xl">
              <EmergencyInfoCard />
            </div>
          </TabsContent>

          {/* Sharing Tab */}
          <TabsContent value="sharing">
            <HealthShareList />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
