export type HealthDto = {
  data: { service: string; version: string; status: string; timestamp: string };
};

export type DemoDto = {
  data: {
    evaluation_id: string;
    title: string;
    status: string;
    requirements: Array<{ id: string; text: string; category: string }>;
    vendors: Array<{ vendor_id: string; name: string }>;
    matrix: Array<{ requirement_id: string; vendor_id: string; state: string; confidence: number; source_pointers: Array<{ document_id: string; page?: number; locator: string }>; conflict_pairs?: Array<{ left: string; right: string }> }>;
  };
};

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { accept: 'application/json', ...(init?.headers ?? {}) },
  });
  if (!response.ok) throw new Error(`API request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthDto>('/api/v1/health'),
  demo: () => request<DemoDto>('/api/v1/demo'),
};
