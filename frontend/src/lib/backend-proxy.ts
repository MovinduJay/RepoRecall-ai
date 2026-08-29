const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function backendRequest(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    return Response.json(
      { detail: "The RepoRecall API is unreachable." },
      { status: 503 },
    );
  }
}

export async function forwardResponse(response: Response): Promise<Response> {
  const body = await response.text();
  return new Response(body, {
    status: response.status,
    headers: { "Content-Type": response.headers.get("Content-Type") ?? "application/json" },
  });
}
