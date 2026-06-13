import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/sectionComponentService";

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    return Response.json(await service.getComponent(id));
  } catch (e) {
    return handleError(e);
  }
}

export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    const body = await req.json();
    return Response.json(await service.updateComponent(id, body));
  } catch (e) {
    return handleError(e);
  }
}

export async function DELETE(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    await service.deleteComponent(id);
    return new Response(null, { status: 204 });
  } catch (e) {
    return handleError(e);
  }
}
