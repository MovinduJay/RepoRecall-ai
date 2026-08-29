import { backendRequest, forwardResponse } from "@/lib/backend-proxy";

export async function POST(request: Request) {
  const body = await request.text();
  return forwardResponse(
    await backendRequest("/api/v1/search/investigate", { method: "POST", body }),
  );
}
