"""
자동 품질 평가 시스템 - 작성된 자기소개서의 품질을 자동으로 평가
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class QualityDimension(Enum):
    """품질 평가 차원"""
    RELEVANCE = "relevance"        # 관련성
    SPECIFICITY = "specificity"    # 구체성
    LOGIC = "logic"                # 논리성
    ORIGINALITY = "originality"    # 독창성
    READABILITY = "readability"    # 가독성
    PERSUASIVENESS = "persuasiveness"  # 설득력
    DEFENSIBILITY = "defensibility"    # 면접 방어 가능성
    COMPANY_FIT = "company_fit"        # 회사 적합성


@dataclass
class QualityScore:
    """품질 점수"""
    overall: float                           # 종합 점수 (0-100)
    details: Dict[str, float]                # 세부 점수
    feedback: List[str] = field(default_factory=list)  # 피드백
    suggestions: List[str] = field(default_factory=list)  # 개선 제안


class QualityEvaluator:
    """
    자동 품질 평가 엔진
    
    평가 차원:
    1. 관련성 - 질문과 답변의 일치도
    2. 구체성 - 수치, 지표 포함 여부
    3. 논리성 - STAR 구조 충실도
    4. 독창성 - 클리셰 및 표절 검출
    5. 가독성 - 문장 길이, 어휘 난이도
    """
    
    # 클리셰 패턴
    CLICHE_PATTERNS = [
        "최선을 다하겠습니다",
        "열정적으로 임하겠습니다",
        "팀원들과 소통하며",
        "맡은 바 책임을 다하겠습니다",
        "성실하게 근무하겠습니다",
        "항상 배우는 자세로",
        "도전을 두려워하지 않는",
        "창의적인 사고를 바탕으로",
        "글로벌 역량을 갖춘",
        "도전 정신으로"
    ]
    
    # 관련성 키워드 (질문 유형별)
    RELEVANCE_KEYWORDS = {
        "동기": ["지원", "동기", "관심", "열정", "목표"],
        "역량": ["경험", "성과", "능력", "기술", "역량"],
        "협업": ["팀", "협업", "소통", "조율", "함께"],
        "문제해결": ["문제", "해결", "개선", "분석", "결과"],
        "성장": ["학습", "성장", "발전", "도전", "경험"]
    }
    
    def evaluate_draft(
        self,
        draft: str,
        question: str,
        experience_context: Optional[str] = None
    ) -> QualityScore:
        """
        초안 품질 평가
        
        Args:
            draft: 평가할 초안
            question: 질문
            experience_context: 경험 컨텍스트 (선택)
        
        Returns:
            QualityScore 객체
        """
        scores = {}
        feedback = []
        suggestions = []
        
        # 1. 관련성 평가
        relevance_score, relevance_feedback = self._evaluate_relevance(draft, question)
        scores["relevance"] = relevance_score
        feedback.extend(relevance_feedback)
        
        # 2. 구체성 평가
        specificity_score, specificity_feedback = self._evaluate_specificity(draft)
        scores["specificity"] = specificity_score
        feedback.extend(specificity_feedback)
        
        # 3. 논리성 평가
        logic_score, logic_feedback = self._evaluate_logic(draft)
        scores["logic"] = logic_score
        feedback.extend(logic_feedback)
        
        # 4. 독창성 평가
        originality_score, originality_feedback = self._evaluate_originality(draft)
        scores["originality"] = originality_score
        feedback.extend(originality_feedback)
        
        # 5. 가독성 평가
        readability_score, readability_feedback = self._evaluate_readability(draft)
        scores["readability"] = readability_score
        feedback.extend(readability_feedback)

        # 6. 설득력 평가
        persuasiveness_score, persuasiveness_feedback = self._evaluate_persuasiveness(draft)
        scores["persuasiveness"] = persuasiveness_score
        feedback.extend(persuasiveness_feedback)

        # 7. 면접 방어 가능성 평가
        defensibility_score, defensibility_feedback = self._evaluate_defensibility(draft)
        scores["defensibility"] = defensibility_score
        feedback.extend(defensibility_feedback)

        # 8. 회사 적합성 평가
        company_fit_score, company_fit_feedback = self._evaluate_company_fit(draft, question)
        scores["company_fit"] = company_fit_score
        feedback.extend(company_fit_feedback)
        
        # 종합 점수 계산 (가중 평균)
        weights = {
            "relevance": 0.30,
            "specificity": 0.18,
            "logic": 0.14,
            "originality": 0.10,
            "readability": 0.08,
            "persuasiveness": 0.08,
            "defensibility": 0.07,
            "company_fit": 0.05,
        }
        
        overall = sum(scores[dim] * weights[dim] for dim in scores)
        
        # 개선 제안 생성
        suggestions = self._generate_suggestions(scores, feedback)
        
        return QualityScore(
            overall=round(overall, 1),
            details={k: round(v, 1) for k, v in scores.items()},
            feedback=feedback,
            suggestions=suggestions
        )
    
    def _evaluate_relevance(self, draft: str, question: str) -> tuple[float, List[str]]:
        """관련성 평가"""
        feedback = []
        score = 70.0  # 기본 점수
        
        # 질문에서 키워드 추출
        question_lower = question.lower()
        draft_lower = draft.lower()
        
        # 질문 유형 감지
        detected_type = self._detect_question_type(question_lower)
        
        if detected_type:
            # 해당 유형의 키워드가 답변에 포함되어 있는지 확인
            matching_keywords = [
                kw for kw in self.RELEVANCE_KEYWORDS[detected_type]
                if kw in draft_lower
            ]
            
            keyword_ratio = len(matching_keywords) / len(self.RELEVANCE_KEYWORDS[detected_type])
            score += keyword_ratio * 30
            
            if keyword_ratio < 0.3:
                feedback.append(f"'{detected_type}' 관련 키워드가 부족합니다")
        
        # 질문의 주요 단어가 답변에 포함되어 있는지 확인
        question_words = set(re.findall(r'[가-힣]{2,}', question))
        draft_words = set(re.findall(r'[가-힣]{2,}', draft))
        
        common_words = question_words & draft_words
        if question_words:
            word_overlap = len(common_words) / len(question_words)
            score += word_overlap * 20
        
        return min(100, score), feedback
    
    def _evaluate_specificity(self, draft: str) -> tuple[float, List[str]]:
        """구체성 평가"""
        feedback = []
        score = 50.0
        
        # 숫자 포함 여부
        numbers = re.findall(r'\d+', draft)
        if numbers:
            score += min(30, len(numbers) * 10)
        else:
            feedback.append("구체적인 수치가 포함되어 있지 않습니다")
        
        # 퍼센트 포함 여부
        if '%' in draft or '퍼센트' in draft:
            score += 10
        
        # 금액 포함 여부
        if any(unit in draft for unit in ['원', '만원', '억', '$']):
            score += 10
        
        # 기간/날짜 포함 여부
        if any(unit in draft for unit in ['개월', '년', '일', '시간']):
            score += 10
        
        return min(100, score), feedback
    
    def _evaluate_logic(self, draft: str) -> tuple[float, List[str]]:
        """논리성 평가 (STAR 구조)"""
        feedback = []
        score = 60.0
        
        # STAR 키워드 확인
        star_keywords = {
            "situation": ["배경", "상황", "당시", "환경", "프로젝트"],
            "task": ["역할", "담당", "목표", "과제", "임무"],
            "action": ["수행", "진행", "구현", "개발", "분석", "설계"],
            "result": ["결과", "성과", "달성", "개선", "향상", "완료"]
        }
        
        detected_elements = []
        for element, keywords in star_keywords.items():
            if any(kw in draft for kw in keywords):
                detected_elements.append(element)
        
        # STAR 요소 비율
        star_ratio = len(detected_elements) / 4
        score += star_ratio * 40
        
        if len(detected_elements) < 2:
            feedback.append("STAR 구조가 충분히 드러나지 않습니다")
        
        # 논리적 연결어 확인
        connectors = ["때문에", "따라서", "그래서", "결과적으로", "이를 통해"]
        connector_count = sum(1 for conn in connectors if conn in draft)
        
        if connector_count > 0:
            score += min(10, connector_count * 5)
        
        return min(100, score), feedback
    
    def _evaluate_originality(self, draft: str) -> tuple[float, List[str]]:
        """독창성 평가"""
        feedback = []
        score = 100.0  # 높은 점수에서 시작
        
        # 클리셰 패턴 검출
        found_cliches = []
        for cliche in self.CLICHE_PATTERNS:
            if cliche in draft:
                found_cliches.append(cliche)
        
        # 클리셰당 감점
        penalty = len(found_cliches) * 15
        score -= penalty
        
        if found_cliches:
            feedback.append(f"일반적인 표현이 포함되어 있습니다: {', '.join(found_cliches[:2])}")
        
        # 너무 짧은 문장 (독창성 의심)
        sentences = self._split_sentences(draft)
        short_sentences = [s for s in sentences if 0 < len(s) < 20]
        
        if len(short_sentences) > len(sentences) * 0.5:
            score -= 10
            feedback.append("너무 짧은 문장이 많습니다")
        
        return max(0, score), feedback
    
    def _evaluate_readability(self, draft: str) -> tuple[float, List[str]]:
        """가독성 평가"""
        feedback = []
        score = 80.0
        
        # 전체 길이
        total_length = len(draft)
        
        if total_length < 100:
            score -= 20
            feedback.append("답변이 너무 짧습니다")
        elif total_length > 1000:
            score -= 10
            feedback.append("답변이 너무 깁니다 (1000자 이내 권장)")
        
        # 문장 길이 분석
        sentence_lengths = [len(s) for s in self._split_sentences(draft) if s]
        
        if sentence_lengths:
            avg_length = sum(sentence_lengths) / len(sentence_lengths)
            
            # 평균 문장 길이가 너무 길면 감점
            if avg_length > 100:
                score -= 15
                feedback.append("평균 문장이 너무 깁니다")
            elif avg_length < 20:
                score -= 10
                feedback.append("평균 문장이 너무 짧습니다")
        
        # 줄바꿈 적절성
        line_count = draft.count('\n')
        if line_count == 0 and total_length > 200:
            score -= 10
            feedback.append("가독성을 위해 문단을 나누는 것을 권장합니다")
        
        return max(0, score), feedback
    
    def _generate_suggestions(
        self,
        scores: Dict[str, float],
        feedback: List[str]
    ) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        # 점수가 낮은 차원에 대한 제안
        if scores.get("relevance", 0) < 70:
            suggestions.append("질문의 핵심 키워드를 답변에 포함시키세요")
        
        if scores.get("specificity", 0) < 70:
            suggestions.append("구체적인 수치(%, 개수, 금액)를 추가하세요")
        
        if scores.get("logic", 0) < 70:
            suggestions.append("STAR 구조(상황-과제-행동-결과)를 명확히 드러내세요")
        
        if scores.get("originality", 0) < 70:
            suggestions.append("일반적인 표현 대신 자신만의 경험을 구체적으로 표현하세요")
        
        if scores.get("readability", 0) < 70:
            suggestions.append("문단을 나누고 적절한 길이의 문장을 사용하세요")

        if scores.get("persuasiveness", 0) < 70:
            suggestions.append("주장 뒤에 바로 근거와 결과를 붙여 설득 구조를 강화하세요")

        if scores.get("defensibility", 0) < 70:
            suggestions.append("면접에서 재질문받을 수 있는 수치·비교 기준·개인 기여를 미리 넣어두세요")

        if scores.get("company_fit", 0) < 70:
            suggestions.append("회사·직무 신호와 본인 경험의 연결고리를 더 앞부분에서 드러내세요")
        
        return suggestions

    def _evaluate_persuasiveness(self, draft: str) -> tuple[float, List[str]]:
        feedback = []
        score = 60.0

        if any(connector in draft for connector in ["결과적으로", "이를 통해", "따라서", "그래서"]):
            score += 15
        if any(char.isdigit() for char in draft):
            score += 15
        if any(keyword in draft for keyword in ["기여", "개선", "성과", "효과"]):
            score += 10
        if score < 75:
            feedback.append("주장과 성과 사이의 연결이 약해 설득력이 떨어질 수 있습니다")
        return min(100, score), feedback

    def _evaluate_defensibility(self, draft: str) -> tuple[float, List[str]]:
        feedback = []
        score = 55.0

        if any(keyword in draft for keyword in ["제가", "직접", "담당", "판단"]):
            score += 20
        if any(char.isdigit() for char in draft):
            score += 15
        if any(keyword in draft for keyword in ["기준", "비교", "근거", "측정"]):
            score += 10
        if score < 70:
            feedback.append("면접에서 근거·비교 기준·개인 기여를 다시 물으면 방어가 약할 수 있습니다")
        return min(100, score), feedback

    def _evaluate_company_fit(self, draft: str, question: str) -> tuple[float, List[str]]:
        feedback = []
        score = 55.0
        combined = f"{question} {draft}"
        if any(keyword in combined for keyword in ["회사", "조직", "기관", "직무", "고객", "서비스"]):
            score += 25
        if any(keyword in draft for keyword in ["입사 후", "기여", "활용", "연결"]):
            score += 15
        if score < 70:
            feedback.append("회사·직무와 본인 경험의 연결이 아직 약하게 들릴 수 있습니다")
        return min(100, score), feedback

    def _detect_question_type(self, question_lower: str) -> Optional[str]:
        """질문 텍스트와 가장 잘 맞는 질문 유형 반환"""
        scored_types = []
        for q_type, keywords in self.RELEVANCE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                scored_types.append((score, q_type))

        if not scored_types:
            return None

        scored_types.sort(reverse=True)
        return scored_types[0][1]

    def _split_sentences(self, text: str) -> List[str]:
        """한글 문장을 과도하게 쪼개지 않도록 문장 단위로 분리"""
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if sentence.strip()
        ]
        return sentences or [normalized]
    
    def get_quality_grade(self, score: float) -> str:
        """점수에 따른 등급 반환"""
        if score >= 90:
            return "A (우수)"
        elif score >= 80:
            return "B (양호)"
        elif score >= 70:
            return "C (보통)"
        elif score >= 60:
            return "D (미흡)"
        else:
            return "F (부족)"


def evaluate_draft_quality(
    draft: str,
    question: str,
    experience_context: Optional[str] = None
) -> QualityScore:
    """초안 품질 평가 편의 함수"""
    evaluator = QualityEvaluator()
    return evaluator.evaluate_draft(draft, question, experience_context)


def evaluate_answer_quality(
    workspace: Any,
    answer: str,
    question: str,
    experience_context: Optional[str] = None,
) -> QualityScore:
    """기존 호출부 호환용 품질 평가 엔트리포인트"""
    _ = workspace
    return evaluate_draft_quality(answer, question, experience_context)
