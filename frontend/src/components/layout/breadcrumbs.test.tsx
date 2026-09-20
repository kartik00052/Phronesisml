import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Breadcrumbs } from "@/components/layout/breadcrumbs";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Breadcrumbs />
    </MemoryRouter>,
  );
}

describe("Breadcrumbs", () => {
  it("renders nothing on the dashboard root", () => {
    const { container } = renderAt("/");
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a linked parent and the current page", () => {
    renderAt("/runs/new");
    const runs = screen.getByRole("link", { name: "Runs" });
    expect(runs).toHaveAttribute("href", "/runs");
    expect(screen.getByText("New Run")).toHaveAttribute("aria-current", "page");
  });

  it("renders unlinked dynamic run ids", () => {
    renderAt("/runs/run-42");
    expect(screen.getByText("run-42")).toHaveAttribute("aria-current", "page");
  });
});
