import { CheckCircle, Circle, Database, Search, Play, FileText } from "lucide-react";

interface ProgressHeaderProps {
  title: string;
  step: number;
  total: number;
  message?: string;
}

const stepIcons = [
  { icon: Play, label: "수집" },
  { icon: Database, label: "정리" },
  { icon: Search, label: "검색" },
  { icon: CheckCircle, label: "완료" }
];

export default function ProgressHeader({ title, step, total, message }: ProgressHeaderProps) {
  const progress = (step / total) * 100;

  return (
    <div className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-200 mb-8 p-4 -mx-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="h-6 w-6 text-blue-600" />
            {title}
          </h1>
          <span className="text-sm text-gray-500 font-medium">
            {step} / {total} 단계
          </span>
        </div>
        
        {/* 단계별 아이콘 */}
        <div className="flex items-center justify-between mb-3">
          {stepIcons.slice(0, total).map((stepInfo, index) => {
            const stepNumber = index + 1;
            const isCompleted = stepNumber < step;
            const isCurrent = stepNumber === step;
            const Icon = stepInfo.icon;
            
            return (
              <div key={stepNumber} className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center mb-1 ${
                  isCompleted 
                    ? 'bg-green-500 text-white' 
                    : isCurrent 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-200 text-gray-500'
                }`}>
                  {isCompleted ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <span className={`text-xs font-medium ${
                  isCompleted || isCurrent ? 'text-gray-900' : 'text-gray-500'
                }`}>
                  {stepInfo.label}
                </span>
              </div>
            );
          })}
        </div>
        
        {/* 진행률 바 */}
        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
        
        {message && (
          <p className="text-sm text-gray-600">{message}</p>
        )}
      </div>
    </div>
  );
}
