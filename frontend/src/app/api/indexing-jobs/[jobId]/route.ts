import { backendRequest, forwardResponse } from "@/lib/backend-proxy";

export async function GET(_request: Request, context: RouteContext<"/api/indexing-jobs/[jobId]">) {
  const { jobId } = await context.params;
  return forwardResponse(await backendRequest(`/api/v1/indexing-jobs/${jobId}`));
}
