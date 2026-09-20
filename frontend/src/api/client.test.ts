import { describe, expect, it } from "vitest";

import { ApiError, buildUrl, getBaseUrl, toApiError } from "@/api/client";

describe("api client", () => {
  it("resolves the base url without a trailing slash", () => {
    expect(getBaseUrl()).toMatch(/^https?:\/\//);
    expect(getBaseUrl().endsWith("/")).toBe(false);
  });

  it("builds urls from relative and absolute paths", () => {
    expect(buildUrl("/runs")).toBe(`${getBaseUrl()}/runs`);
    expect(buildUrl("runs")).toBe(`${getBaseUrl()}/runs`);
  });

  it("passes ApiError through unchanged", () => {
    const original = new ApiError("boom", "Custom", 500);
    expect(toApiError(original)).toBe(original);
  });

  it("wraps plain errors preserving the message", () => {
    const wrapped = toApiError(new Error("network down"));
    expect(wrapped).toBeInstanceOf(ApiError);
    expect(wrapped.message).toBe("network down");
    expect(wrapped.kind).toBe("ApiError");
  });

  it("falls back for non-error throwables", () => {
    expect(toApiError("nope").message).toBe("Request failed.");
    expect(toApiError("nope", "Custom fallback").message).toBe("Custom fallback");
  });
});
