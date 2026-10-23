export type User = { id: string; email: string; access_admin: boolean; demo: boolean; onboarding_step: number };
export type Workspace = { id: string; name: string; role: 'admin' | 'member' };
export type Member = User & { role: 'admin' | 'member' };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

async function attempt<T>(base: string, path: string, token: string | undefined, method: string, body: unknown): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(base + path, {
      method, signal: controller.signal,
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (response.status === 204) return undefined as T;
    // Gateway error pages may contain HTML instead of the API's JSON response.
    const result = await response.json().catch(error => {
      if (controller.signal.aborted || (error instanceof Error && error.name === 'AbortError')) throw error;
      return null;
    });
    if (!response.ok) {
      const detail = result?.detail;
      const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { message?: string }) => item.message || 'Confira os campos.').join(' ') :
        response.status >= 500 ? 'Servidor temporariamente indisponível. Tente novamente.' : 'Não foi possível concluir. Tente novamente.';
      throw new ApiError(message, response.status);
    }
    if (result === null) throw new ApiError('O servidor retornou uma resposta inválida. Tente novamente.', response.status);
    return result as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted || (error instanceof Error && error.name === 'AbortError'))
      throw new ApiError('O servidor demorou para responder. Tente novamente.', 0);
    throw new ApiError('Não foi possível conectar. Verifique a internet e tente novamente.', 0);
  } finally { clearTimeout(timeout); }
}

export async function request<T>(path: string, token?: string, method = 'GET', body?: unknown): Promise<T> {
  const base = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/+$/, '');
  if (!base) throw new ApiError('Configure o endereço do servidor para continuar.', 0);
  const verb = method.toUpperCase();
  try { return await attempt<T>(base, path, token, verb, body); }
  catch (error) {
    // Retry only reads, once. Never repeat payments, purchases or login submissions.
    if (verb !== 'GET' || !(error instanceof ApiError) || ![0, 502, 503, 504].includes(error.status)) throw error;
    await new Promise(resolve => setTimeout(resolve, 300));
    return attempt<T>(base, path, token, verb, body);
  }
}
