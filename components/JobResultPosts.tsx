import Link from "next/link";
import { ExternalLink, FileText } from "lucide-react";

interface JobResultPostsProps {
  posts?: { title: string; url: string; logno?: string; content?: string }[];
  showPreview?: boolean;
}

export default function JobResultPosts({ posts, showPreview = true }: JobResultPostsProps) {
  if (!posts?.length) return null;

  const truncateText = (text: string, maxLength: number = 80) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  return (
    <div className="mt-4">
      <h4 className="font-medium mb-3 flex items-center gap-2">
        <FileText className="h-4 w-4" />
        이번에 수집한 글 ({posts.length}개)
      </h4>
      <div className="space-y-3 max-h-60 overflow-y-auto">
        {posts.map((post, index) => (
          <div key={index} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
                  #{index + 1}
                </span>
                {post.logno && (
                  <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded">
                    #{post.logno}
                  </span>
                )}
              </div>
              <Link 
                href={post.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-gray-600 transition-colors"
                title="원문 보기"
              >
                <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
            
            <h5 className="text-sm font-medium text-gray-900 mb-2 line-clamp-2">
              {post.title}
            </h5>
            
            {showPreview && post.content && (
              <p className="text-xs text-gray-600 leading-relaxed">
                {truncateText(post.content)}
              </p>
            )}
            
            <div className="mt-2 pt-2 border-t border-gray-200">
              <Link 
                href={post.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 font-medium"
              >
                원문 읽기 →
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
