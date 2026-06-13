"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api-client";
import { ARRANGEMENT_TYPE_LABELS, PROJECT_STATUS_LABELS } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { UnitResponse } from "@/types/unit";
import type { ArrangementType, IndoorOutdoor } from "@/app/generated/prisma";

type UnitFormValues = {
  unitName: string;
  arrangementType: ArrangementType;
  airflowCfm?: string;
  indoorOutdoor: IndoorOutdoor;
  widthIn?: string;
  heightIn?: string;
};

function statusClass(status: string) {
  switch (status) {
    case "DRAFT": return "bg-[#2A3140] text-[#8B949E] border-[#2A3140]";
    case "IN_PROGRESS": return "bg-blue-900/60 text-blue-300 border-blue-700";
    case "QUOTED": return "bg-yellow-900/60 text-yellow-300 border-yellow-700";
    case "APPROVED": return "bg-green-900/60 text-green-300 border-green-700";
    case "CANCELLED": return "bg-red-900/60 text-red-300 border-red-700";
    default: return "bg-[#2A3140] text-[#8B949E] border-[#2A3140]";
  }
}

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.projectId as string;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [addUnitOpen, setAddUnitOpen] = useState(false);
  const [deleteUnitTarget, setDeleteUnitTarget] = useState<UnitResponse | null>(null);
  const [arrangementType, setArrangementType] = useState<ArrangementType>("SUPPLY_ONLY");
  const [indoorOutdoor, setIndoorOutdoor] = useState<IndoorOutdoor>("INDOOR");

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.projects.get(projectId),
  });

  const { data: units, isLoading: unitsLoading } = useQuery({
    queryKey: ["units", projectId],
    queryFn: () => api.units.list(projectId),
    enabled: !!projectId,
  });

  const createUnitMutation = useMutation({
    mutationFn: (values: UnitFormValues) =>
      api.units.create(projectId, {
        unitName: values.unitName,
        arrangementType: values.arrangementType,
        airflowCfm: values.airflowCfm ? Number(values.airflowCfm) : undefined,
        indoorOutdoor: values.indoorOutdoor,
        widthIn: values.widthIn ? Number(values.widthIn) : undefined,
        heightIn: values.heightIn ? Number(values.heightIn) : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["units", projectId] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setAddUnitOpen(false);
      reset();
    },
  });

  const deleteUnitMutation = useMutation({
    mutationFn: (id: string) => api.units.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["units", projectId] });
      setDeleteUnitTarget(null);
    },
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<UnitFormValues>({
    defaultValues: { unitName: "", arrangementType: "SUPPLY_ONLY", indoorOutdoor: "INDOOR" },
  });

  function onSubmit(values: UnitFormValues) {
    createUnitMutation.mutate({ ...values, arrangementType, indoorOutdoor });
  }

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-[#181C22] p-8">
        <Skeleton className="h-8 w-64 bg-[#2A3140] mb-4" />
        <Skeleton className="h-32 w-full bg-[#2A3140]" />
      </div>
    );
  }

  if (!project) {
    return <div className="min-h-screen bg-[#181C22] flex items-center justify-center text-[#8B949E]">Project not found.</div>;
  }

  return (
    <div className="min-h-screen bg-[#181C22] text-[#E8E8E8]">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-[#8B949E] mb-6">
          <Link href="/projects" className="hover:text-[#E8A23D] transition-colors">Projects</Link>
          <span>/</span>
          <span className="text-[#E8E8E8]">{project.projectName}</span>
        </nav>

        {/* Project Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-[#E8E8E8]">{project.projectName}</h1>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusClass(project.status)}`}>
                {PROJECT_STATUS_LABELS[project.status] ?? project.status}
              </span>
            </div>
            <p className="text-[#8B949E]">{project.customerName}</p>
            {project.quoteNumber && <p className="text-[#8B949E] text-sm mt-1">Quote: {project.quoteNumber}</p>}
            {project.notes && <p className="text-[#8B949E] text-sm mt-2 italic">{project.notes}</p>}
          </div>
          <Button
            onClick={() => setAddUnitOpen(true)}
            className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d] font-semibold"
          >
            + Add Unit
          </Button>
        </div>

        {/* Units */}
        <div>
          <h2 className="text-lg font-semibold text-[#E8E8E8] mb-4">Air Handling Units</h2>
          {unitsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-48 bg-[#2A3140] rounded-lg" />)}
            </div>
          ) : !units?.length ? (
            <div className="flex flex-col items-center justify-center py-16 bg-[#1F252C] rounded-lg border border-[#2A3140] text-[#8B949E]">
              <p className="text-lg font-medium">No units configured</p>
              <p className="text-sm mt-1">Add an AHU unit to begin configuration</p>
              <Button onClick={() => setAddUnitOpen(true)} className="mt-4 bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]">
                Add Unit
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {units.map((unit) => (
                <Card
                  key={unit.id}
                  className="bg-[#1F252C] border-[#2A3140] hover:border-[#E8A23D]/50 transition-colors cursor-pointer group"
                  onClick={() => router.push(`/projects/${projectId}/units/${unit.id}`)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-[#E8E8E8] text-base">{unit.unitName}</CardTitle>
                      <span className="text-xs bg-[#2A3140] text-[#8B949E] px-2 py-0.5 rounded">
                        {ARRANGEMENT_TYPE_LABELS[unit.arrangementType] ?? unit.arrangementType}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-1 text-sm text-[#8B949E]">
                      {unit.airflowCfm && <p>Airflow: <span className="text-[#E8E8E8]">{unit.airflowCfm} CFM</span></p>}
                      {(unit.widthIn || unit.heightIn) && (
                        <p>Size: <span className="text-[#E8E8E8]">{unit.widthIn ?? "?"}&quot; W × {unit.heightIn ?? "?"}&quot; H</span></p>
                      )}
                      <p>Sections: <span className="text-[#E8E8E8]">{unit._count?.sections ?? 0}</span></p>
                      <p>Location: <span className="text-[#E8E8E8]">{unit.indoorOutdoor === "INDOOR" ? "Indoor" : "Outdoor"}</span></p>
                    </div>
                    <div className="flex justify-end mt-4 gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-[#F85149] hover:text-[#F85149] hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => { e.stopPropagation(); setDeleteUnitTarget(unit); }}
                      >
                        Delete
                      </Button>
                      <Button
                        size="sm"
                        className="bg-[#2A3140] text-[#E8E8E8] hover:bg-[#E8A23D] hover:text-[#181C22] transition-colors"
                        onClick={(e) => { e.stopPropagation(); router.push(`/projects/${projectId}/units/${unit.id}`); }}
                      >
                        Open
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Unit Dialog */}
      <Dialog open={addUnitOpen} onOpenChange={setAddUnitOpen}>
        <DialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <DialogHeader>
            <DialogTitle className="text-[#E8E8E8]">Add Air Handling Unit</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Unit Name</Label>
              <Input {...register("unitName", { required: "Required" })} className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="e.g. AHU-01" />
              {errors.unitName && <p className="text-[#F85149] text-xs">{errors.unitName.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Arrangement Type</Label>
              <Select value={arrangementType} onValueChange={(v) => setArrangementType(v as ArrangementType)}>
                <SelectTrigger className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#1F252C] border-[#2A3140]">
                  {Object.entries(ARRANGEMENT_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k} className="text-[#E8E8E8] focus:bg-[#2A3140]">{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Airflow (CFM)</Label>
                <Input {...register("airflowCfm")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="e.g. 10000" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Location</Label>
                <Select value={indoorOutdoor} onValueChange={(v) => setIndoorOutdoor(v as IndoorOutdoor)}>
                  <SelectTrigger className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1F252C] border-[#2A3140]">
                    <SelectItem value="INDOOR" className="text-[#E8E8E8] focus:bg-[#2A3140]">Indoor</SelectItem>
                    <SelectItem value="OUTDOOR" className="text-[#E8E8E8] focus:bg-[#2A3140]">Outdoor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Width (in, max 96)</Label>
                <Input {...register("widthIn")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="e.g. 48" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[#8B949E]">Height (in)</Label>
                <Input {...register("heightIn")} type="number" className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8]" placeholder="e.g. 72" />
              </div>
            </div>
            {createUnitMutation.error && <p className="text-[#F85149] text-sm">{createUnitMutation.error.message}</p>}
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => { setAddUnitOpen(false); reset(); }} className="text-[#8B949E]">Cancel</Button>
              <Button type="submit" disabled={createUnitMutation.isPending} className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]">
                {createUnitMutation.isPending ? "Adding..." : "Add Unit"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Unit Dialog */}
      <AlertDialog open={!!deleteUnitTarget} onOpenChange={() => setDeleteUnitTarget(null)}>
        <AlertDialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#E8E8E8]">Delete Unit</AlertDialogTitle>
            <AlertDialogDescription className="text-[#8B949E]">
              Delete &quot;{deleteUnitTarget?.unitName}&quot;? All sections and components will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#2A3140] text-[#E8E8E8] border-[#2A3140]">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteUnitTarget && deleteUnitMutation.mutate(deleteUnitTarget.id)}
              className="bg-[#F85149] text-white hover:bg-red-700"
            >
              Delete Unit
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
