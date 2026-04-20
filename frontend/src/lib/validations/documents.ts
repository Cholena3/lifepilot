import { z } from "zod";

export const documentCategorySchema = z.enum([
  "identity",
  "education",
  "career",
  "finance",
]);

export const documentUploadSchema = z.object({
  title: z.string().min(1, "Title is required").max(200, "Title is too long"),
  category: documentCategorySchema,
  expiryDate: z.string().optional().nullable(),
});

export const documentSearchSchema = z.object({
  query: z.string().min(1, "Search query is required"),
  category: documentCategorySchema.optional(),
});

export const shareLinkCreateSchema = z.object({
  expiresInHours: z
    .number()
    .int()
    .min(1, "Expiry must be at least 1 hour")
    .max(720, "Expiry cannot exceed 30 days"),
  password: z
    .string()
    .min(4, "Password must be at least 4 characters")
    .max(50, "Password is too long")
    .optional()
    .nullable(),
});

export type DocumentCategory = z.infer<typeof documentCategorySchema>;
export type DocumentUploadFormData = z.infer<typeof documentUploadSchema>;
export type DocumentSearchFormData = z.infer<typeof documentSearchSchema>;
export type ShareLinkCreateFormData = z.infer<typeof shareLinkCreateSchema>;

export const DOCUMENT_CATEGORIES: { value: DocumentCategory; label: string }[] = [
  { value: "identity", label: "Identity" },
  { value: "education", label: "Education" },
  { value: "career", label: "Career" },
  { value: "finance", label: "Finance" },
];
