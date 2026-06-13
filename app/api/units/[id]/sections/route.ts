import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/sectionService";

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    return Response.json(await service.listSections(id));
  } catch (e) {
    return handleError(e);
  }
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    const body = await req.json();
    return Response.json(await service.createSection(id, body), { status: 201 });
  } catch (e) {
    return handleError(e);
  }
}
