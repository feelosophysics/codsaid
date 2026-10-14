"""생성 응답의 검색 근거를 모으고 저장 가능한 출처 Markdown을 만듭니다."""
from urllib.parse import urlparse, quote


def collect_grounding(chunk, sources, queries):
    """출처와 검색어는 조각마다 반복될 수 있어 사전/집합으로 중복을 제거합니다."""
    suggestion = ""
    for candidate in getattr(chunk, "candidates", None) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        if not metadata:
            continue
        queries.update(getattr(metadata, "web_search_queries", None) or [])
        entry = getattr(metadata, "search_entry_point", None)
        suggestion = getattr(entry, "rendered_content", None) or suggestion
        for item in getattr(metadata, "grounding_chunks", None) or []:
            web = getattr(item, "web", None)
            uri = getattr(web, "uri", "") if web else ""
            try:
                parsed = urlparse(uri)
            except ValueError:
                continue
            if parsed.scheme in {"https", "http"} and parsed.hostname:
                sources[uri] = getattr(web, "title", None) or parsed.hostname
    return suggestion


def sources_markdown(sources):
    """출처를 본문에 붙여 기존 DB와 기록 화면에서도 다시 볼 수 있게 합니다."""
    if not sources:
        return ""
    lines = ["\n\n---\n**웹 검색 출처**"]
    for index, (uri, title) in enumerate(sources.items(), 1):
        # Markdown 문법·HTML을 제목으로 주입하지 못하도록 표시 문자를 치환합니다.
        safe_title = str(title).replace("[", "（").replace("]", "）").replace("<", "〈").replace(">", "〉").replace("\n", " ")[:160]
        safe_uri = quote(uri, safe=":/?&=%#@+;,")
        lines.append(f"{index}. [{safe_title}]({safe_uri})")
    return "\n".join(lines)
