import { Prisma } from "@/app/generated/prisma";
import * as repo from "@/repositories/sectionComponentRepository";
import * as sectionRepo from "@/repositories/sectionRepository";
import { NotFoundError } from "@/lib/errors";
import type {
  CreateSectionComponentBody,
  UpdateSectionComponentBody,
  SectionComponentResponse,
} from "@/types/sectionComponent";

function mapComponent(
  c: NonNullable<Awaited<ReturnType<typeof repo.findComponentById>>>
): SectionComponentResponse {
  return {
    id: c.id,
    sectionId: c.sectionId,
    catalogItemId: c.catalogItemId,
    quantity: c.quantity,
    selectionRole: c.selectionRole,
    configurationJson: c.configurationJson,
    createdAt: c.createdAt.toISOString(),
    updatedAt: c.updatedAt.toISOString(),
    catalogItem: c.catalogItem
      ? {
          id: c.catalogItem.id,
          itemCode: c.catalogItem.itemCode,
          name: c.catalogItem.name,
          itemType: c.catalogItem.itemType,
          manufacturer: c.catalogItem.manufacturer,
          defaultUnitCost: c.catalogItem.defaultUnitCost?.toString() ?? null,
          unitOfMeasure: c.catalogItem.unitOfMeasure,
        }
      : undefined,
  };
}

export async function listComponents(sectionId: string): Promise<SectionComponentResponse[]> {
  const section = await sectionRepo.findSectionById(sectionId);
  if (!section) throw new NotFoundError("Section not found");
  const components = await repo.findComponentsBySectionId(sectionId);
  return components.map(mapComponent);
}

export async function getComponent(id: string): Promise<SectionComponentResponse> {
  const component = await repo.findComponentById(id);
  if (!component) throw new NotFoundError("Component selection not found");
  return mapComponent(component);
}

export async function createComponent(
  sectionId: string,
  body: CreateSectionComponentBody
): Promise<SectionComponentResponse> {
  const section = await sectionRepo.findSectionById(sectionId);
  if (!section) throw new NotFoundError("Section not found");
  const component = await repo.createComponent(sectionId, body);
  return mapComponent(component);
}

export async function updateComponent(
  id: string,
  body: UpdateSectionComponentBody
): Promise<SectionComponentResponse> {
  const existing = await repo.findComponentById(id);
  if (!existing) throw new NotFoundError("Component selection not found");
  try {
    const updated = await repo.updateComponent(id, body);
    return mapComponent(updated);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Component selection not found");
    }
    throw e;
  }
}

export async function deleteComponent(id: string): Promise<void> {
  try {
    await repo.deleteComponent(id);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Component selection not found");
    }
    throw e;
  }
}
