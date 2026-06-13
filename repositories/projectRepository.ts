import { prisma } from "@/lib/prisma";
import type { CreateProjectBody, UpdateProjectBody } from "@/types/project";

export async function findAllProjects() {
  return prisma.project.findMany({
    orderBy: { createdAt: "desc" },
    include: { _count: { select: { units: true } } },
  });
}

export async function findProjectById(id: string) {
  return prisma.project.findUnique({
    where: { id },
    include: { _count: { select: { units: true } } },
  });
}

export async function createProject(data: CreateProjectBody) {
  return prisma.project.create({ data });
}

export async function updateProject(id: string, data: UpdateProjectBody) {
  return prisma.project.update({ where: { id }, data });
}

export async function deleteProject(id: string) {
  return prisma.project.delete({ where: { id } });
}
