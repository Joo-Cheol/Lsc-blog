export default function ProgressHeader({
  title,
  step,
  total,
}: {
  title: string;
  step: number;
  total: number;
}) {
  const pct = Math.round((step / total) * 100);
  return (
    <div className="mb-4">
      <h2 className="text-2xl font-semibold">{title}</h2>
      <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-sm text-gray-600 mt-1">
        {step}/{total} 단계 진행 중
      </p>
    </div>
  );
}
