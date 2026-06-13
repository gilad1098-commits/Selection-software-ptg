import { prisma } from "@/lib/prisma";
import type { CreateUnitBody, UpdateUnitBody } from "@/types/unit";

export async function findUnitsByProjectId(projectId: string) {
  return prisma.unit.findMany({
    where: { projectId },
    orderBy: { createdAt: "asc" },
    include: { _count: { select: { sections: true } } },
  });
}

export async function findUnitById(id: string) {
  return prisma.unit.findUnique({
    where: { id },
    include: { _count: { select: { sections: true } } },
  });
}

export async function findUnitWithSections(id: string) {
  return prisma.unit.findUnique({
    where: { id },
    include: {
      sections: {
        orderBy: { sequenceNumber: "asc" },
        include: { componentSelections: true },
      },
    },
  });
}

export async function createUnit(projectId: string, data: CreateUnitBody) {
  return prisma.unit.create({ data: { ...data, projectId } });
}

export async function updateUnit(id: string, data: UpdateUnitBody) {
  return prisma.unit.update({ where: { id }, data });
}

export async function deleteUnit(id: string) {
  return prisma.unit.delete({ where: { id } });
}
