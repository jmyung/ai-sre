from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyze_router, knowledge_router, search_router, monitor_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Redis AI SRE Assistant",
    description="AI 기반 Redis 장애 분석 및 트러블슈팅 가이드 시스템",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(analyze_router)
app.include_router(knowledge_router)
app.include_router(search_router)
app.include_router(monitor_router)


@app.get("/")
async def root():
    return {
        "message": "Redis AI SRE Assistant API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
