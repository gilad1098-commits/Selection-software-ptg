import { Prisma } from "@/app/generated/prisma";
import * as repo from "@/repositories/unitRepository";
import * as projectRepo from "@/repositories/projectRepository";
import { NotFoundError } from "@/lib/errors";
import type { CreateUnitBody, UpdateUnitBody, UnitResponse } from "@/types/unit";

function mapUnit(u: NonNullable<Awaited<ReturnType<typeof repo.findUnitById>>>): UnitResponse {
  return {
    id: u.id,
    projectId: u.projectId,
    unitName: u.unitName,
    arrangementType: u.arrangementType,
    airflowCfm: u.airflowCfm?.toString() ?? null,
    indoorOutdoor: u.indoorOutdoor,
    widthIn: u.widthIn?.toString() ?? null,
    heightIn: u.heightIn?.toString() ?? null,
    casingConstructionType: u.casingConstructionType,
    panelThicknessIn: u.panelThicknessIn?.toString() ?? null,
    insulationType: u.insulationType,
    baseFrameType: u.baseFrameType,
    serviceSide: u.serviceSide,
    accessLevel: u.accessLevel,
    createdAt: u.createdAt.toISOString(),
    updatedAt: u.updatedAt.toISOString(),
    _count: u._count,
  };
}

export async function listUnits(projectId: string): Promise<UnitResponse[]> {
  const project = await projectRepo.findProjectById(projectId);
  if (!project) throw new NotFoundError("Project not found");
  const units = await repo.findUnitsByProjectId(projectId);
  return units.map(mapUnit);
}

export async function getUnit(id: string): Promise<UnitResponse> {
  const unit = await repo.findUnitById(id);
  if (!unit) throw new NotFoundError("Unit not found");
  return mapUnit(unit);
}

export async function createUnit(
  projectId: string,
  body: CreateUnitBody
): Promise<UnitResponse> {
  const project = await projectRepo.findProjectById(projectId);
  if (!project) throw new NotFoundError("Project not found");
  const unit = await repo.createUnit(projectId, body);
  return mapUnit(await repo.findUnitById(unit.id) as NonNullable<Awaited<ReturnType<typeof repo.findUnitById>>>);
}

export async function updateUnit(
  id: string,
  body: UpdateUnitBody
): Promise<UnitResponse> {
  try {
    await repo.updateUnit(id, body);
    return mapUnit(await repo.findUnitById(id) as NonNullable<Awaited<ReturnType<typeof repo.findUnitById>>>);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Unit not found");
    }
    throw e;
  }
}

export async function deleteUnit(id: string): Promise<void> {
  try {
    await repo.deleteUnit(id);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2025") {
      throw new NotFoundError("Unit not found");
    }
    throw e;
  }
}
