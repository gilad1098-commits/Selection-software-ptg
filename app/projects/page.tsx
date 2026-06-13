"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api-client";
import { createProjectSchema } from "@/schemas/project";
import { PROJECT_STATUS_LABELS } from "@/lib/labels";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ProjectResponse } from "@/types/project";

type FormValues = {
  customerName: string;
  projectName: string;
  quoteNumber?: string;
  notes?: string;
};

function statusBadgeClass(status: string) {
  switch (status) {
    case "DRAFT": return "bg-[#2A3140] text-[#8B949E] border-[#2A3140]";
    case "IN_PROGRESS": return "bg-blue-900/60 text-blue-300 border-blue-700";
    case "QUOTED": return "bg-yellow-900/60 text-yellow-300 border-yellow-700";
    case "APPROVED": return "bg-green-900/60 text-green-300 border-green-700";
    case "CANCELLED": return "bg-red-900/60 text-red-300 border-red-700";
    default: return "bg-[#2A3140] text-[#8B949E] border-[#2A3140]";
  }
}

export default function ProjectsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProjectResponse | null>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.projects.list(),
  });

  const createMutation = useMutation({
    mutationFn: (values: FormValues) => api.projects.create({ ...values, currency: "USD" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setCreateOpen(false);
      reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.projects.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setDeleteTarget(null);
    },
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormValues>({
    defaultValues: { customerName: "", projectName: "" },
  });

  return (
    <div className="min-h-screen bg-[#181C22] text-[#E8E8E8]">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-[#E8E8E8]">Projects</h1>
            <p className="text-[#8B949E] mt-1">PTG AHU Configuration & Pricing</p>
          </div>
          <Button
            onClick={() => setCreateOpen(true)}
            className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d] font-semibold"
          >
            + New Project
          </Button>
        </div>

        {/* Table */}
        <Card className="bg-[#1F252C] border-[#2A3140]">
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-6 space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full bg-[#2A3140]" />
                ))}
              </div>
            ) : !projects?.length ? (
              <div className="flex flex-col items-center justify-center py-16 text-[#8B949E]">
                <div className="text-4xl mb-4">📋</div>
                <p className="text-lg font-medium">No projects yet</p>
                <p className="text-sm mt-1">Create your first project to get started</p>
                <Button
                  onClick={() => setCreateOpen(true)}
                  className="mt-4 bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]"
                >
                  New Project
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-[#2A3140] hover:bg-transparent">
                    <TableHead className="text-[#8B949E]">Project</TableHead>
                    <TableHead className="text-[#8B949E]">Customer</TableHead>
                    <TableHead className="text-[#8B949E]">Status</TableHead>
                    <TableHead className="text-[#8B949E]">Units</TableHead>
                    <TableHead className="text-[#8B949E]">Quote #</TableHead>
                    <TableHead className="text-[#8B949E]">Created</TableHead>
                    <TableHead className="text-[#8B949E] text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {projects.map((project) => (
                    <TableRow
                      key={project.id}
                      className="border-[#2A3140] hover:bg-[#2A3140]/50 cursor-pointer"
                      onClick={() => router.push(`/projects/${project.id}`)}
                    >
                      <TableCell className="font-medium text-[#E8E8E8]">
                        {project.projectName}
                      </TableCell>
                      <TableCell className="text-[#8B949E]">{project.customerName}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusBadgeClass(project.status)}`}>
                          {PROJECT_STATUS_LABELS[project.status] ?? project.status}
                        </span>
                      </TableCell>
                      <TableCell className="text-[#8B949E]">
                        {project._count?.units ?? 0}
                      </TableCell>
                      <TableCell className="text-[#8B949E]">
                        {project.quoteNumber ?? "—"}
                      </TableCell>
                      <TableCell className="text-[#8B949E]">
                        {new Date(project.createdAt).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[#F85149] hover:text-[#F85149] hover:bg-red-900/20"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteTarget(project);
                          }}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <DialogHeader>
            <DialogTitle className="text-[#E8E8E8]">New Project</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => createMutation.mutate(v))} className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Customer Name</Label>
              <Input
                {...register("customerName", { required: "Required" })}
                className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] placeholder:text-[#6E7681]"
                placeholder="e.g. Tel Aviv Office"
              />
              {errors.customerName && <p className="text-[#F85149] text-xs">{errors.customerName.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Project Name</Label>
              <Input
                {...register("projectName", { required: "Required" })}
                className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] placeholder:text-[#6E7681]"
                placeholder="e.g. HVAC Retrofit 2026"
              />
              {errors.projectName && <p className="text-[#F85149] text-xs">{errors.projectName.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Quote Number (optional)</Label>
              <Input
                {...register("quoteNumber")}
                className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] placeholder:text-[#6E7681]"
                placeholder="e.g. Q-2026-001"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-[#8B949E]">Notes (optional)</Label>
              <Input
                {...register("notes")}
                className="bg-[#181C22] border-[#2A3140] text-[#E8E8E8] placeholder:text-[#6E7681]"
                placeholder="Any additional notes..."
              />
            </div>
            {createMutation.error && (
              <p className="text-[#F85149] text-sm">{createMutation.error.message}</p>
            )}
            <DialogFooter>
              <Button
                type="button"
                variant="ghost"
                onClick={() => { setCreateOpen(false); reset(); }}
                className="text-[#8B949E] hover:text-[#E8E8E8]"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending}
                className="bg-[#E8A23D] text-[#181C22] hover:bg-[#d4922d]"
              >
                {createMutation.isPending ? "Creating..." : "Create Project"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent className="bg-[#1F252C] border-[#2A3140] text-[#E8E8E8]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[#E8E8E8]">Delete Project</AlertDialogTitle>
            <AlertDialogDescription className="text-[#8B949E]">
              Are you sure you want to delete &quot;{deleteTarget?.projectName}&quot;? This will permanently
              delete all associated units and sections. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#2A3140] text-[#E8E8E8] border-[#2A3140] hover:bg-[#2A3140]/80">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
              className="bg-[#F85149] text-white hover:bg-red-700"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete Project"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
