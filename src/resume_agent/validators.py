"""
데이터 검증 강화 - 경험 데이터의 품질과 일관성 보장
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

from .models import Experience, EvidenceLevel


class ValidationSeverity(Enum):
    """검증 결과 심각도"""
    ERROR = "error"      # 필수 수정 사항
    WARNING = "warning"  # 권장 수정 사항
    INFO = "info"        # 참고 사항


@dataclass
class ValidationMessage:
    """검증 메시지"""
    severity: ValidationSeverity
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """검증 결과"""
    passed: bool
    errors: List[ValidationMessage]
    warnings: List[ValidationMessage]
    info: List[ValidationMessage]
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """검증 결과 요약 반환"""
        parts = []
        if self.errors:
            parts.append(f"오류 {len(self.errors)}건")
        if self.warnings:
            parts.append(f"경고 {len(self.warnings)}건")
        if self.info:
            parts.append(f"정보 {len(self.info)}건")
        
        if not parts:
            return "검증 통과"
        return ", ".join(parts)


class ExperienceValidator:
    """경험 데이터 검증기"""
    
    # STAR 구조 최소 길이
    MIN_SITUATION_LENGTH = 50
    MIN_TASK_LENGTH = 30
    MIN_ACTION_LENGTH = 100
    MIN_RESULT_LENGTH = 50
    
    # 클리셰 패턴 (사용 지양)
    CLICHE_PATTERNS = [
        "최선을 다하겠습니다",
        "열정적으로 임하겠습니다",
        "팀원들과 소통하며",
        "맡은 바 책임을 다하겠습니다",
        "성실하게 근무하겠습니다",
        "항상 배우는 자세로",
        "도전을 두려워하지 않는",
        "창의적인 사고를 바탕으로"
    ]
    
    def validate(self, experience: Experience) -> ValidationResult:
        """
        경험 데이터 종합 검증
        
        Args:
            experience: 검증할 경험 데이터
        
        Returns:
            ValidationResult 객체
        """
        errors = []
        warnings = []
        info = []
        
        # 1. 필수 필드 검증
        errors.extend(self._validate_required_fields(experience))
        
        # 2. STAR 구조 검증
        star_result = self._validate_star_structure(experience)
        errors.extend(star_result["errors"])
        warnings.extend(star_result["warnings"])
        
        # 3. 구체성 검증
        specificity_result = self._validate_specificity(experience)
        warnings.extend(specificity_result["warnings"])
        info.extend(specificity_result["info"])
        
        # 4. 논리적 일관성 검증
        consistency_result = self._validate_consistency(experience)
        warnings.extend(consistency_result["warnings"])
        
        # 5. 클리셰 검증
        cliche_result = self._validate_cliches(experience)
        warnings.extend(cliche_result["warnings"])
        
        # 6. 증거 레벨 검증
        evidence_result = self._validate_evidence(experience)
        info.extend(evidence_result["info"])
        
        passed = len(errors) == 0
        
        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_required_fields(self, exp: Experience) -> List[ValidationMessage]:
        """필수 필드 검증"""
        errors = []
        
        if not exp.title or len(exp.title.strip()) == 0:
            errors.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field="title",
                message="경험 제목이 비어있습니다",
                suggestion="경험을 대표하는 제목을 입력하세요"
            ))
        
        if not exp.situation or len(exp.situation.strip()) == 0:
            errors.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field="situation",
                message="상황(Situation) 설명이 비어있습니다",
                suggestion="프로젝트나 업무의 배경을 설명하세요"
            ))
        
        if not exp.task or len(exp.task.strip()) == 0:
            errors.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field="task",
                message="과제(Task) 설명이 비어있습니다",
                suggestion="담당 역할과 목표를 설명하세요"
            ))
        
        if not exp.action or len(exp.action.strip()) == 0:
            errors.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field="action",
                message="행동(Action) 설명이 비어있습니다",
                suggestion="구체적으로 수행한 작업을 설명하세요"
            ))
        
        if not exp.result or len(exp.result.strip()) == 0:
            errors.append(ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field="result",
                message="결과(Result) 설명이 비어있습니다",
                suggestion="달성한 성과와 수치를 설명하세요"
            ))
        
        return errors
    
    def _validate_star_structure(self, exp: Experience) -> Dict[str, List[ValidationMessage]]:
        """STAR 구조完整性 검증"""
        errors = []
        warnings = []
        
        # Situation 길이 검증
        if exp.situation and len(exp.situation) < self.MIN_SITUATION_LENGTH:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="situation",
                message=f"상황 설명이 너무 짧습니다 (최소 {self.MIN_SITUATION_LENGTH}자 권장)",
                suggestion="배경, 맥락, 제약조건 등을 더 구체적으로 설명하세요"
            ))
        
        # Task 길이 검증
        if exp.task and len(exp.task) < self.MIN_TASK_LENGTH:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="task",
                message=f"과제 설명이 너무 짧습니다 (최소 {self.MIN_TASK_LENGTH}자 권장)",
                suggestion="담당 역할, 목표, 기대치 등을 더 구체적으로 설명하세요"
            ))
        
        # Action 길이 검증
        if exp.action and len(exp.action) < self.MIN_ACTION_LENGTH:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="action",
                message=f"행동 설명이 너무 짧습니다 (최소 {self.MIN_ACTION_LENGTH}자 권장)",
                suggestion="수행한 작업, 사용한 기술, 의사결정 과정 등을 더 구체적으로 설명하세요"
            ))
        
        # Result 길이 검증
        if exp.result and len(exp.result) < self.MIN_RESULT_LENGTH:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="result",
                message=f"결과 설명이 너무 짧습니다 (최소 {self.MIN_RESULT_LENGTH}자 권장)",
                suggestion="달성한 성과, 배운 점, 영향 등을 더 구체적으로 설명하세요"
            ))
        
        return {"errors": errors, "warnings": warnings}
    
    def _validate_specificity(self, exp: Experience) -> Dict[str, List[ValidationMessage]]:
        """구체성 검증 (숫자, 지표 포함 여부)"""
        warnings = []
        info = []
        
        if not exp.result:
            return {"warnings": warnings, "info": info}
        
        # 숫자 포함 여부 확인
        has_numbers = any(char.isdigit() for char in exp.result)
        
        if not has_numbers:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="result",
                message="결과에 구체적인 수치가 포함되어 있지 않습니다",
                suggestion="퍼센트, 개수, 금액 등 정량적 지표를 추가하면 더 효과적입니다"
            ))
        else:
            info.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field="result",
                message="결과에 구체적인 수치가 포함되어 있습니다"
            ))
        
        return {"warnings": warnings, "info": info}
    
    def _validate_consistency(self, exp: Experience) -> Dict[str, List[ValidationMessage]]:
        """논리적 일관성 검증"""
        warnings = []
        
        if not (exp.situation and exp.task and exp.action and exp.result):
            return {"warnings": warnings}
        
        # Situation과 Task의 연결성 확인
        if exp.situation and exp.task:
            # 간단한 키워드 매칭으로 연결성 확인
            situation_keywords = set(exp.situation.lower().split())
            task_keywords = set(exp.task.lower().split())
            
            common_keywords = situation_keywords & task_keywords
            if len(common_keywords) < 2:
                warnings.append(ValidationMessage(
                    severity=ValidationSeverity.WARNING,
                    field="task",
                    message="상황과 과제 사이의 연결성이 약합니다",
                    suggestion="상황의 맥락이 과제에 자연스럽게 연결되도록 작성하세요"
                ))
        
        return {"warnings": warnings}
    
    def _validate_cliches(self, exp: Experience) -> Dict[str, List[ValidationMessage]]:
        """클리셰 패턴 검증"""
        warnings = []
        
        # 모든 필드에서 클리셰 검출
        all_text = " ".join(filter(None, [
            exp.situation or "",
            exp.task or "",
            exp.action or "",
            exp.result or ""
        ]))
        
        found_cliches = []
        for cliche in self.CLICHE_PATTERNS:
            if cliche in all_text:
                found_cliches.append(cliche)
        
        if found_cliches:
            warnings.append(ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field="general",
                message=f"일반적인 표현이 포함되어 있습니다: {', '.join(found_cliches[:3])}",
                suggestion="독특하고 구체적인 표현으로 대체하면 더 효과적입니다"
            ))
        
        return {"warnings": warnings}
    
    def _validate_evidence(self, exp: Experience) -> Dict[str, List[ValidationMessage]]:
        """증거 레벨 검증"""
        info = []
        
        if exp.evidence_level == EvidenceLevel.L1:
            info.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field="evidence_level",
                message="증거 레벨이 L1(미검증)입니다",
                suggestion="증빙 파일을 추가하면 L2 이상으로 승격됩니다"
            ))
        elif exp.evidence_level == EvidenceLevel.L2:
            info.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field="evidence_level",
                message="증거 레벨이 L2(기본 검증)입니다"
            ))
        elif exp.evidence_level == EvidenceLevel.L3:
            info.append(ValidationMessage(
                severity=ValidationSeverity.INFO,
                field="evidence_level",
                message="증거 레벨이 L3(검증 완료)입니다 - 최고 신뢰도"
            ))
        
        return {"info": info}


def validate_experience(experience: Experience) -> ValidationResult:
    """경험 검증 편의 함수"""
    validator = ExperienceValidator()
    return validator.validate(experience)