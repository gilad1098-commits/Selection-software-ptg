import { Prisma } from "@/app/generated/prisma";
import * as repo from "@/repositories/catalogRepository";
import { NotFoundError, ConflictError, DependencyError } from "@/lib/errors";
import type {
  CreateCatalogCategoryBody,
  UpdateCatalogCategoryBody,
  CatalogCategoryResponse,
  CreateCatalogItemBody,
  UpdateCatalogItemBody,
  CatalogItemFilterQuery,
  CatalogItemResponse,
} from "@/types/catalog";

function mapCategory(
  c: NonNullable<Awaited<ReturnType<typeof repo.findCategoryById>>>
): CatalogCategoryResponse {
  return {
    id: c.id,
    code: c.code,
    name: c.name,
    createdAt: c.createdAt.toISOString(),
    updatedAt: c.updatedAt.toISOString(),
    itemCount: c._count?.items,
  };
}

function mapItem(
  i: NonNullable<Awaited<ReturnType<typeof repo.findItemById>>>
): CatalogItemResponse {
  return {
    id: i.id,
    categoryId: i.categoryId,
    itemCode: i.itemCode,
    name: i.name,
    itemType: i.itemType,
    manufacturer: i.manufacturer,
    description: i.description,
    defaultUnitCost: i.defaultUnitCost?.toString() ?? null,
    unitOfMeasure: i.unitOfMeasure,
    isActive: i.isActive,
    attributesJson: i.attributesJson,
    createdAt: i.createdAt.toISOString(),
    updatedAt: i.updatedAt.toISOString(),
    category: i.category,
  };
}

export async function listCategories(): Promise<CatalogCategoryResponse[]> {
  const categories = await repo.findAllCategories();
  return categories.map(mapCategory);
}

export async function getCategory(id: string): Promise<CatalogCategoryResponse> {
  const category = await repo.findCategoryById(id);
  if (!category) throw new NotFoundError("Category not found");
  return mapCategory(category);
}

export async function createCategory(
  body: CreateCatalogCategoryBody
): Promise<CatalogCategoryResponse> {
  try {
    const category = await repo.createCategory(body);
    return mapCategory(await repo.findCategoryById(category.id) as NonNullable<Awaited<ReturnType<typeof repo.findCategoryById>>>);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
      throw new ConflictError("Category code already exists");
    }
    throw e;
  }
}

export async function updateCategory(
  id: string,
  body: UpdateCatalogCategoryBody
): Promise<CatalogCategoryResponse> {
  const existing = await repo.findCategoryById(id);
  if (!existing) throw new NotFoundError("Category not found");
  try {
    await repo.updateCategory(id, body);
    return mapCategory(await repo.findCategoryById(id) as NonNullable<Awaited<ReturnType<typeof repo.findCategoryById>>>);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
      throw new ConflictError("Category code already exists");
    }
    throw e;
  }
}

export async function deleteCategory(id: string): Promise<void> {
  const existing = await repo.findCategoryById(id);
  if (!existing) throw new NotFoundError("Category not found");
  const itemCount = await repo.countItemsByCategory(id);
  if (itemCount > 0) {
    throw new DependencyError(`Cannot delete category with ${itemCount} items`);
  }
  await repo.deleteCategory(id);
}

export async function listItems(
  filters: CatalogItemFilterQuery
): Promise<CatalogItemResponse[]> {
  const items = await repo.findItemsByFilter(filters);
  return items.map(mapItem);
}

export async function getItem(id: string): Promise<CatalogItemResponse> {
  const item = await repo.findItemById(id);
  if (!item) throw new NotFoundError("Item not found");
  return mapItem(item);
}

export async function createItem(
  body: CreateCatalogItemBody
): Promise<CatalogItemResponse> {
  const category = await repo.findCategoryById(body.categoryId);
  if (!category) throw new NotFoundError("Category not found");
  try {
    const item = await repo.createItem(body);
    return mapItem(item);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
      throw new ConflictError("Item code already exists");
    }
    throw e;
  }
}

export async function updateItem(
  id: string,
  body: UpdateCatalogItemBody
): Promise<CatalogItemResponse> {
  const existing = await repo.findItemById(id);
  if (!existing) throw new NotFoundError("Item not found");
  try {
    const item = await repo.updateItem(id, body);
    return mapItem(item);
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === "P2002") {
      throw new ConflictError("Item code already exists");
    }
    throw e;
  }
}

export async function deactivateItem(id: string): Promise<CatalogItemResponse> {
  const existing = await repo.findItemById(id);
  if (!existing) throw new NotFoundError("Item not found");
  await repo.updateItem(id, { isActive: false });
  return mapItem(await repo.findItemById(id) as NonNullable<Awaited<ReturnType<typeof repo.findItemById>>>);
}
