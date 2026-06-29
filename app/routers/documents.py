import anyio
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from app.config import settings
from app.db.models import User
from app.db.repository import DocumentRepository
from app.dependencies import get_current_user
from app.services.embeddings import GeminiEmbeddingProvider
from app.services.ingestion import chunk_pages, extract_pages

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    data = await file.read()

    # Girdi doğrulama (D3 refleksi): boyut + tip
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Dosya çok büyük")
    name = (file.filename or "").lower()
    if not name.endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Sadece PDF")

    # PDF parse + chunking CPU-bound → event loop'u bloklama (D1 dersi): ayrı thread'de
    pages = await anyio.to_thread.run_sync(extract_pages, data)
    items = await anyio.to_thread.run_sync(
        chunk_pages, pages, settings.chunk_size, settings.chunk_overlap
    )
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Metin çıkarılamadı (taranmış PDF olabilir)")

    # Embedding (batch) — sorgu ve doküman aynı modelden
    embedder = GeminiEmbeddingProvider(request.app.state.genai_client, settings.embedding_model)
    embeddings = await embedder.embed([content for _, content in items])

    repo = DocumentRepository()
    document_id = await repo.add_document(
        user_id=user.id,
        filename=file.filename or "untitled.pdf",
        items=[(page, content, emb) for (page, content), emb in zip(items, embeddings)],
    )
    return {"document_id": str(document_id), "chunks": len(items)}
