import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunStatusBadge, StageStatusBadge } from "@/components/ui/status-badge";

describe("status badges", () => {
  it("renders a run status with its label", () => {
    render(<RunStatusBadge status="completed" />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("renders every run status label without throwing", () => {
    for (const [status, label] of [
      ["queued", "Queued"],
      ["running", "Running"],
      ["completed", "Completed"],
      ["failed", "Failed"],
    ] as const) {
      const { unmount } = render(<RunStatusBadge status={status} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });

  it("renders stage statuses", () => {
    render(<StageStatusBadge status="warning" />);
    expect(screen.getByText("Warning")).toBeInTheDocument();
  });
});
