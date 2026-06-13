export interface ComponentConfigurationJson {
  fanType?: "plug" | "centrifugal" | "fanWall";
  coilType?: "CHW" | "HW" | "Steam" | "DX";
  filterStage?: string;
  accessories?: unknown;
}

export interface CreateSectionComponentBody {
  catalogItemId: string;
  quantity?: number;
  selectionRole?: string;
  configurationJson?: ComponentConfigurationJson;
}

export interface UpdateSectionComponentBody {
  quantity?: number;
  selectionRole?: string;
  configurationJson?: ComponentConfigurationJson;
}

export interface SectionComponentResponse {
  id: string;
  sectionId: string;
  catalogItemId: string;
  quantity: number;
  selectionRole: string | null;
  configurationJson: unknown;
  createdAt: string;
  updatedAt: string;
  catalogItem?: {
    id: string;
    itemCode: string;
    name: string;
    itemType: string;
    manufacturer: string | null;
    defaultUnitCost: string | null;
    unitOfMeasure: string | null;
  };
}
