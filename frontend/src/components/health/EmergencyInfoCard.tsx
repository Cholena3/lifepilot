"use client";

import * as React from "react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useHealthStore } from "@/store/health-store";
import { BLOOD_TYPES } from "@/lib/api/health";
import { QrCode, Plus, X, AlertTriangle, Phone, Heart } from "lucide-react";

const emergencySchema = z.object({
  blood_type: z.string().optional(),
});

type EmergencyFormData = z.infer<typeof emergencySchema>;

const VISIBLE_FIELD_OPTIONS = [
  { value: "blood_type", label: "Blood Type" },
  { value: "allergies", label: "Allergies" },
  { value: "medical_conditions", label: "Medical Conditions" },
  { value: "emergency_contacts", label: "Emergency Contacts" },
  { value: "current_medications", label: "Current Medications" },
];

export function EmergencyInfoCard() {
  const {
    emergencyInfo,
    emergencyQrUrl,
    isLoading,
    isSubmitting,
    fetchEmergencyInfo,
    saveEmergencyInfo,
    fetchEmergencyQrCode,
  } = useHealthStore();

  const [allergies, setAllergies] = React.useState<string[]>([]);
  const [newAllergy, setNewAllergy] = React.useState("");
  const [conditions, setConditions] = React.useState<string[]>([]);
  const [newCondition, setNewCondition] = React.useState("");
  const [medications, setMedications] = React.useState<string[]>([]);
  const [newMedication, setNewMedication] = React.useState("");
  const [contacts, setContacts] = React.useState<
    { name: string; relationship: string; phone: string }[]
  >([]);
  const [visibleFields, setVisibleFields] = React.useState<string[]>([]);

  const { register, handleSubmit, setValue, watch } = useForm<EmergencyFormData>({
    resolver: zodResolver(emergencySchema),
  });

  useEffect(() => {
    fetchEmergencyInfo();
  }, [fetchEmergencyInfo]);

  useEffect(() => {
    if (emergencyInfo) {
      setValue("blood_type", emergencyInfo.blood_type || "");
      setAllergies(emergencyInfo.allergies || []);
      setConditions(emergencyInfo.medical_conditions || []);
      setMedications(emergencyInfo.current_medications || []);
      setContacts(emergencyInfo.emergency_contacts || []);
      setVisibleFields(emergencyInfo.visible_fields || []);
      fetchEmergencyQrCode();
    }
  }, [emergencyInfo, setValue, fetchEmergencyQrCode]);

  const addAllergy = () => {
    if (newAllergy.trim() && !allergies.includes(newAllergy.trim())) {
      setAllergies([...allergies, newAllergy.trim()]);
      setNewAllergy("");
    }
  };

  const removeAllergy = (allergy: string) => {
    setAllergies(allergies.filter((a) => a !== allergy));
  };

  const addCondition = () => {
    if (newCondition.trim() && !conditions.includes(newCondition.trim())) {
      setConditions([...conditions, newCondition.trim()]);
      setNewCondition("");
    }
  };

  const removeCondition = (condition: string) => {
    setConditions(conditions.filter((c) => c !== condition));
  };

  const addMedication = () => {
    if (newMedication.trim() && !medications.includes(newMedication.trim())) {
      setMedications([...medications, newMedication.trim()]);
      setNewMedication("");
    }
  };

  const removeMedication = (medication: string) => {
    setMedications(medications.filter((m) => m !== medication));
  };

  const addContact = () => {
    setContacts([...contacts, { name: "", relationship: "", phone: "" }]);
  };

  const updateContact = (
    index: number,
    field: "name" | "relationship" | "phone",
    value: string
  ) => {
    const newContacts = [...contacts];
    newContacts[index][field] = value;
    setContacts(newContacts);
  };

  const removeContact = (index: number) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  const toggleVisibleField = (field: string) => {
    if (visibleFields.includes(field)) {
      setVisibleFields(visibleFields.filter((f) => f !== field));
    } else {
      setVisibleFields([...visibleFields, field]);
    }
  };

  const onSubmit = async (data: EmergencyFormData) => {
    try {
      await saveEmergencyInfo({
        blood_type: data.blood_type || undefined,
        allergies,
        medical_conditions: conditions,
        emergency_contacts: contacts.filter((c) => c.name && c.phone),
        current_medications: medications,
        visible_fields: visibleFields,
      });
    } catch (error) {
      // Error is handled by the store
    }
  };

  return (
    <div className="space-y-4">
      {/* QR Code Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <QrCode className="h-5 w-5" />
            Emergency QR Code
          </CardTitle>
        </CardHeader>
        <CardContent>
          {emergencyQrUrl ? (
            <div className="flex flex-col items-center gap-4">
              <img
                src={emergencyQrUrl}
                alt="Emergency QR Code"
                className="w-48 h-48 border rounded-lg"
              />
              <p className="text-sm text-muted-foreground text-center">
                Scan this QR code to access your emergency health information.
                Only the fields you select below will be visible.
              </p>
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-4">
              Save your emergency info to generate a QR code
            </p>
          )}
        </CardContent>
      </Card>

      {/* Emergency Info Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Emergency Health Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Blood Type */}
            <div className="space-y-2">
              <Label>Blood Type</Label>
              <Select
                value={watch("blood_type") || ""}
                onValueChange={(value) => setValue("blood_type", value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select blood type" />
                </SelectTrigger>
                <SelectContent>
                  {BLOOD_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Allergies */}
            <div className="space-y-2">
              <Label>Allergies</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add allergy"
                  value={newAllergy}
                  onChange={(e) => setNewAllergy(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addAllergy())}
                />
                <Button type="button" variant="outline" onClick={addAllergy}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {allergies.map((allergy) => (
                  <Badge key={allergy} variant="secondary" className="gap-1">
                    {allergy}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => removeAllergy(allergy)}
                    />
                  </Badge>
                ))}
              </div>
            </div>

            {/* Medical Conditions */}
            <div className="space-y-2">
              <Label>Medical Conditions</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add condition"
                  value={newCondition}
                  onChange={(e) => setNewCondition(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addCondition())}
                />
                <Button type="button" variant="outline" onClick={addCondition}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {conditions.map((condition) => (
                  <Badge key={condition} variant="secondary" className="gap-1">
                    {condition}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => removeCondition(condition)}
                    />
                  </Badge>
                ))}
              </div>
            </div>

            {/* Current Medications */}
            <div className="space-y-2">
              <Label>Current Medications</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Add medication"
                  value={newMedication}
                  onChange={(e) => setNewMedication(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addMedication())}
                />
                <Button type="button" variant="outline" onClick={addMedication}>
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {medications.map((medication) => (
                  <Badge key={medication} variant="secondary" className="gap-1">
                    {medication}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => removeMedication(medication)}
                    />
                  </Badge>
                ))}
              </div>
            </div>

            {/* Emergency Contacts */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="flex items-center gap-2">
                  <Phone className="h-4 w-4" />
                  Emergency Contacts
                </Label>
                <Button type="button" variant="outline" size="sm" onClick={addContact}>
                  <Plus className="h-4 w-4 mr-1" />
                  Add Contact
                </Button>
              </div>
              <div className="space-y-3">
                {contacts.map((contact, index) => (
                  <div key={index} className="flex gap-2 items-start">
                    <Input
                      placeholder="Name"
                      value={contact.name}
                      onChange={(e) => updateContact(index, "name", e.target.value)}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Relationship"
                      value={contact.relationship}
                      onChange={(e) => updateContact(index, "relationship", e.target.value)}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Phone"
                      value={contact.phone}
                      onChange={(e) => updateContact(index, "phone", e.target.value)}
                      className="flex-1"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeContact(index)}
                    >
                      <X className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>

            {/* Visible Fields */}
            <div className="space-y-2">
              <Label>Visible on Public Page</Label>
              <p className="text-sm text-muted-foreground">
                Select which fields should be visible when someone scans your QR code
              </p>
              <div className="space-y-2 mt-2">
                {VISIBLE_FIELD_OPTIONS.map((field) => (
                  <div key={field.value} className="flex items-center gap-2">
                    <Checkbox
                      id={field.value}
                      checked={visibleFields.includes(field.value)}
                      onCheckedChange={() => toggleVisibleField(field.value)}
                    />
                    <Label htmlFor={field.value} className="font-normal cursor-pointer">
                      {field.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save Emergency Info"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
