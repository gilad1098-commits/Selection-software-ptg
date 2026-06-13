import { CatalogItemType } from "@/app/generated/prisma";

export interface CreateCatalogCategoryBody {
  code: string;
  name: string;
}

export interface UpdateCatalogCategoryBody {
  code?: string;
  name?: string;
}

export interface CatalogCategoryResponse {
  id: string;
  code: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  itemCount?: number;
}

export interface CreateCatalogItemBody {
  categoryId: string;
  itemCode: string;
  name: string;
  itemType: CatalogItemType;
  manufacturer?: string;
  description?: string;
  defaultUnitCost?: number;
  unitOfMeasure?: string;
  attributesJson?: Record<string, unknown>;
}

export interface UpdateCatalogItemBody {
  categoryId?: string;
  itemCode?: string;
  name?: string;
  itemType?: CatalogItemType;
  manufacturer?: string;
  description?: string;
  defaultUnitCost?: number;
  unitOfMeasure?: string;
  isActive?: boolean;
  attributesJson?: Record<string, unknown>;
}

export interface CatalogItemFilterQuery {
  categoryId?: string;
  itemType?: CatalogItemType;
  isActive?: boolean;
  search?: string;
}

export interface CatalogItemResponse {
  id: string;
  categoryId: string;
  itemCode: string;
  name: string;
  itemType: CatalogItemType;
  manufacturer: string | null;
  description: string | null;
  defaultUnitCost: string | null;
  unitOfMeasure: string | null;
  isActive: boolean;
  attributesJson: unknown;
  createdAt: string;
  updatedAt: string;
  category?: { id: string; code: string; name: string };
}
