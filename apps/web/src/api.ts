export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("supplyrca-token");
  const response = await fetch("/api/v1" + path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-SupplyRCA-Client": "analyst",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message ??
        (body?.validation
          ? `Dataset quarantined: ${body.validation.errors.length} validation issues. See Data & validation.`
          : `Request failed (${response.status})`),
    );
  }
  return response.json() as Promise<T>;
}
export async function download(id: string, format: "markdown" | "json") {
  const token = sessionStorage.getItem("supplyrca-token");
  const response = await fetch(
    `/api/v1/investigations/${id}/export?format=${format}`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) throw new Error("Export failed. Check access and retry.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `supplyrca-${id}.${format === "json" ? "json" : "md"}`;
  link.click();
  URL.revokeObjectURL(url);
}
