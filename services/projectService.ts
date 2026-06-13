import { Prisma } from "@/app/generated/prisma";
import * as repo from "@/repositories/projectRepository";
import { NotFoundError } from "@/lib/errors";
import type {
  CreateProjectBody,
  UpdateProjectBody,
  ProjectResponse,
} from "@/types/project";

function mapProject(p: Awaited<ReturnType<typeof repo.findProjectById>>): ProjectResponse {
  if (!p) throw new NotFoundError("Project not found");
  return {
    id: p.id,
    customerName: p.customerName,
    projectName: p.projectName,
    quoteNumber: p.quoteNumber,
    currency: p.currency,
    status: p.status,
    notes: p.notes,
    createdAt: p.createdAt.toISOString(),
    updatedAt: p.updatedAt.toISOString(),
    _count: p._count,
  };
}

export async function listProjects(): Promise<ProjectResponse[]> {
  const projects = await repo.findAllProjects();
  return projects.map((p) => mapProject(p));
}

export async function getProject(id: string): Promise<ProjectResponse> {
  const project = await repo.findProjectById(id);
  if (!project) throw new NotFoundError("Project not found");
  return mapProject(project);
}

export async function createProject(body: CreateProjectBody): Promise<ProjectResponse> {
  const project = await repo.createProject(body);
  return mapProject(await repo.findProjectById(project.id));
}

export async function updateProject(
  id: string,
  body: UpdateProjectBody
): Promise<ProjectResponse> {
  try {
    await repo.updateProject(id, body);
    return mapProject(await repo.findProjectById(id));
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Project not found");
    }
    throw e;
  }
}

export async function deleteProject(id: string): Promise<void> {
  try {
    await repo.deleteProject(id);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Project not found");
    }
    throw e;
  }
}
