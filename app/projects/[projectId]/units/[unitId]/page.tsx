"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { SECTION_TYPE_LABELS, ARRANGEMENT_TYPE_LABELS } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { SectionResponse } from "@/types/section";
import type { SectionType } from "@/app/generated/prisma";

const SECTION_TYPES: SectionType[] = [
  "FRESH_AIR_INTAKE","RETURN_AIR_INTAKE","MIXING_BOX","EMPTY_ACCESS",
  "FILTER","COOLING_COIL","HEATING_COIL","FAN","SILENCER",
  "HEAT_RECOVERY","HUMIDIFIER","UV","DAMPER","DISCHARGE_PLENUM"
];

type SectionFormValues = {
  sequenceNumber: string;
  sectionType: SectionType;
  sectionName?: string;
  widthIn?: string;
  heightIn?: string;
  lengthIn?: string;
};

function sectionTypeIcon(type: string) {
  switch (type) {
    case "FAN": return "🌀";
    case "FILTER": return "🔲";
    case "COOLING_COIL": return "❄️";
    case "HEATING_COIL": return "🔥";
    case "FRESH_AIR_INTAKE": return "🌬️";
    case "RETURN_AIR_INTAKE": return "↩️";
    case "MIXING_BOX": return "🔀";
    case "HEAT_RECOVERY": return "♻️";
    case "HUMIDIFIER": return "💧";
    case "SILENCER": return "🔇";
    case "UV": return "☀️";
    case "DAMPER": return "⊟";
    case "DISCHARGE_PLENUM": return "⊡";
    default: return "📦";
  }
}

export default function UnitWorkspacePage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const unitId = params.unitId as string;
  const queryClient = useQueryClient();

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [addSectionOpen, setAddSectionOpen] = useState(false);
  const [deleteSectionTarget, setDeleteSectionTarget] = useState<SectionResponse | null>(null);
  const [sectionType, setSectionType] = useState<SectionType>("FRESH_AIR_INTAKE");
  const [newComponentCatalogId, setNewComponentCatalogId] = useState("");
  const [newComponentQty, setNewComponentQty] = useState(1);

  const { data: unit, isLoading: unitLoading } = useQuery({
    queryKey: ["unit", unitId],
    queryFn: () => api.units.get(unitId),
  });

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.projects.get(projectId),
  });

  const { data: sections, isLoading: sectionsLoading } = useQuery({
    queryKey: ["sections", unitId],
    queryFn: () => api.sections.list(unitId),
    enabled: !!unitId,
  });

  const selectedSection = sections?.find((s) => s.id === selectedSectionId) ?? null;

  const { data: components, isLoading: componentsLoading } = useQuery({
    queryKey: ["components", selectedSectionId],
    queryFn: () => api.components.list(selectedSectionId!),
    enabled: !!selectedSectionId,
  });

  const createSectionMutation = useMutation({
    mutationFn: (values: SectionFormValues) =>
      api.sections.create(unitId, {
        sequenceNumber: Number(values.sequenceNumber),
        sectionType: values.sectionType,
        sectionName: values.sectionName || undefined,
        widthIn: values.widthIn ? Number(values.widthIn) : undefined,
        heightIn: values.heightIn ? Number(values.heightIn) : undefined,
        lengthIn: values.lengthIn ? Number(values.lengthIn) : undefined,
        serviceAccessRequired: false,
        drainPanRequired: false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", unitId] });
      setAddSectionOpen(false);
      reset();
    },
  });

  const deleteSectionMutation = useMutation({
    mutationFn: (id: string) => api.sections.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sections", unitId] });
      if (selectedSectionId === deleteSectionTarget?.id) setSelectedSectionId(null);
      setDeleteSectionTarget(null);
    },
  });

  const addComponentMutation = useMutation({
    mutationFn: () => api.components.create(selectedSectionId!, {
      catalogItemId: newComponentCatalogId,
      quantity: newComponentQty,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["components", selectedSectionId] });
      setNewComponentCatalogId("");
      setNewComponentQty(1);
    },
  });

  const deleteComponentMutation = useMutation({
    mutationFn: (id: string) => api.components.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["components", selectedSectionId] });
    },
  });

  const { register, handleSubmit, reset, setValue } = useForm<SectionFormValues>({
    defaultValues: {
      sequenceNumber: String((sections?.length ?? 0) + 1),
      sectionType: "FRESH_AIR_INTAKE",
    },
  });

  function onAddSection(values: SectionFormValues) {
    createSectionMutation.mutate({ ...values, sectionType });
  }

  if (unitLoading) {
    return (
      <div className="min-h-screen bg-[#181C22] p-8">
        <Skeleton className="h-8 w-64 bg-[#2A3140] mb-4" />
        <Skeleton className="h-96 w-full bg-[#2A3140]" />
      </div>
    );
  }

  if (!unit) {
    return <div className="min-h-screen bg-[#181C22] flex items-center justify-center text-[#8B949E]">Unit not found.</div>;
  }

  const nextSeq = String((sections?.length ?? 0) + 1);

  return (
    <div className="min-h-screen bg-[#181C22] text-[#E8E8E8] flex flex-col">
      {/* Top nav */}
      <div className="border-b border-[#2A3140] px-6 py-3 flex items-center gap-3 text-sm text-[#8B949E] bg-[#1F252C]">
        <Link href="/projects" className="hover:text-[#E8A23D] transition-colors">Projects</Link>
        <span>/</span>
        <Link href={`/projects/${projectId}`} className="hover:text-[#E8A23D] transition-colors">
          {project?.projectName ?? "Project"}
        </Link>
        <span>/</span>
        <span className="text-[#E8E8E8] font-medium">{unit.unitName}</span>
      </div>

      <div className="flex flex-1 overflow-hidden" style={{ height: "calc(100vh - 49px)" }}>
        {/* LEFT SIDEBAR */}
        <div className="w-64 bg-[#1F252C] border-r border-[#2A3140] flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-[#2A3140]">
            <h2 className="font-bold text-[#E8E8E8] text-base">{unit.unitName}</h2>
            <span className="text-xs bg-[#2A3140] text-[#8B949E] px-2 py-0.5 rounded mt-1 inline-block">
              {ARRANGEMENT_TYPE_LABELS[unit.arrangementType] ?? unit.arrangementType}
            </span>
          </div>
          <div className="p-4 border-b border-[#2A3140] space-y-1 text-sm">
            {unit.airflowCfm && (
              <p className="text-[#8B949E]">Airflow: <span className="text-[#E8E8E8]">{unit.airflowCfm} CFM</span></p>
            )}
            {(unit.widthIn || unit.heightIn) && (
              <p className="text-[#8B949E]">Size: <span className="text-[#E8E8E8]">{unit.widthIn ?? "?"}&quot; × {unit.heightIn ?? "?"}&quot;</span></p>
            )}
            <p className="text-[#8B949E]">Location: <span className="text-[#E8E8E8]">{unit.indoorOutdoor === "INDOOR" ? "Indoor" : "Outdoor"}</span></p>
          </div>
          {/* Section navigation */}
          <div className="flex-1 p-2">
            <p className="text-xs text-[#6E7681] font-semibold uppercase tracking-wider px-2 py-2">Sections</p>
            {sectionsLoading ? (
              <div className="space-y-1">
                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-8 bg-[#2A3140] rounded" />)}
              </div>
            ) : !sections?.length ? (
              <p className="text-xs text-[#6E7681] px-2">No sections yet</p>
            ) : (
              sections.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSectionId(s.id)}
                  className={`w-full text-left px-2 py-2 rounded text-sm transition-colors flex items-center gap-2 ${
                    selectedSectionId === s.id
                      ? "bg-[#E8A23D]/20 text-[#E8A23D] border border-[#E8A23D]/30"
                      : "text-[#8B949E] hover:bg-[#2A3140] hover:text-[#E8E8E8]"
                  }`}
                >
                  <span className="text-xs opacity-60 w-4">{s.sequenceNumber}</span>
                  <span className="text-sm">{sectionTypeIcon(s.sectionType)}</span>
                  <span className="truncate">{s.sectionName ?? SECTION_TYPE_LABELS[s.sectionType] ?? s.sectionType}</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* CENTER PANEL */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-[#E8E8E8]">Section Builder</h2>
            <Button
              onClick={() => {
                setValue("sequenceNumber", nextSeq);
                setSectionType("FRESH_AIR_INTAKE");
                setAddSectionOpen(true);
              }}
              className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d] text-sm font-semibold"
            >
              + Add Section
            </Button>
          </div>

          {/* Linear schematic */}
          {sections && sections.length > 0 && (
            <div className="mb-6 p-4 bg-[#1F252C] rounded-lg border border-[#2A3140] overflow-x-auto">
              <p className="text-xs text-[#6E7681] uppercase tracking-wider mb-3 font-semibold">Airflow Schematic</p>
              <div className="flex items-center gap-0 min-w-max">
                <div className="flex items-center text-[#E8A23D] text-xs mr-1">
                  <span className="text-[#8B949E]">IN</span>
                  <span className="ml-1 text-[#E8A23D]">→</span>
                </div>
                {sections.map((s, i) => (
                  <div key={s.id} className="flex items-center">
                    <button
                      onClick={() => setSelectedSectionId(s.id)}
                      className={`flex flex-col items-center justify-center w-20 h-16 border rounded text-center transition-all ${
                        selectedSectionId === s.id
                          ? "border-[#E8A23D] bg-[#E8A23D]/10"
                          : "border-[#2A3140] hover:border-[#E8A23D]/50 bg-[#181C22]"
                      }`}
                    >
                      <span className="text-xl">{sectionTypeIcon(s.sectionType)}</span>
                      <span className="text-[8px] text-[#8B949E] mt-0.5 px-0.5 leading-tight">
                        {(SECTION_TYPE_LABELS[s.sectionType] ?? s.sectionType).split(" ").slice(0, 2).join(" ")}
                      </span>
                    </button>
                    {i < sections.length - 1 && (
                      <span className="text-[#2A3140] mx-0.5">→</span>
                    )}
                  </div>
                ))}
                <div className="flex items-center text-[#8B949E] text-xs ml-1">
                  <span className="mr-1 text-[#E8A23D]">→</span>
                  <span>OUT</span>
                </div>
              </div>
            </div>
          )}

          {/* Section list */}
          {sectionsLoading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 bg-[#2A3140] rounded-lg" />)}
            </div>
          ) : !sections?.length ? (
            <div className="flex flex-col items-center justify-center py-20 bg-[#1F252C] rounded-lg border border-dashed border-[#2A3140] text-[#8B949E]">
              <p className="text-lg font-medium">No sections yet</p>
              <p className="text-sm mt-1">Add sections to build this AHU configuration</p>
              <Button onClick={() => setAddSectionOpen(true)} className="mt-4 bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]">
                Add First Section
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {sections.map((s) => (
                <div
                  key={s.id}
                  onClick={() => setSelectedSectionId(s.id)}
                  className={`flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-all ${
                    selectedSectionId === s.id
                      ? "border-[#E8A23D] bg-[#E8A23D]/5"
                      : "border-[#2A3140] bg-[#1F252C] hover:border-[#E8A23D]/40"
                  }`}
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded bg-[#2A3140] text-[#8B949E] text-sm font-mono font-bold">
                    {s.sequenceNumber}
                  </div>
                  <span className="text-2xl">{sectionTypeIcon(s.sectionType)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-[#E8E8E8]">
                        {s.sectionName ?? SECTION_TYPE_LABELS[s.sectionType] ?? s.sectionType}
                      </span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        s.validationStatus === "VALID" ? "bg-green-900/40 text-green-400" :
                        s.validationStatus === "WARNING" ? "bg-yellow-900/40 text-yellow-400" :
                        s.validationStatus === "INVALID" ? "bg-red-900/40 text-red-400" :
                        "bg-[#2A3140] text-[#6E7681]"
                      }`}>
                        {s.validationStatus}
                      </span>
                    </div>
                    <div className="flex gap-3 mt-0.5 text-xs text-[#8B949E]">
                      {s.widthIn && <span>{s.widthIn}&quot; W</span>}
                      {s.heightIn && <span>{s.heightIn}&quot; H</span>}
                      {s.lengthIn && <span>{s.lengthIn}&quot; L</span>}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-[#F85149] hover:text-[#F85149] hover:bg-red-900/20 h-7 px-2 text-xs"
                    onClick={(e) => { e.stopPropagation(); setDeleteSectionTarget(s); }}
                  >
                    ×
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="w-80 bg-[#1F252C] border-l border-[#2A3140] flex flex-col overflow-y-auto">
          {!selectedSection ? (
            <div className="flex flex-col items-center justify-center flex-1 p-6 text-[#6E7681] text-sm text-center">
              <p>Select a section to view and edit its details</p>
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-[#2A3140]">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xl">{sectionTypeIcon(selectedSection.sectionType)}</span>
                  <h3 className="font-semibold text-[#E8E8E8]">
                    {selectedSection.sectionName ?? SECTION_TYPE_LABELS[selectedSection.sectionType] ?? selectedSection.sectionType}
                  </h3>
                </div>
                <p className="text-xs text-[#8B949E]">Section #{selectedSection.sequenceNumber}</p>
              </div>

              {/* Section details */}
              <div className="p-4 border-b border-[#2A3140] space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#8B949E]">Type</span>
                  <span className="text-[#E8E8E8]">{SECTION_TYPE_LABELS[selectedSection.sectionType]}</span>
                </div>
                {selectedSection.widthIn && (
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">Width</span>
                    <span className="text-[#E8E8E8]">{selectedSection.widthIn}&quot;</span>
                  </div>
                )}
                {selectedSection.heightIn && (
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">Height</span>
                    <span className="text-[#E8E8E8]">{selectedSection.heightIn}&quot;</span>
                  </div>
                )}
                {selectedSection.lengthIn && (
                  <div className="flex justify-between">
                    <span className="text-[#8B949E]">Length</span>
                    <span className="text-[#E8E8E8]">{selectedSection.lengthIn}&quot;</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-[#8B949E]">Service Access</span>
                  <span className={selectedSection.serviceAccessRequired ? "text-[#E8A23D]" : "text-[#6E7681]"}>
                    {selectedSection.serviceAccessRequired ? "Required" : "None"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8B949E]">Drain Pan</span>
                  <span className={selectedSection.drainPanRequired ? "text-[#E8A23D]" : "text-[#6E7681]"}>
                    {selectedSection.drainPanRequired ? "Required" : "None"}
                  </span>
                </div>
              </div>

              {/* Components */}
              <div className="p-4 flex-1">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-[#E8E8E8]">Components</h4>
                </div>

                {componentsLoading ? (
                  <div className="space-y-2">
                    {[...Array(2)].map((_, i) => <Skeleton key={i} className="h-10 bg-[#2A3140]" />)}
                  </div>
                ) : !components?.length ? (
                  <p className="text-xs text-[#6E7681] mb-3">No components assigned</p>
                ) : (
                  <div className="space-y-1 mb-3">
                    {components.map((c) => (
                      <div key={c.id} className="flex items-center justify-between p-2 rounded bg-[#181C22] border border-[#2A3140]">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-[#E8E8E8] truncate">
                            {c.catalogItem?.name ?? c.catalogItemId}
                          </p>
                          <p className="text-xs text-[#6E7681]">
                            {c.catalogItem?.itemCode && `${c.catalogItem.itemCode} · `}Qty: {c.quantity}
                          </p>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 text-[#F85149] hover:bg-red-900/20 ml-2"
                          onClick={() => deleteComponentMutation.mutate(c.id)}
                        >
                          ×
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add component form */}
                <div className="space-y-2 pt-2 border-t border-[#2A3140]">
                  <p className="text-xs text-[#6E7681] font-semibold uppercase tracking-wider">Add Component</p>
                  <Input
                    value={newComponentCatalogId}
                    onChange={(e) => setNewComponentCatalogId(e.target.value)}
                    placeholder="Catalog Item ID"
                    className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] text-xs h-8"
                  />
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      min={1}
                      value={newComponentQty}
                      onChange={(e) => setNewComponentQty(Number(e.target.value))}
                      placeholder="Qty"
                      className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] text-xs h-8 w-20"
                    />
                    <Button
                      size="sm"
                      disabled={!newComponentCatalogId || addComponentMutation.isPending}
                      onClick={() => addComponentMutation.mutate()}
                      className="flex-1 bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d] h-8 text-xs"
                    >
                      {addComponentMutation.isPending ? "Adding..." : "Add"}
                    </Button>
                  </div>
                  {addComponentMutation.error && (
                    <p className="text-[#F85149] text-xs">{addComponentMutation.error.message}</p>
                  )}
                </div>
              </div>

              {/* Delete section button */}
              <div className="p-4 border-t border-[#2A3140]">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-[#F85149] hover:text-[#F85149] hover:bg-red-900/20"
                  onClick={() => setDeleteSectionTarget(selectedSection)}
                >
                  Delete Section
                </Button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Add Section Dialog */}
      <Dialog open={addSectionOpen} onOpenChange={setAddSectionOpen}>
        <DialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <DialogHeader>
            <DialogTitle className="text-[#E8E8E8]">Add Section</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onAddSection)} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Sequence #</Label>
                <Input {...register("sequenceNumber", { required: true })} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Section Type</Label>
                <Select value={sectionType} onValueChange={(v) => setSectionType(v as SectionType)}>
                  <SelectTrigger className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1F252C] border-[#2A3140] max-h-64 overflow-y-auto">
                    {SECTION_TYPES.map((t) => (
                      <SelectItem key={t} value={t} className="text-[#E8E8E8] focus:bg-[#2A3140]">
                        {sectionTypeIcon(t)} {SECTION_TYPE_LABELS[t] ?? t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Section Name (optional)</Label>
              <Input {...register("sectionName")} className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="Custom name..." />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Width (in)</Label>
                <Input {...register("widthIn")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="≤96" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Height (in)</Label>
                <Input {...register("heightIn")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Length (in)</Label>
                <Input {...register("lengthIn")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="≤120" />
              </div>
            </div>
            {createSectionMutation.error && (
              <p className="text-[#F85149] text-sm">{createSectionMutation.error.message}</p>
            )}
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => { setAddSectionOpen(false); reset(); }} className="text-[#8B949E]">Cancel</Button>
              <Button type="submit" disabled={createSectionMutation.isPending} className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]">
                {createSectionMutation.isPending ? "Adding..." : "Add Section"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Section Dialog */}
      <AlertDialog open={!!deleteSectionTarget} onOpenChange={() => setDeleteSectionTarget(null)}>
        <AlertDialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#E8E8E8]">Delete Section</AlertDialogTitle>
            <AlertDialogDescription className="text-[#8B949E]">
              Delete section &quot;{deleteSectionTarget ? (deleteSectionTarget.sectionName ?? SECTION_TYPE_LABELS[deleteSectionTarget.sectionType]) : ""}&quot;?
              All components in this section will be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#2A3140] text-[#E8E8E8] border-[#2A3140]">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteSectionTarget && deleteSectionMutation.mutate(deleteSectionTarget.id)}
              className="bg-[#F85149] text-white hover:bg-red-700"
            >
              Delete Section
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
