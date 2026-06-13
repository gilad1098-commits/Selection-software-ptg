import { z } from "zod";

export const createUnitSchema = z.object({
  unitName: z.string().min(1, "Unit name required"),
  arrangementType: z.enum(["SUPPLY_ONLY","RETURN_ONLY","SUPPLY_RETURN","MAU","EXHAUST"]),
  airflowCfm: z.coerce.number().positive().optional(),
  indoorOutdoor: z.enum(["INDOOR","OUTDOOR"]).default("INDOOR"),
  widthIn: z.coerce.number().positive().max(96).optional(),
  heightIn: z.coerce.number().positive().optional(),
  casingConstructionType: z.string().optional(),
  panelThicknessIn: z.coerce.number().positive().optional(),
  insulationType: z.string().optional(),
  baseFrameType: z.string().optional(),
  serviceSide: z.enum(["LEFT","RIGHT","BOTH"]).optional(),
  accessLevel: z.string().optional(),
});

export type CreateUnitFormValues = z.infer<typeof createUnitSchema>;
