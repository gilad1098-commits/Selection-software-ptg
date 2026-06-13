import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/catalogService";

export async function GET(
  _req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    return Response.json(await service.getItem(id));
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
    return Response.json(await service.updateItem(id, body));
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
    return Response.json(await service.deactivateItem(id));
  } catch (e) {
    return handleError(e);
  }
}
