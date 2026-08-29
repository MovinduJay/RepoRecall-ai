import { backendRequest, forwardResponse } from "@/lib/backend-proxy";

export async function POST(request: Request, context: RouteContext<"/api/repositories/[repositoryId]/sync">) {
  const { repositoryId } = await context.params;
  const body = await request.text();
  return forwardResponse(
    await backendRequest(`/api/v1/repositories/${repositoryId}/sync`, {
      method: "POST",
      body: body || JSON.stringify({ max_items_per_source: 200 }),
    }),
  );
}
