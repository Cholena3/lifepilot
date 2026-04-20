"use client";

import * as React from "react";
import { useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useHealthStore } from "@/store/health-store";
import { Pill, Clock, Trash2, Check, X, AlertTriangle } from "lucide-react";

export function MedicineList() {
  const {
    medicines,
    todayDoses,
    isLoading,
    fetchMedicines,
    fetchTodayDoses,
    deleteMedicine,
    recordDose,
    updateMedicine,
  } = useHealthStore();

  useEffect(() => {
    fetchMedicines();
    fetchTodayDoses();
  }, [fetchMedicines, fetchTodayDoses]);

  const formatTime = (timeStr: string) => {
    const [hours, minutes] = timeStr.split(":");
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? "PM" : "AM";
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  };

  const getMedicineDoses = (medicineId: string) => {
    return todayDoses.filter((dose) => dose.medicine_id === medicineId);
  };

  const getCompletedDoses = (medicineId: string) => {
    return getMedicineDoses(medicineId).filter(
      (dose) => dose.status === "taken" || dose.status === "skipped"
    ).length;
  };

  const getTotalDoses = (medicineId: string) => {
    return getMedicineDoses(medicineId).length;
  };

  const isLowStock = (medicine: typeof medicines[0]) => {
    return medicine.current_stock <= medicine.refill_threshold;
  };

  return (
    <div className="space-y-4">
      {/* Today's Doses Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Today&apos;s Doses
          </CardTitle>
        </CardHeader>
        <CardContent>
          {todayDoses.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              No doses scheduled for today
            </p>
          ) : (
            <div className="space-y-3">
              {todayDoses
                .filter((dose) => dose.status === "pending")
                .map((dose) => {
                  const medicine = medicines.find((m) => m.id === dose.medicine_id);
                  return (
                    <div
                      key={dose.id}
                      className="flex items-center justify-between p-3 bg-muted rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{medicine?.name || "Unknown"}</p>
                        <p className="text-sm text-muted-foreground">
                          {medicine?.dosage} • {formatTime(dose.scheduled_time)}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => recordDose(dose.id, "taken")}
                        >
                          <Check className="h-4 w-4 mr-1" />
                          Taken
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => recordDose(dose.id, "skipped")}
                        >
                          <X className="h-4 w-4 mr-1" />
                          Skip
                        </Button>
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Medicines List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Medicines</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : medicines.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              No medicines added yet. Add your first medicine to start tracking.
            </p>
          ) : (
            <div className="space-y-4">
              {medicines.map((medicine) => (
                <div
                  key={medicine.id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Pill className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{medicine.name}</h3>
                          {!medicine.is_active && (
                            <Badge variant="secondary">Inactive</Badge>
                          )}
                          {isLowStock(medicine) && (
                            <Badge variant="destructive" className="flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3" />
                              Low Stock
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {medicine.dosage} • {medicine.frequency}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Times: {medicine.reminder_times.map(formatTime).join(", ")}
                        </p>
                        {medicine.instructions && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {medicine.instructions}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          updateMedicine(medicine.id, { is_active: !medicine.is_active })
                        }
                      >
                        {medicine.is_active ? (
                          <X className="h-4 w-4" />
                        ) : (
                          <Check className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteMedicine(medicine.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>

                  {/* Today's Progress */}
                  {medicine.is_active && getTotalDoses(medicine.id) > 0 && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span>Today&apos;s Progress</span>
                        <span>
                          {getCompletedDoses(medicine.id)} / {getTotalDoses(medicine.id)}
                        </span>
                      </div>
                      <Progress
                        value={
                          (getCompletedDoses(medicine.id) / getTotalDoses(medicine.id)) *
                          100
                        }
                      />
                    </div>
                  )}

                  {/* Stock Info */}
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>Stock: {medicine.current_stock} remaining</span>
                    <span>Refill at: {medicine.refill_threshold}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
