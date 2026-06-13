import { prisma } from "@/lib/prisma";
import { Prisma } from "@/app/generated/prisma";
import type {
  CreateCatalogCategoryBody,
  UpdateCatalogCategoryBody,
  CreateCatalogItemBody,
  UpdateCatalogItemBody,
  CatalogItemFilterQuery,
} from "@/types/catalog";

export async function findAllCategories() {
  return prisma.catalogCategory.findMany({
    orderBy: { code: "asc" },
    include: { _count: { select: { items: true } } },
  });
}

export async function findCategoryById(id: string) {
  return prisma.catalogCategory.findUnique({
    where: { id },
    include: { _count: { select: { items: true } } },
  });
}

export async function createCategory(data: CreateCatalogCategoryBody) {
  return prisma.catalogCategory.create({ data });
}

export async function updateCategory(id: string, data: UpdateCatalogCategoryBody) {
  return prisma.catalogCategory.update({ where: { id }, data });
}

export async function deleteCategory(id: string) {
  return prisma.catalogCategory.delete({ where: { id } });
}

export async function findItemsByFilter(filters: CatalogItemFilterQuery) {
  const where: Prisma.CatalogItemWhereInput = {};
  if (filters.categoryId) where.categoryId = filters.categoryId;
  if (filters.itemType) where.itemType = filters.itemType;
  if (filters.isActive !== undefined) where.isActive = filters.isActive;
  if (filters.search) {
    where.OR = [
      { name: { contains: filters.search, mode: "insensitive" } },
      { itemCode: { contains: filters.search, mode: "insensitive" } },
      { manufacturer: { contains: filters.search, mode: "insensitive" } },
    ];
  }
  return prisma.catalogItem.findMany({
    where,
    orderBy: { itemCode: "asc" },
    include: {
      category: { select: { id: true, code: true, name: true } },
    },
  });
}

export async function findItemById(id: string) {
  return prisma.catalogItem.findUnique({
    where: { id },
    include: {
      category: { select: { id: true, code: true, name: true } },
    },
  });
}

export async function createItem(data: CreateCatalogItemBody) {
  return prisma.catalogItem.create({
    data: {
      ...data,
      attributesJson: data.attributesJson
        ? (data.attributesJson as unknown as Prisma.InputJsonValue)
        : Prisma.JsonNull,
    },
    include: { category: { select: { id: true, code: true, name: true } } },
  });
}

export async function updateItem(id: string, data: UpdateCatalogItemBody) {
  const { attributesJson, ...rest } = data;
  const update: Prisma.CatalogItemUpdateInput = rest as Prisma.CatalogItemUpdateInput;
  if ("attributesJson" in data) {
    update.attributesJson = attributesJson
      ? (attributesJson as unknown as Prisma.InputJsonValue)
      : Prisma.JsonNull;
  }
  return prisma.catalogItem.update({
    where: { id },
    data: update,
    include: { category: { select: { id: true, code: true, name: true } } },
  });
}

export async function countItemsByCategory(categoryId: string) {
  return prisma.catalogItem.count({ where: { categoryId } });
}
