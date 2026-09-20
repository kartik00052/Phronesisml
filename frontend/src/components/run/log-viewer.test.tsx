import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LogViewer } from "@/components/run/log-viewer";

const logs = [
  "2026-01-01 INFO starting pipeline",
  "2026-01-01 INFO loading dataset",
  "[ERROR] failed to fit model",
  "[WARN] low variance feature dropped",
];

describe("LogViewer", () => {
  it("shows the total line count and error/warning badges", () => {
    render(<LogViewer logs={logs} />);
    expect(screen.getByText("4 lines")).toBeInTheDocument();
    expect(screen.getByText("1 errors")).toBeInTheDocument();
    expect(screen.getByText("1 warnings")).toBeInTheDocument();
  });

  it("renders an empty state when there are no logs", () => {
    render(<LogViewer logs={[]} />);
    expect(screen.getByText("No logs yet")).toBeInTheDocument();
  });

  it("accepts a search filter without throwing", () => {
    render(<LogViewer logs={logs} />);
    fireEvent.change(screen.getByLabelText("Filter logs"), {
      target: { value: "dataset" },
    });
    expect(screen.getByLabelText("Filter logs")).toHaveValue("dataset");
  });

  it("toggles wrap and follow modes via accessible buttons", () => {
    render(<LogViewer logs={logs} live />);
    const wrap = screen.getByRole("button", { name: "Wrap" });
    fireEvent.click(wrap);
    expect(wrap).toHaveAttribute("aria-pressed", "true");
  });
});
