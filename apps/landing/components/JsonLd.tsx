// Minimal, build-safe JSON-LD injector for Next.js app-router (server & client).
// Usage: <JsonLd data={schemaObject} />  — renders one application/ld+json script.
export default function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      // schema is author-controlled (no user input) → safe to inline
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
