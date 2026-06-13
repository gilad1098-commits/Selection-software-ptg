import { z } from "zod";

export const createProjectSchema = z.object({
  customerName: z.string().min(1, "Customer name required"),
  projectName: z.string().min(1, "Project name required"),
  quoteNumber: z.string().optional(),
  currency: z.string().default("USD"),
  notes: z.string().optional(),
});

export const updateProjectSchema = createProjectSchema.partial().extend({
  status: z.enum(["DRAFT","IN_PROGRESS","QUOTED","APPROVED","CANCELLED"]).optional(),
});

export type CreateProjectFormValues = z.infer<typeof createProjectSchema>;
export type UpdateProjectFormValues = z.infer<typeof updateProjectSchema>;
