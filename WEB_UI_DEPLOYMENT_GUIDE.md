# 🚀 **웹 UI 배포 가이드**

## 📦 **생성된 파일들**

다음 파일들이 이미 생성되어 있습니다:

### **핵심 파일들**
- `package.json` - 의존성 정의
- `app/layout.tsx` - 메인 레이아웃
- `app/page.tsx` - 검색 페이지
- `app/generate/page.tsx` - 생성 페이지  
- `app/ops/page.tsx` - 운영 페이지
- `components/` - UI 컴포넌트들
- `lib/` - API 클라이언트 및 타입 정의

## 🔧 **배포 방법**

### **방법 1: Vercel (권장)**
1. https://vercel.com 에서 계정 생성
2. GitHub에 코드 업로드
3. Vercel에서 프로젝트 연결
4. 자동 배포 완료

### **방법 2: Netlify**
1. https://netlify.com 에서 계정 생성
2. 드래그 앤 드롭으로 폴더 업로드
3. 빌드 설정: `npm run build`
4. 배포 완료

### **방법 3: 로컬 개발 (Node.js 설치 후)**
```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 브라우저에서 http://localhost:3000 접속
```

## ⚙️ **환경 변수 설정**

배포 시 다음 환경 변수를 설정하세요:

```bash
# API 엔드포인트
NEXT_PUBLIC_LSC_API_BASE=https://your-api-domain.com

# API 키 (선택사항)
NEXT_PUBLIC_LSC_API_KEY=your-api-key
```

## 🔗 **백엔드 연동**

백엔드 FastAPI 서버의 CORS 설정에 프론트엔드 도메인을 추가하세요:

```python
# src/app/main.py
origins = [
    "https://your-frontend-domain.vercel.app",
    "http://localhost:3000"  # 개발용
]
```

## 🎯 **완성된 기능들**

✅ **검색 페이지** - RAG 검색 + 하이브리드 옵션
✅ **생성 페이지** - 블로그 생성 + QC 표시 + 다운로드
✅ **운영 페이지** - 스케줄러 상태 + 메트릭 링크
✅ **반응형 디자인** - 모바일/데스크톱 지원
✅ **타입 안전성** - TypeScript 완전 지원

## 🚀 **즉시 사용 가능**

모든 파일이 준비되어 있으므로, Node.js만 설치되면 바로 실행 가능합니다!









