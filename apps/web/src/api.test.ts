import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});
describe("API boundary", () => {
  it("surfaces structured errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({ error: { message: "Missing baseline" } }),
      }),
    );
    await expect(api("/investigations")).rejects.toThrow("Missing baseline");
  });
  it("sends mutation guard and session token", async () => {
    sessionStorage.setItem("supplyrca-token", "test-token");
    const fetch = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
    vi.stubGlobal("fetch", fetch);
    await api("/investigations", { method: "POST" });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/investigations",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-SupplyRCA-Client": "analyst",
          Authorization: "Bearer test-token",
        }),
      }),
    );
  });
});
