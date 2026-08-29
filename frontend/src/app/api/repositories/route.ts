import { backendRequest, forwardResponse } from "@/lib/backend-proxy";

type Repository = {
  id: string;
  github_url: string;
};

export async function GET() {
  return forwardResponse(await backendRequest("/api/v1/repositories"));
}

export async function POST(request: Request) {
  const body = await request.text();
  const response = await backendRequest("/api/v1/repositories", { method: "POST", body });

  if (response.status !== 409) return forwardResponse(response);

  const requested = JSON.parse(body) as { github_url?: string };
  const listResponse = await backendRequest("/api/v1/repositories");
  if (!listResponse.ok) return forwardResponse(response);

  const repositories = (await listResponse.json()) as Repository[];
  const normalizedUrl = requested.github_url?.trim().replace(/\.git\/?$/, "").replace(/\/$/, "");
  const existing = repositories.find((repository) => repository.github_url === normalizedUrl);
  if (!existing) return forwardResponse(response);

  return Response.json({ ...existing, existing: true });
}
