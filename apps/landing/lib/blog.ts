import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";

const POSTS_DIR = path.join(process.cwd(), "content", "blog");

export type BlogPost = {
  slug: string;
  title: string;
  date: string;
  excerpt?: string;
  content: string;
};

function extractH1Title(content: string): string | null {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : null;
}

function extractFirstParagraph(content: string): string {
  const withoutH1 = content.replace(/^#\s+.+$/m, "").trim();
  const firstPara = withoutH1.split(/\n\n/)[0]?.trim() ?? "";
  return firstPara.replace(/^#+\s+/, "").slice(0, 200);
}

export function getAllPosts(): BlogPost[] {
  if (!fs.existsSync(POSTS_DIR)) return [];
  const files = fs.readdirSync(POSTS_DIR).filter((f) => f.endsWith(".md"));
  const posts = files.map((file) => {
    const slug = file.replace(/\.md$/, "");
    const raw = fs.readFileSync(path.join(POSTS_DIR, file), "utf8");
    const { data, content } = matter(raw);
    const title = (data.title as string) || extractH1Title(content) || slug;
    return {
      slug,
      title,
      date: (data.date as string) || "",
      excerpt: (data.excerpt as string) || extractFirstParagraph(content),
      content,
    };
  });
  return posts.sort((a, b) => b.date.localeCompare(a.date));
}

export function getPostBySlug(slug: string): BlogPost | null {
  const file = path.join(POSTS_DIR, `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  const { data, content } = matter(raw);
  const title = (data.title as string) || extractH1Title(content) || slug;
  return {
    slug,
    title,
    date: (data.date as string) || "",
    excerpt: (data.excerpt as string) || extractFirstParagraph(content),
    content,
  };
}
