"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useAuthStore } from "@/store/auth-store";
import { profileApi } from "@/lib/api/profile";
import {
  basicProfileSchema,
  studentProfileSchema,
  careerPreferencesSchema,
  BasicProfileFormData,
  StudentProfileFormData,
  CareerPreferencesFormData,
} from "@/lib/validations/profile";

const STEPS = [
  { id: 1, title: "Basic Profile", description: "Personal information" },
  { id: 2, title: "Student Profile", description: "Academic details" },
  { id: 3, title: "Career Preferences", description: "Job preferences" },
];

const COMMON_ROLES = [
  "Software Engineer",
  "Data Scientist",
  "Product Manager",
  "UX Designer",
  "DevOps Engineer",
  "Business Analyst",
  "Full Stack Developer",
  "Machine Learning Engineer",
];

const COMMON_LOCATIONS = [
  "Remote",
  "Bangalore",
  "Mumbai",
  "Delhi NCR",
  "Hyderabad",
  "Pune",
  "Chennai",
  "San Francisco",
  "New York",
];

export default function ProfileWizardPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [completionPercentage, setCompletionPercentage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form for basic profile (Step 1)
  const basicForm = useForm<BasicProfileFormData>({
    resolver: zodResolver(basicProfileSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      dateOfBirth: "",
      gender: undefined,
    },
  });

  // Form for student profile (Step 2)
  const studentForm = useForm<StudentProfileFormData>({
    resolver: zodResolver(studentProfileSchema),
    defaultValues: {
      institution: "",
      degree: "",
      branch: "",
      cgpa: null,
      graduationYear: null,
    },
  });

  // Form for career preferences (Step 3)
  const careerForm = useForm<CareerPreferencesFormData>({
    resolver: zodResolver(careerPreferencesSchema),
    defaultValues: {
      preferredRoles: [],
      preferredLocations: [],
      minSalary: null,
      maxSalary: null,
      jobType: null,
    },
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/auth/login");
      return;
    }
    loadProfileData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, router]);

  const loadProfileData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load all profile data in parallel
      const [profile, studentProfile, careerPreferences] = await Promise.all([
        profileApi.getProfile().catch(() => null),
        profileApi.getStudentProfile().catch(() => null),
        profileApi.getCareerPreferences().catch(() => null),
      ]);

      // Populate basic profile form
      if (profile) {
        setCompletionPercentage(profile.completion_percentage);
        basicForm.reset({
          firstName: profile.first_name || "",
          lastName: profile.last_name || "",
          dateOfBirth: profile.date_of_birth || "",
          gender: (profile.gender as BasicProfileFormData["gender"]) || undefined,
        });
      }

      // Populate student profile form
      if (studentProfile) {
        studentForm.reset({
          institution: studentProfile.institution || "",
          degree: studentProfile.degree || "",
          branch: studentProfile.branch || "",
          cgpa: studentProfile.cgpa,
          graduationYear: studentProfile.graduation_year,
        });
      }

      // Populate career preferences form
      if (careerPreferences) {
        careerForm.reset({
          preferredRoles: careerPreferences.preferred_roles || [],
          preferredLocations: careerPreferences.preferred_locations || [],
          minSalary: careerPreferences.min_salary,
          maxSalary: careerPreferences.max_salary,
          jobType: (careerPreferences.job_type as CareerPreferencesFormData["jobType"]) || null,
        });
      }
    } catch (err) {
      setError("Failed to load profile data");
      console.error("Error loading profile:", err);
    } finally {
      setIsLoading(false);
    }
  }, [basicForm, studentForm, careerForm]);

  const handleBasicProfileSubmit = async (data: BasicProfileFormData) => {
    try {
      setIsSaving(true);
      setError(null);
      const response = await profileApi.updateProfile({
        first_name: data.firstName || null,
        last_name: data.lastName || null,
        date_of_birth: data.dateOfBirth || null,
        gender: data.gender || null,
      });
      setCompletionPercentage(response.completion_percentage);
      setCurrentStep(2);
    } catch (err) {
      setError("Failed to save basic profile");
      console.error("Error saving basic profile:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleStudentProfileSubmit = async (data: StudentProfileFormData) => {
    try {
      setIsSaving(true);
      setError(null);
      await profileApi.updateStudentProfile({
        institution: data.institution || null,
        degree: data.degree || null,
        branch: data.branch || null,
        cgpa: data.cgpa,
        graduation_year: data.graduationYear,
      });
      // Refresh completion percentage
      const profile = await profileApi.getProfile();
      setCompletionPercentage(profile.completion_percentage);
      setCurrentStep(3);
    } catch (err) {
      setError("Failed to save student profile");
      console.error("Error saving student profile:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCareerPreferencesSubmit = async (data: CareerPreferencesFormData) => {
    try {
      setIsSaving(true);
      setError(null);
      await profileApi.updateCareerPreferences({
        preferred_roles: data.preferredRoles?.length ? data.preferredRoles : null,
        preferred_locations: data.preferredLocations?.length ? data.preferredLocations : null,
        min_salary: data.minSalary,
        max_salary: data.maxSalary,
        job_type: data.jobType,
      });
      // Refresh completion percentage
      const profile = await profileApi.getProfile();
      setCompletionPercentage(profile.completion_percentage);
      // Navigate to dashboard on completion
      router.push("/dashboard");
    } catch (err) {
      setError("Failed to save career preferences");
      console.error("Error saving career preferences:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSkip = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    } else {
      router.push("/dashboard");
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const toggleArrayItem = (
    array: string[],
    item: string,
    onChange: (value: string[]) => void
  ) => {
    if (array.includes(item)) {
      onChange(array.filter((i) => i !== item));
    } else {
      onChange([...array, item]);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="text-2xl font-bold text-primary">
            LifePilot
          </Link>
          <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            Back to Dashboard
          </Link>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Progress Section */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-2">
            <h1 className="text-2xl font-bold">Complete Your Profile</h1>
            <span className="text-sm font-medium text-muted-foreground">
              {completionPercentage}% Complete
            </span>
          </div>
          <Progress value={completionPercentage} className="h-2" />
        </div>

        {/* Step Indicators */}
        <div className="flex justify-between mb-8">
          {STEPS.map((step) => (
            <div
              key={step.id}
              className={`flex-1 text-center ${
                step.id === currentStep
                  ? "text-primary"
                  : step.id < currentStep
                  ? "text-muted-foreground"
                  : "text-muted-foreground/50"
              }`}
            >
              <div
                className={`w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center text-sm font-medium ${
                  step.id === currentStep
                    ? "bg-primary text-primary-foreground"
                    : step.id < currentStep
                    ? "bg-primary/20 text-primary"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {step.id < currentStep ? "✓" : step.id}
              </div>
              <p className="text-sm font-medium">{step.title}</p>
              <p className="text-xs">{step.description}</p>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-md">
            {error}
          </div>
        )}

        {/* Step 1: Basic Profile */}
        {currentStep === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Basic Profile</CardTitle>
              <CardDescription>
                Tell us about yourself. This information helps personalize your experience.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...basicForm}>
                <form onSubmit={basicForm.handleSubmit(handleBasicProfileSubmit)} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={basicForm.control}
                      name="firstName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>First Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="John" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={basicForm.control}
                      name="lastName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Last Name *</FormLabel>
                          <FormControl>
                            <Input placeholder="Doe" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={basicForm.control}
                    name="dateOfBirth"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Date of Birth</FormLabel>
                        <FormControl>
                          <Input type="date" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={basicForm.control}
                    name="gender"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Gender</FormLabel>
                        <FormControl>
                          <select
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                            value={field.value || ""}
                            onChange={(e) => field.onChange(e.target.value || undefined)}
                          >
                            <option value="">Select gender</option>
                            <option value="male">Male</option>
                            <option value="female">Female</option>
                            <option value="other">Other</option>
                            <option value="prefer_not_to_say">Prefer not to say</option>
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex justify-between pt-4">
                    <Button type="button" variant="outline" onClick={handleSkip}>
                      Skip
                    </Button>
                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Next"}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Student Profile */}
        {currentStep === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Student Profile</CardTitle>
              <CardDescription>
                Your academic information helps us find relevant exams and opportunities.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...studentForm}>
                <form onSubmit={studentForm.handleSubmit(handleStudentProfileSubmit)} className="space-y-4">
                  <FormField
                    control={studentForm.control}
                    name="institution"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Institution</FormLabel>
                        <FormControl>
                          <Input placeholder="e.g., MIT, Stanford University" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={studentForm.control}
                      name="degree"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Degree</FormLabel>
                          <FormControl>
                            <select
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                              value={field.value || ""}
                              onChange={(e) => field.onChange(e.target.value || "")}
                            >
                              <option value="">Select degree</option>
                              <option value="B.Tech">B.Tech</option>
                              <option value="B.E.">B.E.</option>
                              <option value="B.Sc">B.Sc</option>
                              <option value="BCA">BCA</option>
                              <option value="M.Tech">M.Tech</option>
                              <option value="M.E.">M.E.</option>
                              <option value="M.Sc">M.Sc</option>
                              <option value="MCA">MCA</option>
                              <option value="MBA">MBA</option>
                              <option value="PhD">PhD</option>
                              <option value="Other">Other</option>
                            </select>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={studentForm.control}
                      name="branch"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Branch/Major</FormLabel>
                          <FormControl>
                            <select
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                              value={field.value || ""}
                              onChange={(e) => field.onChange(e.target.value || "")}
                            >
                              <option value="">Select branch</option>
                              <option value="Computer Science">Computer Science</option>
                              <option value="Information Technology">Information Technology</option>
                              <option value="Electronics">Electronics</option>
                              <option value="Electrical">Electrical</option>
                              <option value="Mechanical">Mechanical</option>
                              <option value="Civil">Civil</option>
                              <option value="Chemical">Chemical</option>
                              <option value="Data Science">Data Science</option>
                              <option value="AI/ML">AI/ML</option>
                              <option value="Other">Other</option>
                            </select>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={studentForm.control}
                      name="cgpa"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>CGPA (0.0 - 10.0)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="0.01"
                              min="0"
                              max="10"
                              placeholder="8.5"
                              value={field.value ?? ""}
                              onChange={(e) =>
                                field.onChange(e.target.value ? parseFloat(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={studentForm.control}
                      name="graduationYear"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Graduation Year</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min="1990"
                              max="2050"
                              placeholder="2025"
                              value={field.value ?? ""}
                              onChange={(e) =>
                                field.onChange(e.target.value ? parseInt(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="flex justify-between pt-4">
                    <div className="space-x-2">
                      <Button type="button" variant="outline" onClick={handlePrevious}>
                        Previous
                      </Button>
                      <Button type="button" variant="ghost" onClick={handleSkip}>
                        Skip
                      </Button>
                    </div>
                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Next"}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Career Preferences */}
        {currentStep === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>Career Preferences</CardTitle>
              <CardDescription>
                Tell us about your career goals to get personalized job recommendations.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...careerForm}>
                <form onSubmit={careerForm.handleSubmit(handleCareerPreferencesSubmit)} className="space-y-4">
                  <FormField
                    control={careerForm.control}
                    name="preferredRoles"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Preferred Roles</FormLabel>
                        <FormControl>
                          <div className="flex flex-wrap gap-2">
                            {COMMON_ROLES.map((role) => (
                              <button
                                key={role}
                                type="button"
                                onClick={() =>
                                  toggleArrayItem(field.value || [], role, field.onChange)
                                }
                                className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                                  field.value?.includes(role)
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "bg-background border-input hover:bg-accent"
                                }`}
                              >
                                {role}
                              </button>
                            ))}
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={careerForm.control}
                    name="preferredLocations"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Preferred Locations</FormLabel>
                        <FormControl>
                          <div className="flex flex-wrap gap-2">
                            {COMMON_LOCATIONS.map((location) => (
                              <button
                                key={location}
                                type="button"
                                onClick={() =>
                                  toggleArrayItem(field.value || [], location, field.onChange)
                                }
                                className={`px-3 py-1 rounded-full text-sm border transition-colors ${
                                  field.value?.includes(location)
                                    ? "bg-primary text-primary-foreground border-primary"
                                    : "bg-background border-input hover:bg-accent"
                                }`}
                              >
                                {location}
                              </button>
                            ))}
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={careerForm.control}
                      name="minSalary"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Minimum Salary (Annual)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min="0"
                              placeholder="e.g., 500000"
                              value={field.value ?? ""}
                              onChange={(e) =>
                                field.onChange(e.target.value ? parseFloat(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={careerForm.control}
                      name="maxSalary"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Maximum Salary (Annual)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min="0"
                              placeholder="e.g., 1500000"
                              value={field.value ?? ""}
                              onChange={(e) =>
                                field.onChange(e.target.value ? parseFloat(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={careerForm.control}
                    name="jobType"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Job Type</FormLabel>
                        <FormControl>
                          <select
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                            value={field.value || ""}
                            onChange={(e) => field.onChange(e.target.value || null)}
                          >
                            <option value="">Select job type</option>
                            <option value="full_time">Full Time</option>
                            <option value="part_time">Part Time</option>
                            <option value="internship">Internship</option>
                            <option value="contract">Contract</option>
                          </select>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex justify-between pt-4">
                    <div className="space-x-2">
                      <Button type="button" variant="outline" onClick={handlePrevious}>
                        Previous
                      </Button>
                      <Button type="button" variant="ghost" onClick={handleSkip}>
                        Skip
                      </Button>
                    </div>
                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Complete Profile"}
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
