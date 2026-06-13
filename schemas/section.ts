import { z } from "zod";

export const createSectionSchema = z.object({
  sequenceNumber: z.coerce.number().int().positive(),
  sectionType: z.enum([
    "FRESH_AIR_INTAKE","RETURN_AIR_INTAKE","MIXING_BOX","EMPTY_ACCESS",
    "FILTER","COOLING_COIL","HEATING_COIL","FAN","SILENCER",
    "HEAT_RECOVERY","HUMIDIFIER","UV","DAMPER","DISCHARGE_PLENUM"
  ]),
  sectionName: z.string().optional(),
  widthIn: z.coerce.number().positive().max(96).optional(),
  heightIn: z.coerce.number().positive().optional(),
  lengthIn: z.coerce.number().positive().max(120).optional(),
  serviceAccessRequired: z.boolean().default(false),
  drainPanRequired: z.boolean().default(false),
});

export type CreateSectionFormValues = z.infer<typeof createSectionSchema>;
