import { prisma } from "@/lib/prisma";
import { Prisma } from "@/app/generated/prisma";
import type { CreateSectionBody, UpdateSectionBody } from "@/types/section";

export async function findSectionsByUnitId(unitId: string) {
  return prisma.section.findMany({
    where: { unitId },
    orderBy: { sequenceNumber: "asc" },
    include: { _count: { select: { componentSelections: true } } },
  });
}

export async function findSectionById(id: string) {
  return prisma.section.findUnique({
    where: { id },
    include: {
      componentSelections: {
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
      },
    },
  });
}

export async function sequenceNumberExists(
  unitId: string,
  sequenceNumber: number,
  excludeSectionId?: string
) {
  const section = await prisma.section.findFirst({
    where: {
      unitId,
      sequenceNumber,
      ...(excludeSectionId ? { NOT: { id: excludeSectionId } } : {}),
    },
  });
  return !!section;
}

export async function createSection(unitId: string, data: CreateSectionBody) {
  return prisma.section.create({
    data: {
      ...data,
      unitId,
      metadataJson: data.metadataJson
        ? (data.metadataJson as unknown as Prisma.InputJsonValue)
        : Prisma.JsonNull,
    },
  });
}

export async function updateSection(id: string, data: UpdateSectionBody) {
  const { metadataJson, ...rest } = data;
  const update: Prisma.SectionUpdateInput = rest as Prisma.SectionUpdateInput;
  if ("metadataJson" in data) {
    update.metadataJson = metadataJson
      ? (metadataJson as unknown as Prisma.InputJsonValue)
      : Prisma.JsonNull;
  }
  return prisma.section.update({ where: { id }, data: update });
}

export async function deleteSection(id: string) {
  return prisma.section.delete({ where: { id } });
}

export async function reorderSections(
  updates: Array<{ id: string; sequenceNumber: number }>
) {
  return prisma.$transaction(
    updates.map(({ id, sequenceNumber }) =>
      prisma.section.update({ where: { id }, data: { sequenceNumber } })
    )
  );
}

export async function countSectionsByUnitId(unitId: string) {
  return prisma.section.count({ where: { unitId } });
}
