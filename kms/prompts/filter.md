주어진 주제어와 문서 후보들을 평가한다. 각 문서에 대해:
- relevance: 1-10 (주제와의 관련도)
- credibility: 1-10 (출처 신뢰도, 본문 깊이)
- reason: 한 줄 평가

규칙:
- 출력은 JSON만. 다른 설명/코드블록 금지.
- 형식: {"scores": [{"index": 0, "relevance": 8, "credibility": 7, "reason": "..."}, ...]}
- index는 입력 배열의 0-based 인덱스
