# 🚀 구글 Gemini API 설정 가이드

## 🔑 API 키 발급 및 설정

### 1. **구글 AI Studio에서 API 키 발급**
1. [Google AI Studio](https://aistudio.google.com/) 접속
2. Google 계정으로 로그인
3. "Get API Key" 클릭
4. 새 프로젝트 생성 또는 기존 프로젝트 선택
5. API 키 생성 및 복사

### 2. **환경변수 설정**

#### **Windows (PowerShell)**
```powershell
# 현재 세션용
$env:GEMINI_API_KEY="your-gemini-api-key-here"

# 영구 설정 (시스템 환경변수)
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "your-gemini-api-key-here", "User")
```

#### **Windows (CMD)**
```cmd
set GEMINI_API_KEY=your-gemini-api-key-here
```

#### **Linux/Mac**
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
echo 'export GEMINI_API_KEY="your-gemini-api-key-here"' >> ~/.bashrc
```

### 3. **설정 확인**
```bash
# Windows
echo $env:GEMINI_API_KEY

# Linux/Mac
echo $GEMINI_API_KEY
```

## 🚀 사용법

### **API 키가 설정된 경우:**
- B 파이프라인에서 **구글 Gemini**가 실제로 텍스트를 다듬습니다
- 한국어 처리에 뛰어난 성능
- 빠르고 정확한 결과

### **API 키가 없는 경우:**
- 자동으로 **Mock 모드**로 폴백됩니다
- 기본적인 문장 다듬기 규칙이 적용됩니다

## 💰 비용 정보

- **Gemini Pro**: 무료 할당량 제공 (월 60회 요청)
- **유료 사용**: 매우 저렴한 비용
- **예상 비용**: 블로그 1개당 약 $0.0005 미만

## 🔧 문제 해결

### **API 키 오류**
```
⚠️ GEMINI_API_KEY 환경변수가 설정되지 않았습니다.
```
→ 위의 환경변수 설정 방법을 따라하세요

### **API 호출 실패**
```
❌ Gemini API 오류: 401 - Unauthorized
```
→ API 키가 올바른지 확인하세요

### **타임아웃 오류**
```
⏰ Gemini API 타임아웃 - Mock 모드로 폴백
```
→ 네트워크 연결을 확인하거나 잠시 후 다시 시도하세요

## 🎯 테스트 방법

1. **API 키 설정 후 서버 재시작**
2. **웹에서 B 파이프라인 선택**
3. **블로그 생성 후 결과 확인**
4. **"B 파이프라인 (향상된 구글 Gemini)" 모드 표시 확인**

## 📊 성능 비교

| 모드 | 속도 | 품질 | 비용 | 한국어 |
|------|------|------|------|--------|
| A 파이프라인 | ⚡ 매우 빠름 | 📊 기본 | 💰 무료 | ✅ |
| B 파이프라인 (Mock) | ⚡ 빠름 | 📝 양호 | 💰 무료 | ✅ |
| B 파이프라인 (Gemini) | 🐌 보통 | ✨ 우수 | 💰 저렴 | 🌟 최고 |

## 🌟 Gemini의 장점

### **한국어 특화**
- 한국어 이해도가 뛰어남
- 법률 용어 처리 우수
- 자연스러운 문체 생성

### **빠른 응답**
- Google의 강력한 인프라
- 안정적인 서비스
- 낮은 지연시간

### **비용 효율성**
- 무료 할당량 제공
- 저렴한 유료 사용료
- 대량 처리 가능

---

**구글 Gemini API를 설정하면 더욱 자연스럽고 정확한 한국어 법률 블로그를 생성할 수 있습니다!** 🎉
