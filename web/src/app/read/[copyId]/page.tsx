import { Studio } from "@/components/Studio";

export default async function ReadPage({ params }: { params: Promise<{ copyId: string }> }) {
  const { copyId } = await params;
  return <Studio copyId={copyId} />;
}
