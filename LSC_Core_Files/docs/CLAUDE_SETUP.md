# 🧠 재미나이(Claude) API 설정 가이드

## 🔑 API 키 발급 및 설정

### 1. **재미나이 API 키 발급**
1. [Anthropic Console](https://console.anthropic.com/) 접속
2. 계정 생성/로그인
3. API Keys 메뉴에서 새 키 생성
4. API 키 복사 (sk-ant-... 형태)

### 2. **환경변수 설정**

#### **Windows (PowerShell)**
```powershell
# 현재 세션용
$env:CLAUDE_API_KEY="sk-ant-your-api-key-here"

# 영구 설정 (시스템 환경변수)
[Environment]::SetEnvironmentVariable("CLAUDE_API_KEY", "sk-ant-your-api-key-here", "User")
```

#### **Windows (CMD)**
```cmd
set CLAUDE_API_KEY=sk-ant-your-api-key-here
```

#### **Linux/Mac**
```bash
export CLAUDE_API_KEY="sk-ant-your-api-key-here"
echo 'export CLAUDE_API_KEY="sk-ant-your-api-key-here"' >> ~/.bashrc
```

### 3. **설정 확인**
```bash
# Windows
echo $env:CLAUDE_API_KEY

# Linux/Mac
echo $CLAUDE_API_KEY
```

## 🚀 사용법

### **API 키가 설정된 경우:**
- B 파이프라인에서 **재미나이 Claude**가 실제로 텍스트를 다듬습니다
- 더 자연스럽고 전문적인 문체로 생성됩니다

### **API 키가 없는 경우:**
- 자동으로 **Mock 모드**로 폴백됩니다
- 기본적인 문장 다듬기 규칙이 적용됩니다

## 💰 비용 정보

- **Claude 3 Haiku**: 가장 저렴한 모델 사용
- **토큰당 비용**: 매우 저렴 (약 $0.25/1M 토큰)
- **예상 비용**: 블로그 1개당 약 $0.001 미만

## 🔧 문제 해결

### **API 키 오류**
```
⚠️ CLAUDE_API_KEY 환경변수가 설정되지 않았습니다.
```
→ 위의 환경변수 설정 방법을 따라하세요

### **API 호출 실패**
```
❌ Claude API 오류: 401 - Unauthorized
```
→ API 키가 올바른지 확인하세요

### **타임아웃 오류**
```
⏰ Claude API 타임아웃 - Mock 모드로 폴백
```
→ 네트워크 연결을 확인하거나 잠시 후 다시 시도하세요

## 🎯 테스트 방법

1. **API 키 설정 후 서버 재시작**
2. **웹에서 B 파이프라인 선택**
3. **블로그 생성 후 결과 확인**
4. **"B 파이프라인 (재미나이 Claude)" 모드 표시 확인**

## 📊 성능 비교

| 모드 | 속도 | 품질 | 비용 |
|------|------|------|------|
| A 파이프라인 | ⚡ 매우 빠름 | 📊 기본 | 💰 무료 |
| B 파이프라인 (Mock) | ⚡ 빠름 | 📝 양호 | 💰 무료 |
| B 파이프라인 (Claude) | 🐌 보통 | ✨ 우수 | 💰 저렴 |

---

**재미나이 Claude API를 설정하면 더욱 자연스럽고 전문적인 블로그를 생성할 수 있습니다!** 🎉
