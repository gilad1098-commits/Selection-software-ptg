import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/projectService";

export async function GET() {
  try {
    const projects = await service.listProjects();
    return Response.json(projects);
  } catch (e) {
    return handleError(e);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const project = await service.createProject(body);
    return Response.json(project, { status: 201 });
  } catch (e) {
    return handleError(e);
  }
}
