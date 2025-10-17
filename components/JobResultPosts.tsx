import Link from "next/link";

export default function JobResultPosts({
  posts,
}: {
  posts?: { title: string; url: string; logno?: string }[];
}) {
  if (!posts?.length) return null;
  return (
    <div className="mt-4">
      <h4 className="font-medium mb-2">이번에 수집한 글 ({posts.length})</h4>
      <ul className="space-y-1">
        {posts.map((p, i) => (
          <li key={i} className="text-sm">
            •{" "}
            <Link
              href={p.url}
              target="_blank"
              className="text-blue-600 hover:underline"
            >
              {p.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
