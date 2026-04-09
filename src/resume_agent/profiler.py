"""지원자 프로파일링 모듈."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Optional

from .experience_analyzer import ExperienceDeepAnalyzer
from .models import ApplicantProfile, Experience, WritingStyleAnalysis

_STOPWORDS = {
    "그리고",
    "하지만",
    "통해",
    "정리",
    "업무",
    "경험",
    "프로젝트",
    "진행",
    "수행",
    "문제",
    "결과",
    "지원",
    "직무",
    "제가",
    "저는",
    "위해",
    "관련",
}
_GENERIC_PATTERNS = (
    "최선을 다",
    "많은 도움",
    "성장할 수",
    "역량을 발휘",
    "잘 해냈",
    "성공적으로",
)
_FORMAL_ENDINGS = ("습니다", "했습니다", "입니다", "였습니다")
_FRIENDLY_ENDINGS = ("해요", "했어요", "이에요", "였어요")
_ASSERTIVE_TOKENS = ("직접", "주도", "개선", "설계", "구축", "정의")
_EVIDENCE_TOKENS = ("%", "건", "명", "시간", "일", "배", "지표", "데이터", "수치", "기록")


class _DisabledSemanticEngine:
    def __bool__(self) -> bool:
        return False


class ApplicantProfiler:
    """경험과 과거 답변을 기반으로 지원자 프로파일을 생성합니다."""

    def __init__(self, deep_analyzer: Optional[ExperienceDeepAnalyzer] = None):
        self.deep_analyzer = deep_analyzer or ExperienceDeepAnalyzer(
            semantic_engine=_DisabledSemanticEngine()
        )

    def build_profile(
        self,
        experiences: list[Experience],
        past_answers: Optional[list[str]] = None,
        profile_id: str = "default",
    ) -> ApplicantProfile:
        texts = self.collect_text_samples(experiences, past_answers)
        writing_style = self.analyze_writing_style(texts)
        strengths, weaknesses = self.detect_strengths_and_weaknesses(
            experiences,
            writing_style,
        )
        recommendations = self.build_recommendations(writing_style, weaknesses)

        return ApplicantProfile(
            profile_id=profile_id,
            source_count=len(experiences),
            analyzed_text_count=len(texts),
            writing_style=writing_style,
            strength_keywords=strengths,
            weakness_codes=[item["code"] for item in weaknesses],
            weakness_details=[item["detail"] for item in weaknesses],
            recommendation_summary=[item["summary"] for item in recommendations],
            answer_style_preferences=[item["style"] for item in recommendations],
            coaching_priorities=[item["priority"] for item in recommendations],
        )

    def collect_text_samples(
        self,
        experiences: list[Experience],
        past_answers: Optional[list[str]] = None,
    ) -> list[str]:
        samples: list[str] = []
        for experience in experiences:
            sample = " ".join(
                part.strip()
                for part in (
                    experience.situation,
                    experience.task,
                    experience.action,
                    experience.result,
                    experience.personal_contribution,
                )
                if part and part.strip()
            )
            if sample:
                samples.append(sample)
        for answer in past_answers or []:
            if answer and answer.strip():
                samples.append(answer.strip())
        return samples

    def analyze_writing_style(self, texts: Iterable[str]) -> WritingStyleAnalysis:
        normalized = [text.strip() for text in texts if text and text.strip()]
        if not normalized:
            return WritingStyleAnalysis()

        sentences: list[str] = []
        for text in normalized:
            parts = [part.strip() for part in re.split(r"[.!?\n]+", text) if part.strip()]
            sentences.extend(parts)
        tokens = [
            token
            for text in normalized
            for token in re.findall(r"[가-힣A-Za-z0-9%]+", text.lower())
        ]
        filtered_tokens = [
            token for token in tokens if len(token) >= 2 and token not in _STOPWORDS
        ]

        avg_sentence_words = round(
            sum(len(re.findall(r"[가-힣A-Za-z0-9%]+", sentence)) for sentence in sentences)
            / max(1, len(sentences)),
            2,
        )
        avg_sentence_chars = round(
            sum(len(sentence) for sentence in sentences) / max(1, len(sentences)),
            2,
        )
        evidence_hits = sum(text.count(token) for text in normalized for token in _EVIDENCE_TOKENS)
        formal_hits = sum(text.count(ending) for text in normalized for ending in _FORMAL_ENDINGS)
        friendly_hits = sum(text.count(ending) for text in normalized for ending in _FRIENDLY_ENDINGS)
        assertive_hits = sum(text.count(token) for text in normalized for token in _ASSERTIVE_TOKENS)

        dominant_tone = "balanced"
        if formal_hits >= friendly_hits + 2:
            dominant_tone = "logical"
        elif friendly_hits > formal_hits:
            dominant_tone = "relational"

        formality_level = "balanced"
        if formal_hits:
            formality_level = "formal"
        elif friendly_hits:
            formality_level = "friendly"

        sentence_style = "balanced"
        if avg_sentence_words >= 18:
            sentence_style = "descriptive"
        elif avg_sentence_words <= 10:
            sentence_style = "concise"

        confidence_tendency = "balanced"
        if assertive_hits >= max(2, len(normalized)):
            confidence_tendency = "assertive"
        elif assertive_hits == 0:
            confidence_tendency = "reserved"

        keyword_frequency = dict(Counter(filtered_tokens).most_common(8))
        expression_patterns: list[str] = []
        if evidence_hits:
            expression_patterns.append("정량 근거를 섞어 설명하는 편")
        if avg_sentence_words >= 16:
            expression_patterns.append("긴 서술형 문장을 자주 사용")
        else:
            expression_patterns.append("짧고 빠르게 결론을 말하는 편")
        if dominant_tone == "logical":
            expression_patterns.append("분석형 톤이 강함")
        elif dominant_tone == "relational":
            expression_patterns.append("상대와 맥락을 먼저 설명하는 편")
        if confidence_tendency == "assertive":
            expression_patterns.append("주도적으로 말하는 편")

        evidence_density = round(evidence_hits / max(1, len(sentences)), 2)
        return WritingStyleAnalysis(
            avg_sentence_words=avg_sentence_words,
            avg_sentence_chars=avg_sentence_chars,
            dominant_tone=dominant_tone,
            formality_level=formality_level,
            sentence_style=sentence_style,
            evidence_density=evidence_density,
            confidence_tendency=confidence_tendency,
            expression_patterns=expression_patterns[:4],
            keyword_frequency=keyword_frequency,
        )

    def detect_strengths_and_weaknesses(
        self,
        experiences: list[Experience],
        writing_style: WritingStyleAnalysis,
    ) -> tuple[list[str], list[dict[str, str]]]:
        competency_counter: Counter[str] = Counter()
        hidden_strengths = self.deep_analyzer.find_hidden_strengths(experiences)
        metric_count = sum(1 for item in experiences if item.metrics.strip())
        contribution_count = sum(
            1 for item in experiences if item.personal_contribution.strip()
        )
        evidence_count = sum(1 for item in experiences if item.evidence_text.strip())

        for experience in experiences:
            for competency in self.deep_analyzer.analyze_core_competency(experience):
                competency_counter[competency.competency] += 1

        strengths = [name for name, _ in competency_counter.most_common(3)]
        for hidden in hidden_strengths:
            if hidden not in strengths:
                strengths.append(hidden)
        if writing_style.evidence_density >= 1.0:
            strengths.append("근거 중심 서술")
        if writing_style.confidence_tendency == "assertive":
            strengths.append("주도적 표현")
        strengths = strengths[:5] or ["직무 적합성"]

        total = max(1, len(experiences))
        generic_hits = sum(
            1
            for experience in experiences
            if any(pattern in " ".join([experience.action, experience.result]) for pattern in _GENERIC_PATTERNS)
        )

        weaknesses: list[dict[str, str]] = []
        if metric_count / total < 0.5:
            weaknesses.append(
                {"code": "low_metrics", "detail": "성과를 설명할 때 수치나 비교 기준이 자주 빠집니다."}
            )
        if contribution_count / total < 0.5:
            weaknesses.append(
                {"code": "low_contribution", "detail": "팀 성과 대비 본인 역할을 더 분리해 설명할 필요가 있습니다."}
            )
        if evidence_count / total < 0.5:
            weaknesses.append(
                {"code": "low_evidence", "detail": "면접 방어에 쓸 증빙 문장과 기록이 부족합니다."}
            )
        if generic_hits >= max(1, total // 2):
            weaknesses.append(
                {"code": "abstract_language", "detail": "일반적 표현이 반복되어 차별화가 약해질 수 있습니다."}
            )
        if writing_style.sentence_style == "descriptive":
            weaknesses.append(
                {"code": "long_sentences", "detail": "문장이 길어져 핵심 메시지가 늦게 나올 수 있습니다."}
            )
        return strengths, weaknesses

    def build_recommendations(
        self,
        writing_style: WritingStyleAnalysis,
        weaknesses: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        weakness_codes = {item["code"] for item in weaknesses}
        recommendations: list[dict[str, str]] = []

        opening_style = "결론을 먼저 말하고 바로 근거를 붙이세요."
        if writing_style.dominant_tone == "relational":
            opening_style = "상황 한 문장 뒤에 본인 판단과 행동을 바로 연결하세요."
        recommendations.append(
            {
                "summary": "답변의 첫 문장을 더 빠르게 세우는 편이 유리합니다.",
                "style": opening_style,
                "priority": "첫 문장 15초 안에 결론-행동-결과를 고정하세요.",
            }
        )

        if "low_metrics" in weakness_codes:
            recommendations.append(
                {
                    "summary": "성과 숫자와 비교 기준을 먼저 확보하세요.",
                    "style": "결과 문장마다 최소 1개의 수치·건수·전후 비교를 넣으세요.",
                    "priority": "반복해서 쓰는 경험 3개부터 정량 근거를 보강하세요.",
                }
            )
        if "low_contribution" in weakness_codes:
            recommendations.append(
                {
                    "summary": "개인 기여를 팀 성과와 분리해 말할 필요가 있습니다.",
                    "style": "\"제가 맡은 판단\"과 \"팀 전체 결과\"를 구분해 답하세요.",
                    "priority": "주요 경험마다 본인 결정 1개를 명시하세요.",
                }
            )
        if "abstract_language" in weakness_codes or "long_sentences" in weakness_codes:
            recommendations.append(
                {
                    "summary": "추상 표현을 행동 단위로 바꾸면 설득력이 올라갑니다.",
                    "style": "\"열심히\" 대신 무엇을 어떻게 바꿨는지 동사 중심으로 바꾸세요.",
                    "priority": "긴 문장은 두 문장으로 끊고 행동 동사를 앞에 두세요.",
                }
            )
        return recommendations[:4]


def build_candidate_profile_payload(profile: ApplicantProfile) -> dict[str, object]:
    """기존 candidate_profile dict에 병합하기 쉬운 형태로 변환합니다."""
    writing_style = profile.writing_style
    return {
        "personalized_profile": profile.model_dump(mode="json"),
        "writing_style": writing_style.model_dump(),
        "communication_style": writing_style.dominant_tone,
        "confidence_style": writing_style.confidence_tendency,
        "signature_strengths": profile.strength_keywords[:4],
        "blind_spots": profile.weakness_details[:3],
        "coaching_focus": profile.coaching_priorities[:3],
        "profile_summary": (
            f"{writing_style.formality_level} 톤을 기본으로 쓰고, "
            f"{', '.join(profile.strength_keywords[:3]) or '직무 적합성'}을 강점으로 가진 지원자입니다."
        ),
    }
