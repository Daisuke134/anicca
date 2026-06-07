import { notFound } from "next/navigation";
import { getAllPosts, getPostBySlug } from "@/lib/blog";

export async function generateStaticParams() {
  return getAllPosts().map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: { slug: string } }) {
  const post = getPostBySlug(params.slug);
  if (!post) return {};
  return { title: `${post.title} | Anicca Blog`, description: post.excerpt };
}

export default function BlogPost({ params }: { params: { slug: string } }) {
  const post = getPostBySlug(params.slug);
  if (!post) notFound();
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-bold">{post.title}</h1>
      {post.date && <time className="text-sm text-gray-500">{post.date}</time>}
      <article className="prose mt-8 whitespace-pre-wrap">{post.content}</article>
    </main>
  );
}
