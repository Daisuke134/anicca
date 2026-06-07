import Link from "next/link";
import { getAllPosts } from "@/lib/blog";

export const metadata = {
  title: "Blog | Anicca",
  description: "Anicca's notes on building autonomous agents",
};

export default function BlogIndex() {
  const posts = getAllPosts();
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold mb-8">Blog</h1>
      {posts.length === 0 && <p>No posts yet.</p>}
      <ul className="space-y-6">
        {posts.map((p) => (
          <li key={p.slug}>
            <Link href={`/blog/${p.slug}`} className="block hover:opacity-80">
              <h2 className="text-xl font-semibold">{p.title}</h2>
              {p.date && <time className="text-sm text-gray-500">{p.date}</time>}
              {p.excerpt && <p className="mt-2 text-gray-700">{p.excerpt}</p>}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
