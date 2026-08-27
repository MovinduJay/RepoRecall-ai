const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export type ApiHealth = {
  status: "ok";
};

export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export async function getApiHealth(): Promise<ApiHealth> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/health`, { cache: "no-store" });
  } catch {
    throw new ApiRequestError("The RepoRecall API is unreachable.");
  }

  if (!response.ok) {
    throw new ApiRequestError("The RepoRecall API health check failed.", response.status);
  }

  return (await response.json()) as ApiHealth;
}
