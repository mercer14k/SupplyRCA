import { describe, expect, it } from "vitest";
import { formatKpi } from "./types";
describe("KPI presentation", () => {
  it("preserves undefined denominators", () =>
    expect(formatKpi(null, "fill_rate")).toBe("Undefined"));
  it("distinguishes days from percentages", () => {
    expect(formatKpi(0.6484, "fill_rate")).toBe("64.8%");
    expect(formatKpi(7.25, "lead_time")).toBe("7.25 days");
  });
  it("shows negative forecast accuracy instead of silently clipping", () =>
    expect(formatKpi(-0.2, "forecast_accuracy")).toBe("-20.0%"));
});
