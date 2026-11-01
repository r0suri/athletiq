import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <main className="mx-auto max-w-sm px-5 py-24">
      <h1 className="text-3xl font-semibold">Page not found</h1>
      <p className="mt-2 text-muted">That address doesn't match any page in AthletIQ.</p>
      <Link to="/" className="mt-6 inline-block text-action underline-offset-4 hover:underline">
        Go to your overview
      </Link>
    </main>
  );
}
