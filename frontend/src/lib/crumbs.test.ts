import { describe, expect, it } from "vitest";

import { buildCrumbs } from "@/lib/crumbs";

describe("buildCrumbs", () => {
  it("resolves top-level nav routes to titles", () => {
    expect(buildCrumbs("/")).toEqual([]);
    expect(buildCrumbs("/runs")).toEqual([{ label: "Runs", to: "/runs" }]);
    expect(buildCrumbs("/datasets")).toEqual([{ label: "Datasets", to: "/datasets" }]);
  });

  it("resolves nested nav routes and keeps parent links", () => {
    const crumbs = buildCrumbs("/runs/new");
    expect(crumbs[0]).toEqual({ label: "Runs", to: "/runs" });
    expect(crumbs[1]).toEqual({ label: "New Run", to: "/runs/new" });
  });

  it("leaves unknown / dynamic segments unlinked", () => {
    const crumbs = buildCrumbs("/runs/run%20abc");
    expect(crumbs[0]).toEqual({ label: "Runs", to: "/runs" });
    expect(crumbs[1].label).toBe("run abc");
    expect(crumbs[1].to).toBeUndefined();
  });
});
