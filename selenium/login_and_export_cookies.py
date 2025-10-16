# src/login_and_export_cookies.py
import json, os, tempfile, shutil, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

# chromedriver 경로 (프로젝트 구조에 맞게 조정)
CHROMEDRIVER = os.path.join(os.path.dirname(__file__), "chromedriver.exe")

def main():
    tmp_profile = tempfile.mkdtemp(prefix="naver_login_")
    print("[INFO] 임시 프로필:", tmp_profile)

    opts = webdriver.ChromeOptions()
    opts.add_argument(f"--user-data-dir={tmp_profile}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    service = Service(CHROMEDRIVER)
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        # 네이버 로그인 페이지로 이동
        driver.get("https://nid.naver.com/nidlogin.login")
        print("\n[ACTION] 브라우저에서 직접 로그인하세요. (로그인 유지 체크)")
        print("        로그인 완료 후, 이 콘솔에 엔터(Enter)를 눌러 주세요.")
        input()

        # 로그인 후 네이버 메인 한 번 접속(쿠키 안정화)
        driver.get("https://www.naver.com")
        time.sleep(2)

        # 현재 도메인/하위도메인 쿠키 모두 긁기
        # 중요한 건 .naver.com 쿠키(NID_AUT/NID_SES 등)
        cookies = driver.get_cookies()

        out_path = os.path.join(os.path.expanduser("~"), "cookies.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"\n[SAVED] 쿠키를 저장했습니다: {out_path}")
        print("       이 파일을 크롤러가 재사용합니다.")
    finally:
        driver.quit()
        shutil.rmtree(tmp_profile, ignore_errors=True)

if __name__ == "__main__":
    main()
