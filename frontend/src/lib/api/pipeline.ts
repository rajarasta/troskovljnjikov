import { fetchAPI } from "./client";

export async function startPipeline(fileId: string): Promise<{ pipeline_id: string }> {
  return fetchAPI<{ pipeline_id: string }>("/api/pipeline/start", {
    method: "POST",
    body: JSON.stringify({ file_id: fileId }),
  });
}
