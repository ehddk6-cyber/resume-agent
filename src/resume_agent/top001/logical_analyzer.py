from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from .base_types import (
    LogicalNode,
    LogicalGraph,
    VulnerableLink,
    AnswerStyle,
    AttackVector,
)


_INDIGITOH = r"[가-힣]{2,}"


CLAIM_INDICATORS = [
    "저는",
    "제가",
    "주도했습니다",
    "주도한",
    "개선했습니다",
    "개선한",
    "달성했습니다",
    "달성한",
    "해결했습니다",
    "해결한",
    "도입했습니다",
    "도입한",
    "구축했습니다",
    "구축한",
    "수행했습니다",
    "수행한",
    "担当しました",
    "主動しました",
]

EVIDENCE_INDICATORS = [
    "위해서",
    "통해",
    "덕분에",
    "결과",
    "성과",
    "기여",
    "으로 인해",
    "때문이다",
    "그 결과",
    "이로 인해",
    "때문에",
    "때문은",
]

CONCLUSION_INDICATORS = [
    "배운 점",
    "교훈",
    "경험",
    "효과",
    "변화",
    "개선",
    "발견",
    "성찰",
    "느낀 점",
    "분석 결과",
]

VAGUE_ATTRIBUTION = ["우리 팀", "우리 부서", "함께", "공동으로", "협력하여"]
PERSONAL_ATTRIBUTION = ["저는", "제가", "내가", "내가 직접", "담당하여", "주도하여"]

OVERGENERALIZATION_PATTERNS = [
    r"항상",
    r"완전",
    r"모두",
    r"전부",
    r"반드시",
    r"누구나",
    r"모든",
    r"끝없이",
    r"최고",
    r"유일한",
]


def _extract_entities(text: str) -> List[str]:
    entities = []
    entities.extend(re.findall(r"\d+(?:\.\d+)?%", text))
    entities.extend(re.findall(r"\d+(?:배|건|명|위|시간|일|개월|년)", text))
    entities.extend(re.findall(r"[가-힣]{2,}", text))
    return list(set(entities))


def _classify_sentence(sentence: str) -> str:
    sentence_lower = sentence.lower()
    claim_score = sum(1 for ind in CLAIM_INDICATORS if ind in sentence_lower)
    evidence_score = sum(1 for ind in EVIDENCE_INDICATORS if ind in sentence_lower)
    conclusion_score = sum(1 for ind in CONCLUSION_INDICATORS if ind in sentence_lower)
    scores = {
        "claim": claim_score,
        "evidence": evidence_score,
        "conclusion": conclusion_score,
    }
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "claim"


def _find_transitions(sentence: str) -> List[str]:
    transitions = [
        "그래서",
        "따라서",
        "그 결과",
        "이로 인해",
        "때문에",
        "위해",
        "통해",
        "덕분에",
        "이러한",
        "이를",
    ]
    found = [t for t in transitions if t in sentence]
    return found


def _has_vague_attribution(text: str) -> bool:
    for phrase in VAGUE_ATTRIBUTION:
        if phrase in text:
            personal = any(p in text for p in PERSONAL_ATTRIBUTION)
            if not personal:
                return True
    return False


def _has_overgeneralization(text: str) -> bool:
    for pattern in OVERGENERALIZATION_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def _has_unverified_metric(text: str) -> bool:
    metrics = re.findall(r"\d+(?:\.\d+)?%", text)
    if not metrics:
        return False
    measurement_context = [
        "측정",
        "기준",
        "비교",
        "대비",
        "기준점",
        "산출",
        "계산",
        "어디서",
        "어떻게",
    ]
    return not any(ctx in text for ctx in measurement_context)


def _has_weak_causality(text: str) -> bool:
    cause_words = ["때문에", "위해", "으로 인해", "결과"]
    effect_words = ["달성", "改善", "해결", "향상", "증가"]
    has_cause = any(w in text for w in cause_words)
    has_effect = any(w in text for w in effect_words)
    if has_cause and has_effect:
        linking_words = ["통해", "덕분에", "로 인해", "따라서", "그래서"]
        return not any(lw in text for lw in linking_words)
    return False


class LogicalStructureAnalyzer:
    def parse(self, answer: str) -> LogicalGraph:
        sentences = [s.strip() for s in re.split(r"[.!?]\s+", answer) if s.strip()]
        nodes: Dict[str, LogicalNode] = {}
        edges: List[Tuple[str, str, str]] = []

        for i, sentence in enumerate(sentences):
            node_id = f"node_{i}"
            node_type = _classify_sentence(sentence)
            entities = _extract_entities(sentence)
            transitions = _find_transitions(sentence)
            node = LogicalNode(
                id=node_id,
                node_type=node_type,
                content=sentence,
                confidence=1.0,
                supporting_evidence=entities,
                attacks=transitions,
            )
            nodes[node_id] = node

        for i in range(len(sentences) - 1):
            curr_type = nodes[f"node_{i}"].node_type
            next_type = nodes[f"node_{i + 1}"].node_type
            if curr_type == "claim" and next_type == "evidence":
                edges.append((f"node_{i}", f"node_{i + 1}", "supports"))
            elif curr_type == "evidence" and next_type == "conclusion":
                edges.append((f"node_{i}", f"node_{i + 1}", "leads_to"))
            elif curr_type == "evidence" and next_type == "evidence":
                edges.append((f"node_{i}", f"node_{i + 1}", "elaborates"))

        claim_nodes = [n for n in nodes.values() if n.node_type == "claim"]
        root = claim_nodes[0].id if claim_nodes else None

        return LogicalGraph(nodes=nodes, edges=edges, root_claim=root)

    def identify_vulnerable_links(self, graph: LogicalGraph) -> List[VulnerableLink]:
        vulnerabilities: List[VulnerableLink] = []
        seen_types: set = set()

        for node_id, node in graph.nodes.items():
            if node.node_type != "claim":
                continue
            connected = [e[1] for e in graph.edges if e[0] == node_id]
            has_evidence = any(
                graph.nodes[n].node_type == "evidence" for n in connected
            )
            has_conclusion = any(
                graph.nodes[n].node_type == "conclusion" for n in connected
            )

            if not has_evidence and not has_conclusion:
                v_type = "insufficient_evidence"
                if v_type not in seen_types:
                    vulnerabilities.append(
                        VulnerableLink(
                            source_id=node_id,
                            target_id="",
                            link_type="none",
                            vulnerability_type=v_type,
                            severity="high",
                            description=f"주장 '{node.content[:30]}...' 에 근거가 없습니다",
                            attack_vectors=[
                                "그 주장에 대한 구체적 근거는 무엇인가요?",
                                "어떤 데이터나 사실을 기반으로 하신 말인가요?",
                            ],
                        )
                    )
                    seen_types.add(v_type)

            if _has_vague_attribution(node.content):
                v_type = "unclear_attribution"
                if v_type not in seen_types:
                    vulnerabilities.append(
                        VulnerableLink(
                            source_id=node_id,
                            target_id="",
                            link_type="vague",
                            vulnerability_type=v_type,
                            severity="high",
                            description=f"'{node.content[:30]}...' 에서 팀 vs 개인 기여가 불분명합니다",
                            attack_vectors=[
                                "팀 활동에서 본인의 구체적 역할은 무엇이었나요?",
                                "다른 팀원은 어떤 업무를 맡았나요?",
                            ],
                        )
                    )
                    seen_types.add(v_type)

            if _has_overgeneralization(node.content):
                v_type = "overgeneralization"
                if v_type not in seen_types:
                    vulnerabilities.append(
                        VulnerableLink(
                            source_id=node_id,
                            target_id="",
                            link_type="broad",
                            vulnerability_type=v_type,
                            severity="medium",
                            description=f"'{node.content[:30]}...' 에 과_generalization이 있습니다",
                            attack_vectors=[
                                "'항상' 혹은 '모두'라는 표현의 근거가 되나요?",
                                "예외 상황은 없었나요?",
                            ],
                        )
                    )
                    seen_types.add(v_type)

            if _has_unverified_metric(node.content):
                v_type = "unverified_metrics"
                if v_type not in seen_types:
                    vulnerabilities.append(
                        VulnerableLink(
                            source_id=node_id,
                            target_id="",
                            link_type="metric",
                            vulnerability_type=v_type,
                            severity="high",
                            description=f"'{node.content[:30]}...' 의 수치가 검증되지 않았습니다",
                            attack_vectors=[
                                "그 수치는 어떻게 산출된 것인가요?",
                                "비교 기준이나 측정 방법은 무엇인가요?",
                            ],
                        )
                    )
                    seen_types.add(v_type)

        for i, edge in enumerate(graph.edges):
            source_node = graph.nodes.get(edge[0])
            target_node = graph.nodes.get(edge[1])
            if source_node and target_node:
                if _has_weak_causality(source_node.content + target_node.content):
                    v_type = "weak_causality"
                    if v_type not in seen_types:
                        vulnerabilities.append(
                            VulnerableLink(
                                source_id=edge[0],
                                target_id=edge[1],
                                link_type=edge[2],
                                vulnerability_type=v_type,
                                severity="medium",
                                description="인과관게가 약합니다",
                                attack_vectors=[
                                    "그 결과의 원인이 정말 이것뿐인가요?",
                                    "다른影响因素은 없었나요?",
                                ],
                            )
                        )
                        seen_types.add(v_type)

        return vulnerabilities

    def calculate_confidence_score(self, graph: LogicalGraph) -> float:
        if not graph.nodes:
            return 0.0
        claims = [n for n in graph.nodes.values() if n.node_type == "claim"]
        if not claims:
            return 0.5
        evidenced_count = 0
        for claim in claims:
            connected = [e[1] for e in graph.edges if e[0] == claim.id]
            if any(graph.nodes[n].node_type == "evidence" for n in connected):
                evidenced_count += 1
        claim_ratio = evidenced_count / len(claims)
        has_quantified = any(
            re.search(r"\d+(?:\.\d+)?%", n.content) for n in graph.nodes.values()
        )
        quantified_bonus = 0.1 if has_quantified else 0.0
        score = min(1.0, claim_ratio * 0.8 + quantified_bonus + 0.1)
        return round(score, 2)
