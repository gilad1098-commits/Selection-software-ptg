import { ArrangementType, IndoorOutdoor, ServiceSide } from "@/app/generated/prisma";

export interface CreateUnitBody {
  unitName: string;
  arrangementType: ArrangementType;
  airflowCfm?: number;
  indoorOutdoor?: IndoorOutdoor;
  widthIn?: number;
  heightIn?: number;
  casingConstructionType?: string;
  panelThicknessIn?: number;
  insulationType?: string;
  baseFrameType?: string;
  serviceSide?: ServiceSide;
  accessLevel?: string;
}

export interface UpdateUnitBody {
  unitName?: string;
  arrangementType?: ArrangementType;
  airflowCfm?: number;
  indoorOutdoor?: IndoorOutdoor;
  widthIn?: number;
  heightIn?: number;
  casingConstructionType?: string;
  panelThicknessIn?: number;
  insulationType?: string;
  baseFrameType?: string;
  serviceSide?: ServiceSide;
  accessLevel?: string;
}

export interface UnitResponse {
  id: string;
  projectId: string;
  unitName: string;
  arrangementType: ArrangementType;
  airflowCfm: string | null;
  indoorOutdoor: IndoorOutdoor;
  widthIn: string | null;
  heightIn: string | null;
  casingConstructionType: string | null;
  panelThicknessIn: string | null;
  insulationType: string | null;
  baseFrameType: string | null;
  serviceSide: ServiceSide | null;
  accessLevel: string | null;
  createdAt: string;
  updatedAt: string;
  _count?: { sections: number };
}
