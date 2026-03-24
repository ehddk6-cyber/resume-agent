import re
from pathlib import Path
from typing import List

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF 파일(또는 폴더 내의 모든 PDF)에서 텍스트를 추출합니다."""
    if not PdfReader:
        return ""
        
    texts = []
    
    # 단일 파일인 경우
    if pdf_path.is_file() and pdf_path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(pdf_path)
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            texts.append(text)
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            
    # 디렉토리인 경우 (다중 JD 분석)
    elif pdf_path.is_dir():
        for file in pdf_path.glob("*.pdf"):
            try:
                reader = PdfReader(file)
                text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
                texts.append(text)
            except Exception as e:
                print(f"Error reading PDF {file}: {e}")
                
    return "\n\n".join(texts)

def extract_jd_keywords(text: str) -> List[str]:
    """
    직무기술서 텍스트에서 명사형 키워드를 추출합니다.
    자주 등장하는 키워드(직무, 역량 관련)를 필터링하여 상위 10개를 반환합니다.
    """
    if not text:
        return []
    
    # 불용어(의미가 적은 일반 명사나 조사 등)
    stopwords = {"업무", "수행", "관련", "분야", "내용", "지원", "사항", "해당", "기타", "필요", "직무", "자격", "우대", "경험", "능력", "활용", "이해", "지식", "제출", "기준", "담당"}
    
    # 2글자 이상 한글/영문 단어 추출
    words = re.findall(r'[가-힣a-zA-Z]{2,}', text)
    
    # 단어 빈도 계산
    freq = {}
    for word in words:
        if word not in stopwords:
            freq[word] = freq.get(word, 0) + 1
            
    # 빈도순 정렬
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:10]]

def split_text(text: str, chunk_size: int = 3000, overlap: int = 500) -> List[str]:
    """
    텍스트를 chunk_size 크기로 나눕니다. 
    문단 단위(\n\n)로 먼저 나누어 문맥 파편화를 최소화합니다.
    """
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # 단일 문단이 chunk_size보다 큰 경우 강제 분할
            if len(para) > chunk_size:
                start = 0
                while start < len(para):
                    chunks.append(para[start:start + chunk_size].strip())
                    start += chunk_size - overlap
                current_chunk = ""
            else:
                current_chunk = para + "\n\n"
                
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks
