import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BRAIN_HARNESS_LABELS } from "@/lib/agentLabels";
import type { AgentBundleInput } from "@/lib/agentBundle";

/**
 * Harness options for the picker. "default" uses the server's default
 * executor (no explicit harness in the bundle).
 */
const HARNESS_OPTIONS: { value: string; label: string }[] = [
  { value: "default", label: "Default" },
  ...Object.entries(BRAIN_HARNESS_LABELS).map(([value, label]) => ({ value, label })),
];

/**
 * Dialog for creating a custom agent from the new-session picker.
 *
 * Collects a name, optional description, optional system instructions,
 * and a harness choice. On submit, passes the agent configuration back
 * to the parent via `onCreate` so it can build a bundle and start a
 * session with it.
 */
export function CreateAgentDialog({
  open,
  onOpenChange,
  onCreate,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: AgentBundleInput) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [harness, setHarness] = useState("default");

  function reset() {
    setName("");
    setDescription("");
    setInstructions("");
    setHarness("default");
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset();
    onOpenChange(next);
  }

  function handleSubmit() {
    const trimmedName = name.trim();
    if (!trimmedName) return;

    onCreate({
      name: trimmedName,
      description: description.trim() || undefined,
      instructions: instructions.trim() || undefined,
      harness: harness === "default" ? undefined : harness,
    });
    reset();
    onOpenChange(false);
  }

  const canSubmit = name.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        data-testid="create-agent-dialog"
        className="flex max-h-[85vh] flex-col gap-4 sm:max-w-lg"
      >
        <DialogHeader>
          <DialogTitle>Create custom agent</DialogTitle>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto">
          {/* Name */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="create-agent-name" className="text-xs font-medium text-muted-foreground">
              Name <span className="text-destructive">*</span>
            </label>
            <Input
              id="create-agent-name"
              data-testid="create-agent-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-agent"
              autoFocus
            />
          </div>

          {/* Description */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="create-agent-description"
              className="text-xs font-medium text-muted-foreground"
            >
              Description
            </label>
            <Input
              id="create-agent-description"
              data-testid="create-agent-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A short summary of what this agent does"
            />
          </div>

          {/* Harness */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">Harness</label>
            <Select value={harness} onValueChange={setHarness}>
              <SelectTrigger data-testid="create-agent-harness" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {HARNESS_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Instructions / System Prompt */}
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="create-agent-instructions"
              className="text-xs font-medium text-muted-foreground"
            >
              System instructions
            </label>
            <Textarea
              id="create-agent-instructions"
              data-testid="create-agent-instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="You are a helpful assistant that..."
              className="min-h-[120px]"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button data-testid="create-agent-submit" onClick={handleSubmit} disabled={!canSubmit}>
            Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
