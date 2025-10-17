import re

def ngrams(tokens, n=8):
    return set(tuple(tokens[i:i+n]) for i in range(0, max(0, len(tokens)-n+1)))

def tokenize_ko(text: str):
    # 간단 토크나이저(공백/문장부호 기준) — mecab 미사용
    text = re.sub(r"[^\w가-힣\s]", " ", text)
    return [t for t in re.split(r"\s+", text) if t]

def plag_8gram(generated: str, contexts: list[str]) -> float:
    gt = tokenize_ko(generated)
    g8 = ngrams(gt, 8)
    if not g8: return 0.0
    ctx_tokens = []
    for c in contexts:
        ctx_tokens += tokenize_ko(c)
    c8 = ngrams(ctx_tokens, 8)
    if not c8: return 0.0
    inter = g8.intersection(c8)
    return round(len(inter) / max(1, len(g8)), 4)










