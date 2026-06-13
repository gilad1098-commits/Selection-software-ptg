import type { NextRequest } from "next/server";
import { handleError } from "@/lib/errors";
import { CatalogItemType } from "@/app/generated/prisma";
import * as service from "@/services/catalogService";

export async function GET(req: NextRequest) {
  try {
    const sp = req.nextUrl.searchParams;
    const filters = {
      categoryId: sp.get("categoryId") ?? undefined,
      itemType: (sp.get("itemType") as CatalogItemType) ?? undefined,
      isActive: sp.get("isActive") === "false" ? false : true,
      search: sp.get("search") ?? undefined,
    };
    return Response.json(await service.listItems(filters));
  } catch (e) {
    return handleError(e);
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    return Response.json(await service.createItem(body), { status: 201 });
  } catch (e) {
    return handleError(e);
  }
}
