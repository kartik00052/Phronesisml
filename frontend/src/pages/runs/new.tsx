import { NewRunWizard } from "@/components/new-run/wizard";
import { PageHeader } from "@/components/layout/page-header";

export default function NewRunPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="New Run"
        description="Configure the agentic AutoML pipeline — the platform detects the task, engineers features, and tunes models automatically."
      />
      <NewRunWizard />
    </div>
  );
}