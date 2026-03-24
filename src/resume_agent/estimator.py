import tiktoken
from .logger import get_logger

logger = get_logger("estimator")

# GPT-4o(또는 동급 모델) 기준 근사치 ($0.005 / 1k tokens)
COST_PER_1K_TOKENS = 0.005
WARNING_THRESHOLD_TOKENS = 8000

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
    cost = (tokens / 1000) * COST_PER_1K_TOKENS
    
    log_msg = f"[{context_name}] Tokens: {tokens:,} | Estimated Cost: ${cost:.4f}"
    
    if tokens > WARNING_THRESHOLD_TOKENS:
        logger.warning(f"{log_msg} (WARNING: High token count. Automatic compression may be applied.)")
    else:
        logger.info(log_msg)
        
    return tokens

def is_over_limit(tokens: int, limit: int = WARNING_THRESHOLD_TOKENS) -> bool:
    """토큰 수가 한도를 초과했는지 확인합니다."""
    return tokens > limit
