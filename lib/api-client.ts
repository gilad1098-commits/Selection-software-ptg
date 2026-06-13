import type { ProjectResponse, CreateProjectBody, UpdateProjectBody } from "@/types/project";
import type { UnitResponse, CreateUnitBody, UpdateUnitBody } from "@/types/unit";
import type { SectionResponse, CreateSectionBody, UpdateSectionBody, ReorderSectionsBody } from "@/types/section";
import type { SectionComponentResponse, CreateSectionComponentBody, UpdateSectionComponentBody } from "@/types/sectionComponent";
import type { CatalogCategoryResponse, CatalogItemResponse } from "@/types/catalog";

const BASE = "";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  projects: {
    list: () => request<ProjectResponse[]>("/api/projects"),
    get: (id: string) => request<ProjectResponse>(`/api/projects/${id}`),
    create: (body: CreateProjectBody) =>
      request<ProjectResponse>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: UpdateProjectBody) =>
      request<ProjectResponse>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) =>
      request<void>(`/api/projects/${id}`, { method: "DELETE" }),
  },
  units: {
    list: (projectId: string) => request<UnitResponse[]>(`/api/projects/${projectId}/units`),
    get: (id: string) => request<UnitResponse>(`/api/units/${id}`),
    create: (projectId: string, body: CreateUnitBody) =>
      request<UnitResponse>(`/api/projects/${projectId}/units`, { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: UpdateUnitBody) =>
      request<UnitResponse>(`/api/units/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) =>
      request<void>(`/api/units/${id}`, { method: "DELETE" }),
  },
  sections: {
    list: (unitId: string) => request<SectionResponse[]>(`/api/units/${unitId}/sections`),
    get: (id: string) => request<SectionResponse>(`/api/sections/${id}`),
    create: (unitId: string, body: CreateSectionBody) =>
      request<SectionResponse>(`/api/units/${unitId}/sections`, { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: UpdateSectionBody) =>
      request<SectionResponse>(`/api/sections/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) =>
      request<void>(`/api/sections/${id}`, { method: "DELETE" }),
    reorder: (unitId: string, body: ReorderSectionsBody) =>
      request<SectionResponse[]>(`/api/units/${unitId}/sections/reorder`, { method: "POST", body: JSON.stringify(body) }),
  },
  components: {
    list: (sectionId: string) => request<SectionComponentResponse[]>(`/api/sections/${sectionId}/components`),
    create: (sectionId: string, body: CreateSectionComponentBody) =>
      request<SectionComponentResponse>(`/api/sections/${sectionId}/components`, { method: "POST", body: JSON.stringify(body) }),
    update: (id: string, body: UpdateSectionComponentBody) =>
      request<SectionComponentResponse>(`/api/section-components/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
    delete: (id: string) =>
      request<void>(`/api/section-components/${id}`, { method: "DELETE" }),
  },
  catalog: {
    listCategories: () => request<CatalogCategoryResponse[]>("/api/catalog/categories"),
    listItems: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return request<CatalogItemResponse[]>(`/api/catalog/items${qs}`);
    },
  },
};
