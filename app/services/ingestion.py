import io

from pypdf import PdfReader


def extract_pages(data: bytes) -> list[tuple[int, str]]:
    """PDF bayttan (sayfa_no, metin) listesi. Taranmış (görüntü) PDF'lerde metin boş gelebilir."""
    reader = PdfReader(io.BytesIO(data))
    return [(i + 1, (page.extract_text() or "")) for i, page in enumerate(reader.pages)]


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Metni overlap'li parçalara böl. Küçük parça → isabetli/bağlamsız; büyük → bağlamlı/bulanık."""
    text = " ".join(text.split())  # fazla boşluk/satır sonunu sadeleştir
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks


def chunk_pages(pages: list[tuple[int, str]], size: int, overlap: int) -> list[tuple[int, str]]:
    """(sayfa_no, metin) listesinden (sayfa_no, parça) listesi — kaynak gösterimi için sayfa korunur."""
    out: list[tuple[int, str]] = []
    for page_no, text in pages:
        for chunk in chunk_text(text, size, overlap):
            out.append((page_no, chunk))
    return out
