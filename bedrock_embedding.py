"""
Bedrock 임베딩 처리 클래스 (LangChain 없이)
"""

import boto3
import json
from typing import List, Union


class BedrockEmbedding:
    """Bedrock 임베딩 클래스"""
    
    def __init__(self, region: str = 'us-west-2', model_id: str = "amazon.titan-embed-text-v2:0"):
        """
        Args:
            region: AWS 리전
            model_id: Bedrock 임베딩 모델 ID
        """
        self.region = region
        self.model_id = model_id
        self.client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region
        )
    
    def embed_text(self, text: str) -> List[float]:
        """
        단일 텍스트 임베딩
        
        Args:
            text: 임베딩할 텍스트
            
        Returns:
            임베딩 벡터 (리스트)
        """
        try:
            # Titan 임베딩 모델 요청 형식
            body = json.dumps({
                "inputText": text
            })
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType='application/json',
                accept='application/json'
            )
            
            # 응답 파싱
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding')
            
            return embedding
            
        except Exception as e:
            print(f"❌ 임베딩 실패: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        여러 텍스트 임베딩
        
        Args:
            texts: 임베딩할 텍스트 리스트
            
        Returns:
            임베딩 벡터 리스트
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        # Titan v2 모델은 1024 차원
        if "titan-embed-text-v2" in self.model_id:
            return 1024
        # Titan v1 모델은 1536 차원
        elif "titan-embed-text-v1" in self.model_id:
            return 1536
        else:
            # 실제로 임베딩해서 차원 확인
            test_embedding = self.embed_text("test")
            return len(test_embedding)


def example_usage():
    """사용 예제"""
    
    print("=" * 60)
    print("Bedrock 임베딩 테스트")
    print("=" * 60)
    
    # 임베딩 클래스 생성
    embedder = BedrockEmbedding(region='us-west-2')
    
    # 1. 단일 텍스트 임베딩
    print("\n1️⃣  단일 텍스트 임베딩")
    text = "안녕하세요, AWS Bedrock 임베딩 테스트입니다."
    embedding = embedder.embed_text(text)
    print(f"   텍스트: {text}")
    print(f"   임베딩 차원: {len(embedding)}")
    print(f"   임베딩 벡터 (처음 5개): {embedding[:5]}")
    
    # 2. 여러 텍스트 임베딩
    print("\n2️⃣  여러 텍스트 임베딩")
    texts = [
        "첫 번째 문장입니다.",
        "두 번째 문장입니다.",
        "세 번째 문장입니다."
    ]
    embeddings = embedder.embed_texts(texts)
    print(f"   총 {len(embeddings)}개 텍스트 임베딩 완료")
    for i, emb in enumerate(embeddings, 1):
        print(f"   {i}. 차원: {len(emb)}, 처음 3개 값: {emb[:3]}")
    
    # 3. 임베딩 차원 확인
    print("\n3️⃣  임베딩 차원")
    dimension = embedder.get_embedding_dimension()
    print(f"   모델 차원: {dimension}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    example_usage()
