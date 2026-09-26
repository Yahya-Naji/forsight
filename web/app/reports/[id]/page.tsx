import { supabase } from "../../../lib/supabase";
import ReactMarkdown from "react-markdown";
import { label } from "../../../components/chips";

export const revalidate = 0;
export const dynamic = "force-dynamic";

export default async function Report({ params }: { params: { id: string } }) {
  const { data } = await supabase.from("reports").select("*").eq("id", params.id).single();
  if (!data) return <p>Not found.</p>;
  return (
    <article style={{ background: "#fff", border: "1px solid #D5DEF5", borderRadius: 10, padding: 28 }}>
      <div style={{ color: "#666", fontSize: 13 }}>Status: {label(data.status)}</div>
      <ReactMarkdown>{data.body_md ?? ""}</ReactMarkdown>
    </article>
  );
}
