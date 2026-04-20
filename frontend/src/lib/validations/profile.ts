import { z } from "zod";

export const basicProfileSchema = z.object({
  firstName: z.string().min(1, "First name is required").max(50),
  lastName: z.string().min(1, "Last name is required").max(50),
  dateOfBirth: z.string().optional(),
  gender: z.enum(["male", "female", "other", "prefer_not_to_say"]).optional(),
});

export const studentProfileSchema = z.object({
  institution: z.string().max(200).optional(),
  degree: z.string().max(100).optional(),
  branch: z.string().max(100).optional(),
  cgpa: z
    .number()
    .min(0, "CGPA must be at least 0.0")
    .max(10, "CGPA cannot exceed 10.0")
    .optional()
    .nullable(),
  backlogs: z.number().int().min(0, "Backlogs cannot be negative").optional().nullable(),
  graduationYear: z
    .number()
    .int()
    .min(1990, "Invalid graduation year")
    .max(2050, "Invalid graduation year")
    .optional()
    .nullable(),
});

export const careerPreferencesSchema = z
  .object({
    preferredRoles: z.array(z.string()).optional(),
    preferredLocations: z.array(z.string()).optional(),
    minSalary: z.number().min(0, "Minimum salary cannot be negative").optional().nullable(),
    maxSalary: z.number().min(0, "Maximum salary cannot be negative").optional().nullable(),
    jobType: z.enum(["full_time", "part_time", "internship", "contract"]).optional().nullable(),
  })
  .refine(
    (data) => {
      if (data.minSalary != null && data.maxSalary != null) {
        return data.maxSalary >= data.minSalary;
      }
      return true;
    },
    {
      message: "Maximum salary must be greater than or equal to minimum salary",
      path: ["maxSalary"],
    }
  );

export type BasicProfileFormData = z.infer<typeof basicProfileSchema>;
export type StudentProfileFormData = z.infer<typeof studentProfileSchema>;
export type CareerPreferencesFormData = z.infer<typeof careerPreferencesSchema>;
