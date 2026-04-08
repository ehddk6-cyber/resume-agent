# Sources & Assumptions (CMPAA-13)

## Sources used

- `취업_ws/sources/normalized/` 하위 공공기관/준정부기관 지원 자료 파일명 및 본문 문맥
- 예시 파일(샘플 레코드에 직접 연결):
  - `linkareer_0038_한국자산관리공사_5급_금융일반_경영_2025_상반기.md`
  - `linkareer_0053_한국철도공사_사무영업일반_수도권_2024_하반기.md`
  - `linkareer_0097_한국주택금융공사_일반전형_비수도권_행정_2024_하반기.md`
  - `linkareer_0020_국민건강보험공단_행정직_6급가_2025_상반기.md`

## Assumptions

- 파일명 메타(기관명/직무명/연도/반기)가 누락되지 않았다고 가정
- 샘플 데이터는 파이프라인 연동 예시용으로, 통계적 대표 표본이 아님
- 직무군(`role_family`)은 실무 활용을 위해 상위 카테고리로 단순화
- confidence는 JD 명시도 + 문맥 일치도를 기준으로 연구자 휴리스틱 점수 부여

## Intended program input

- 레코드 단위 JSON Lines(`company_role_skill_sample.jsonl`)
- 스키마 검증 후 `skill_tags` 기준으로 집계/추천 파이프라인 연결
