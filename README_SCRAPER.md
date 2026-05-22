# X (Twitter) Scraper & Automation

이 프로젝트는 특정 X 계정의 포스트를 자동으로 수집하고 GitHub에 저장합니다.

## 1. 로컬 실행 방법

1.  **가상 환경 활성화**: `source venv/bin/activate`
2.  **계정 정보 입력**: `credentials.json` 파일에 정보 입력
3.  **실행**: `python3 scrape_x.py`

## 2. GitHub Actions 자동화 (매일 실행)

이 프로젝트는 GitHub Actions를 통해 매일 자정에 자동으로 실행되도록 설정되어 있습니다.

### 설정 방법:

1.  **GitHub Repository 생성**: 본인의 GitHub에 새 저장소를 만듭니다.
2.  **Secrets 설정**:
    *   GitHub 저장소의 `Settings` > `Secrets and variables` > `Actions`로 이동합니다.
    *   `New repository secret` 버튼을 눌러 다음 3개를 추가합니다:
        *   `X_USERNAME`: X 아이디
        *   `X_EMAIL`: X 등록 이메일
        *   `X_PASSWORD`: X 비밀번호
3.  **코드 푸시**:
    ```bash
    git init
    git add .
    git commit -m "Initial commit with automation"
    git branch -M main
    git remote add origin <본인의_repo_url>
    git push -u origin main
    ```

### 자동화 동작:
*   **스케줄**: 매일 자정(UTC)에 자동으로 실행됩니다.
*   **저장**: 수집된 데이터(`wendys_posts.json`)와 세션 쿠키(`cookies.json`)가 자동으로 커밋되어 저장소에 업데이트됩니다.
*   **수동 실행**: GitHub Actions 탭에서 `Run workflow` 버튼을 눌러 즉시 실행할 수도 있습니다.

## 주의 사항
*   **계정 잠김**: GitHub Actions의 서버 IP가 평소와 달라 X에서 '의심스러운 로그인'으로 판단할 수 있습니다. 이 경우 이메일 인증이 필요할 수 있습니다.
*   **보안**: `credentials.json`은 절대 GitHub에 올리지 마세요. (이미 `.gitignore`에 포함되어 있어야 함)
