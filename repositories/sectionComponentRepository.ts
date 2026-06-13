import { prisma } from "@/lib/prisma";
import { Prisma } from "@/app/generated/prisma";
import type {
  CreateSectionComponentBody,
  UpdateSectionComponentBody,
} from "@/types/sectionComponent";

export async function findComponentsBySectionId(sectionId: string) {
  return prisma.sectionComponentSelection.findMany({
    where: { sectionId },
    include: {
      catalogItem: {
        select: {
          id: true,
          itemCode: true,
          name: true,
          itemType: true,
          manufacturer: true,
          defaultUnitCost: true,
          unitOfMeasure: true,
        },
      },
    },
  });
}

export async function findComponentById(id: string) {
  return prisma.sectionComponentSelection.findUnique({
    where: { id },
    include: {
      catalogItem: {
        select: {
          id: true,
          itemCode: true,
          name: true,
          itemType: true,
          manufacturer: true,
          defaultUnitCost: true,
          unitOfMeasure: true,
        },
      },
    },
  });
}

export async function createComponent(
  sectionId: string,
  data: CreateSectionComponentBody
) {
  return prisma.sectionComponentSelection.create({
    data: {
      sectionId,
      catalogItemId: data.catalogItemId,
      quantity: data.quantity ?? 1,
      selectionRole: data.selectionRole,
      configurationJson: data.configurationJson
        ? (data.configurationJson as unknown as Prisma.InputJsonValue)
        : Prisma.JsonNull,
    },
    include: {
      catalogItem: {
        select: {
          id: true,
          itemCode: true,
          name: true,
          itemType: true,
          manufacturer: true,
          defaultUnitCost: true,
          unitOfMeasure: true,
        },
      },
    },
  });
}

export async function updateComponent(
  id: string,
  data: UpdateSectionComponentBody
) {
  const update: Prisma.SectionComponentSelectionUpdateInput = {};
  if (data.quantity !== undefined) update.quantity = data.quantity;
  if (data.selectionRole !== undefined) update.selectionRole = data.selectionRole;
  if ("configurationJson" in data) {
    update.configurationJson = data.configurationJson
      ? (data.configurationJson as unknown as Prisma.InputJsonValue)
      : Prisma.JsonNull;
  }
  return prisma.sectionComponentSelection.update({
    where: { id },
    data: update,
    include: {
      catalogItem: {
        select: {
          id: true,
          itemCode: true,
          name: true,
          itemType: true,
          manufacturer: true,
          defaultUnitCost: true,
          unitOfMeasure: true,
        },
      },
    },
  });
}

export async function deleteComponent(id: string) {
  return prisma.sectionComponentSelection.delete({ where: { id } });
}
