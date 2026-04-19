import bleach

ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({"p","br","ul","ol","li","strong","em","b","i","a"})
ALLOWED_ATTRIBUTES = {"a": ["href","title","target","rel"]}

def sanitize_html(html: str) -> str:
    return bleach.clean(html or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
