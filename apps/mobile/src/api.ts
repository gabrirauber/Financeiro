export type User = { id: string; email: string };
export type Workspace = { id: string; name: string; role: 'admin' | 'member' };
export type Member = User & { role: 'admin' | 'member' };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
export async function request<T>(path: string, token?: string, method = 'GET', body?: unknown): Promise<T> {
  const base = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');
  if (!base) throw new ApiError('Configure o endereço do servidor para continuar.', 0);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(base + path, {
      method, signal: controller.signal,
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (response.status === 204) return undefined as T;
    const result = await response.json();
    if (!response.ok) {
      const detail = result.detail;
      const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { message?: string }) => item.message || 'Confira os campos.').join(' ') : 'Não foi possível concluir. Tente novamente.';
      throw new ApiError(message, response.status);
    }
    return result as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('Não foi possível conectar. Verifique a internet e tente novamente.', 0);
  } finally { clearTimeout(timeout); }
}
