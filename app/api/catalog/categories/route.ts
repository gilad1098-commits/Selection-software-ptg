import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import * as service from "@/services/catalogService";

export async function GET() {
  try {
    return Response.json(await service.listCategories());
  } catch (e) {
    return handleError(e);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    return Response.json(await service.createCategory(body), { status: 201 });
  } catch (e) {
    return handleError(e);
  }
}
