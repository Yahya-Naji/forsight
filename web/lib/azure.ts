// The one place the web app talks to a model — mirrors pipeline/llm.py so the
// console and the pipeline use the same provider and deployments.
const env = (n: string) => {
  const v = process.env[n];
  return v && v.trim() ? v.trim() : undefined;
};

const endpoint = () => (env("AZURE_OPENAI_ENDPOINT") ?? "").split("/openai/")[0].replace(/\/$/, "");
const apiVersion = () => {
  const raw = env("AZURE_OPENAI_ENDPOINT") ?? "";
  if (raw.includes("api-version=")) return raw.split("api-version=")[1].split("&")[0];
  return env("AZURE_OPENAI_API_VERSION") ?? "2025-04-01-preview";
};

export const hasModel = () => Boolean(env("AZURE_OPENAI_KEY") && endpoint());

export type Msg = { role: "system" | "user" | "assistant"; content: string };

/** Plain completion. Returns null when unconfigured so callers degrade rather than throw. */
export async function complete(
  messages: Msg[],
  opts: { fast?: boolean; maxTokens?: number } = {}
): Promise<string | null> {
  if (!hasModel()) return null;
  const deployment = opts.fast
    ? env("AZURE_OPENAI_DEPLOYMENT_FAST") ?? env("AZURE_OPENAI_DEPLOYMENT")
    : env("AZURE_OPENAI_DEPLOYMENT");
  if (!deployment) return null;

  const instructions = messages.filter(m => m.role === "system").map(m => m.content).join("\n\n");
  const input = messages
    .filter(m => m.role !== "system")
    .map(m => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
    .join("\n\n");

  const res = await fetch(`${endpoint()}/openai/responses?api-version=${apiVersion()}`, {
    method: "POST",
    headers: { "api-key": env("AZURE_OPENAI_KEY")!, "Content-Type": "application/json" },
    body: JSON.stringify({
      model: deployment,
      instructions: instructions || undefined,
      input,
      max_output_tokens: opts.maxTokens ?? 4000,
    }),
  });
  if (!res.ok) return null;
  const j = await res.json();
  if (typeof j.output_text === "string" && j.output_text) return j.output_text;
  let out = "";
  for (const item of j.output ?? []) for (const c of item.content ?? []) out += c.text ?? "";
  return out || null;
}
