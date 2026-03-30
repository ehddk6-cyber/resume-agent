# Codex 실행 실패 (폴백 출력)

## 안내
Codex CLI 실행이 3회 실패했습니다.

### 해결 방법
1. `codex` CLI가 설치되어 있고 PATH에 등록되어 있는지 확인하세요.
   - 설치: `npm install -g @openai/codex`
2. 네트워크 연결 상태를 확인하세요.
3. 프롬프트 파일(`취업_ws/outputs/latest_draft_prompt.md`)의 크기가 토큰 한도를 초과하지 않는지 확인하세요.
4. 수동으로 Codex를 실행해 보세요:
   ```
   codex exec --skip-git-repo-check -C 취업_ws -o 취업_ws/runs/20260327_021803/raw_writer.md - < 취업_ws/outputs/latest_draft_prompt.md
   ```
5. 다른 CLI 도구를 사용해 보세요: `--tool claude` 또는 `--tool gemini`
