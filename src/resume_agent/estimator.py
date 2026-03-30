import tiktoken
from .logger import get_logger
from .config import get_config_value

logger = get_logger("estimator")


def _get_threshold() -> int:
    return int(get_config_value("token.warning_threshold", 8000))


def _get_cost_per_1k() -> float:
    return float(get_config_value("token.cost_per_1k", 0.005))


# 하위 호환: 모듈 로드 시점 상수 (config.yaml 값 반영)
COST_PER_1K_TOKENS = _get_cost_per_1k()
WARNING_THRESHOLD_TOKENS = _get_threshold()


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """텍스트의 토큰 수를 계산합니다."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning(f"Model {model} not found in tiktoken. Using cl100k_base.")
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def estimate_cost_and_log(prompt: str, context_name: str = "Prompt") -> int:
    """프롬프트의 토큰 수와 예상 비용을 계산하고 로깅합니다."""
    tokens = count_tokens(prompt)
    cost = (tokens / 1000) * _get_cost_per_1k()

    log_msg = f"[{context_name}] Tokens: {tokens:,} | Estimated Cost: ${cost:.4f}"

    if tokens > _get_threshold():
        logger.warning(
            f"{log_msg} (WARNING: High token count. Automatic compression may be applied.)"
        )
    else:
        logger.info(log_msg)

    return tokens


def is_over_limit(tokens: int, limit: int | None = None) -> bool:
    """토큰 수가 한도를 초과했는지 확인합니다."""
    threshold = limit if limit is not None else _get_threshold()
    return tokens > threshold
