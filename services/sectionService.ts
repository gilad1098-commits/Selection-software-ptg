import { Prisma } from "@/app/generated/prisma";
import * as repo from "@/repositories/sectionRepository";
import * as unitRepo from "@/repositories/unitRepository";
import { NotFoundError, ConflictError, ValidationError } from "@/lib/errors";
import type {
  CreateSectionBody,
  UpdateSectionBody,
  ReorderSectionsBody,
  SectionResponse,
} from "@/types/section";

function mapSection(
  s: NonNullable<Awaited<ReturnType<typeof repo.findSectionById>>>
): SectionResponse {
  return {
    id: s.id,
    unitId: s.unitId,
    sequenceNumber: s.sequenceNumber,
    sectionType: s.sectionType,
    sectionName: s.sectionName,
    widthIn: s.widthIn?.toString() ?? null,
    heightIn: s.heightIn?.toString() ?? null,
    lengthIn: s.lengthIn?.toString() ?? null,
    serviceAccessRequired: s.serviceAccessRequired,
    drainPanRequired: s.drainPanRequired,
    validationStatus: s.validationStatus,
    metadataJson: s.metadataJson,
    createdAt: s.createdAt.toISOString(),
    updatedAt: s.updatedAt.toISOString(),
  };
}

export async function listSections(unitId: string): Promise<SectionResponse[]> {
  const unit = await unitRepo.findUnitById(unitId);
  if (!unit) throw new NotFoundError("Unit not found");
  const sections = await repo.findSectionsByUnitId(unitId);
  return sections.map((s) => ({
    id: s.id,
    unitId: s.unitId,
    sequenceNumber: s.sequenceNumber,
    sectionType: s.sectionType,
    sectionName: s.sectionName,
    widthIn: s.widthIn?.toString() ?? null,
    heightIn: s.heightIn?.toString() ?? null,
    lengthIn: s.lengthIn?.toString() ?? null,
    serviceAccessRequired: s.serviceAccessRequired,
    drainPanRequired: s.drainPanRequired,
    validationStatus: s.validationStatus,
    metadataJson: s.metadataJson,
    createdAt: s.createdAt.toISOString(),
    updatedAt: s.updatedAt.toISOString(),
  }));
}

export async function getSection(id: string): Promise<SectionResponse> {
  const section = await repo.findSectionById(id);
  if (!section) throw new NotFoundError("Section not found");
  return mapSection(section);
}

export async function createSection(
  unitId: string,
  body: CreateSectionBody
): Promise<SectionResponse> {
  const unit = await unitRepo.findUnitById(unitId);
  if (!unit) throw new NotFoundError("Unit not found");
  const exists = await repo.sequenceNumberExists(unitId, body.sequenceNumber);
  if (exists) throw new ConflictError(`Sequence number ${body.sequenceNumber} already in use`);
  const section = await repo.createSection(unitId, body);
  return mapSection(await repo.findSectionById(section.id) as NonNullable<Awaited<ReturnType<typeof repo.findSectionById>>>);
}

export async function updateSection(
  id: string,
  body: UpdateSectionBody
): Promise<SectionResponse> {
  const existing = await repo.findSectionById(id);
  if (!existing) throw new NotFoundError("Section not found");
  try {
    await repo.updateSection(id, body);
    return mapSection(await repo.findSectionById(id) as NonNullable<Awaited<ReturnType<typeof repo.findSectionById>>>);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Section not found");
    }
    throw e;
  }
}

export async function deleteSection(id: string): Promise<void> {
  try {
    await repo.deleteSection(id);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Section not found");
    }
    throw e;
  }
}

export async function reorderSections(
  unitId: string,
  body: ReorderSectionsBody
): Promise<SectionResponse[]> {
  const unit = await unitRepo.findUnitById(unitId);
  if (!unit) throw new NotFoundError("Unit not found");
  const existing = await repo.findSectionsByUnitId(unitId);
  const existingIds = new Set(existing.map((s) => s.id));
  for (const item of body.order) {
    if (!existingIds.has(item.id)) {
      throw new ValidationError(`Section ${item.id} does not belong to this unit`);
    }
  }
  if (body.order.length !== existing.length) {
    throw new ValidationError("Reorder must include all sections");
  }
  const nums = body.order.map((o) => o.sequenceNumber).sort((a, b) => a - b);
  for (let i = 0; i < nums.length; i++) {
    if (nums[i] !== i + 1) {
      throw new ValidationError("Sequence numbers must be continuous starting from 1");
    }
  }
  await repo.reorderSections(body.order);
  return listSections(unitId);
}
