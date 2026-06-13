import { SectionType, ValidationStatus } from "@/app/generated/prisma";

export interface CreateSectionBody {
  sequenceNumber: number;
  sectionType: SectionType;
  sectionName?: string;
  widthIn?: number;
  heightIn?: number;
  lengthIn?: number;
  serviceAccessRequired?: boolean;
  drainPanRequired?: boolean;
  metadataJson?: Record<string, unknown>;
}

export interface UpdateSectionBody {
  sectionType?: SectionType;
  sectionName?: string;
  widthIn?: number;
  heightIn?: number;
  lengthIn?: number;
  serviceAccessRequired?: boolean;
  drainPanRequired?: boolean;
  metadataJson?: Record<string, unknown>;
}

export interface ReorderSectionsBody {
  order: Array<{ id: string; sequenceNumber: number }>;
}

export interface SectionResponse {
  id: string;
  unitId: string;
  sequenceNumber: number;
  sectionType: SectionType;
  sectionName: string | null;
  widthIn: string | null;
  heightIn: string | null;
  lengthIn: string | null;
  serviceAccessRequired: boolean;
  drainPanRequired: boolean;
  validationStatus: ValidationStatus;
  metadataJson: unknown;
  createdAt: string;
  updatedAt: string;
}
