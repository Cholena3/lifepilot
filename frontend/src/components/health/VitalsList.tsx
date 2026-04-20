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
import { useHealthStore } from "@/store/health-store";
import { VITAL_TYPES } from "@/lib/api/health";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Activity, Trash2, Download, TrendingUp, TrendingDown } from "lucide-react";

export function VitalsList() {
  const {
    vitals,
    vitalTrends,
    selectedVitalType,
    isLoading,
    fetchVitals,
    deleteVital,
    setSelectedVitalType,
    exportVitalsPdf,
  } = useHealthStore();

  useEffect(() => {
    if (!selectedVitalType) {
      setSelectedVitalType("blood_pressure_systolic");
    }
  }, [selectedVitalType, setSelectedVitalType]);

  const getVitalTypeLabel = (type: string) => {
    return VITAL_TYPES.find((v) => v.value === type)?.label || type;
  };

  const getVitalTypeUnit = (type: string) => {
    return VITAL_TYPES.find((v) => v.value === type)?.unit || "";
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString();
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const handleExport = async () => {
    if (selectedVitalType) {
      await exportVitalsPdf(selectedVitalType);
    }
  };

  return (
    <div className="space-y-4">
      {/* Vital Type Selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <Select
              value={selectedVitalType || ""}
              onValueChange={setSelectedVitalType}
            >
              <SelectTrigger className="w-[250px]">
                <SelectValue placeholder="Select vital type" />
              </SelectTrigger>
              <SelectContent>
                {VITAL_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button variant="outline" onClick={handleExport} disabled={!selectedVitalType}>
              <Download className="h-4 w-4 mr-2" />
              Export PDF
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Trends Chart */}
      {vitalTrends && vitalTrends.readings.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {getVitalTypeLabel(vitalTrends.vital_type)} Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={vitalTrends.readings}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <YAxis />
                  <Tooltip
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                    formatter={(value: number) => [
                      `${value} ${getVitalTypeUnit(vitalTrends.vital_type)}`,
                      "Value",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--primary))" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Average</p>
                <p className="text-xl font-bold">
                  {vitalTrends.average.toFixed(1)} {getVitalTypeUnit(vitalTrends.vital_type)}
                </p>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Min</p>
                <p className="text-xl font-bold flex items-center justify-center gap-1">
                  <TrendingDown className="h-4 w-4 text-blue-500" />
                  {vitalTrends.min} {getVitalTypeUnit(vitalTrends.vital_type)}
                </p>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">Max</p>
                <p className="text-xl font-bold flex items-center justify-center gap-1">
                  <TrendingUp className="h-4 w-4 text-red-500" />
                  {vitalTrends.max} {getVitalTypeUnit(vitalTrends.vital_type)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Readings */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Readings</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : vitals.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">
              No readings recorded yet. Add your first vital reading.
            </p>
          ) : (
            <div className="space-y-3">
              {vitals.map((vital) => (
                <div
                  key={vital.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {vital.value} {vital.unit}
                      </span>
                      <Badge variant="outline">
                        {getVitalTypeLabel(vital.vital_type)}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatDateTime(vital.recorded_at)}
                    </p>
                    {vital.notes && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {vital.notes}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => deleteVital(vital.id)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
