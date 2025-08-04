import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from typing import List, Dict
import uuid  # ID 생성용
#from sentence_transformers import SentenceTransformer  # 추가: Ko-BGE용

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# MongoDB 연결 (기존 collection 사용)
client = MongoClient(MONGODB_URI)
db = client["halla_academic_db"]
collection = db["regulation_chunks"]

# Pinecone 연결
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "halla-academic-index"  # 인덱스 이름 (카테고리별 namespace 사용)

# 인덱스 생성 (이미 있으면 스킵)
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # OpenAI 임베딩 차원  
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")  # 당신의 리전으로 변경
    )
index = pc.Index(index_name)

# OpenAI 임베딩 클라이언트
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def get_embedding(text: str) -> List[float]:
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"  # 비용/성능 균형 좋은 모델
    )
    return response.data[0].embedding

def upload_chunks_to_pinecone(category: str = None, batch_size: int = 100):
    """MongoDB 청크를 카테고리 필터로 읽어 Pinecone 업로드"""
    query = {"metadata.category": category} if category else {}
    chunks = list(collection.find(query))
    print(f"업로드 대상 청크 수: {len(chunks)}개 (카테고리: {category or '전체'})")

    vectors = []
    for chunk in chunks:
        embedding = get_embedding(chunk["text"])
        id = str(uuid.uuid4())  # 고유 ID
        metadata = chunk["metadata"]  # 카테고리 등 기존 메타데이터 유지
        metadata["text_preview"] = chunk["text"][:100]  # 디버그용
        vectors.append({
            "id": id,
            "values": embedding,
            "metadata": metadata
        })

        # Batch 업로드 (100개씩)
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors, namespace=category or "default")  # 카테고리별 namespace로 구분 저장
            vectors = []
            print(f"Batch 업로드 완료: {batch_size}개")

    # 남은 부분 업로드
    if vectors:
        index.upsert(vectors=vectors, namespace=category or "default")
        print("최종 Batch 업로드 완료")

