import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/sectionService";

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await ctx.params;
    const body = await req.json();
    return Response.json(await service.reorderSections(id, body));
  } catch (e) {
    return handleError(e);
  }
}
