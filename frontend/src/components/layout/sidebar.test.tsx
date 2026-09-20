import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";
import { NAV_SECTIONS } from "@/config/navigation";

describe("Sidebar", () => {
  it("renders every nav section and item when expanded", () => {
    render(
      <MemoryRouter initialEntries={["/runs"]}>
        <Sidebar collapsed={false} />
      </MemoryRouter>,
    );

    for (const section of NAV_SECTIONS) {
      expect(screen.getByText(section.label)).toBeInTheDocument();
    }
    expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /datasets/i })).toHaveAttribute("href", "/datasets");
    expect(screen.getAllByRole("link", { name: /runs/i }).length).toBeGreaterThan(0);
  });

  it("hides labels when collapsed", () => {
    render(
      <MemoryRouter>
        <TooltipProvider>
          <Sidebar collapsed />
        </TooltipProvider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("Datasets")).not.toBeInTheDocument();
  });
});
