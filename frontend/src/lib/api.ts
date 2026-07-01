// Frontend API client wrapper

const API_BASE = typeof window !== "undefined" 
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1") 
  : (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1");

interface FetchOptions extends RequestInit {
  token?: string;
}

class ApiClient {
  private getHeaders(token?: string, isMultipart: boolean = false): HeadersInit {
    const headers: Record<string, string> = {};
    if (!isMultipart) {
      headers["Content-Type"] = "application/json";
    }
    
    const authToken = token || (typeof window !== "undefined" ? localStorage.getItem("token") : null);
    if (authToken) {
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    return headers;
  }

  async get<T>(path: string, options: FetchOptions = {}): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "GET",
      headers: this.getHeaders(options.token),
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "An error occurred" }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  async post<T>(path: string, body: any, options: FetchOptions = {}): Promise<T> {
    const isMultipart = body instanceof FormData;
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: this.getHeaders(options.token, isMultipart),
      body: isMultipart ? body : JSON.stringify(body),
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "An error occurred" }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  async put<T>(path: string, body: any, options: FetchOptions = {}): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PUT",
      headers: this.getHeaders(options.token),
      body: JSON.stringify(body),
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "An error occurred" }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }

  async delete<T>(path: string, options: FetchOptions = {}): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(options.token),
      ...options
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "An error occurred" }));
      throw new Error(err.detail || "Request failed");
    }
    return res.json();
  }
}

export const api = new ApiClient();
export default api;
