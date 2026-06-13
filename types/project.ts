import { ProjectStatus } from "@/app/generated/prisma";

export interface CreateProjectBody {
  customerName: string;
  projectName: string;
  quoteNumber?: string;
  currency?: string;
  notes?: string;
}

export interface UpdateProjectBody {
  customerName?: string;
  projectName?: string;
  quoteNumber?: string;
  currency?: string;
  status?: ProjectStatus;
  notes?: string;
}

export interface ProjectResponse {
  id: string;
  customerName: string;
  projectName: string;
  quoteNumber: string | null;
  currency: string;
  status: ProjectStatus;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
  _count?: { units: number };
}
