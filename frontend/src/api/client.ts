export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getBaseUrl(): string {
  return import.meta.env.VITE_API_URL || "http://localhost:8000";
}

function parseDetail(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => JSON.stringify(item)).join("; ");
    }
  }
  return "Request failed";
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, init);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      message = parseDetail(await response.json());
    } catch {
      // ignore parse errors
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
