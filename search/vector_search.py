"""
Vector Search Implementation using Neptune Analytics and Bedrock Embeddings
"""

import sys
sys.path.append('/home/ec2-user/strandtest/moive')

from tool import get_neptune_client
from bedrock_embedding import BedrockEmbedding
import json


class VectorSearch:
    """Neptune Analytics 벡터 검색 클래스"""
    
    def __init__(self, bedrock_region='us-east-1'):
        """
        Args:
            bedrock_region: Bedrock 리전 (기본: us-east-1)
        """
        self.neptune = get_neptune_client()
        self.embedder = BedrockEmbedding(region=bedrock_region)
        print("✅ Vector Search 초기화 완료")
    
    def create_or_reset_vector_index(self):
        """벡터 인덱스 확인"""
        print("🔧 벡터 인덱스 확인 중...")
        
        try:
            # Neptune Analytics 벡터 인덱스는 그래프 생성 시 설정됨
            # 영화 노드 수 확인
            query = """
            MATCH (m:Movie)
            RETURN count(m) as count
            """
            result = self.neptune.execute_query(query)
            count = result.get('results', [{}])[0].get('count', 0)
            
            if count > 0:
                print(f"✅ 벡터 인덱스 준비 완료 (영화 노드: {count}개)")
                print("💡 Neptune Analytics 그래프에 벡터 인덱스(1024차원)가 활성화되어 있어야 합니다")
            else:
                print("⚠️  영화 노드가 없습니다. data_to_graph.py를 먼저 실행하세요.")
                
        except Exception as e:
            print(f"❌ 벡터 인덱스 확인 실패: {e}")
    
    def perform_vector_search(self, query: str, top_k: int = 3):
        """
        벡터 검색 수행 (Neptune 네이티브 벡터 검색)
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 결과 수
        """
        print(f"\n🔍 벡터 검색 수행: '{query}'")
        print(f"   Top-K: {top_k}")
        
        try:
            # 1. 쿼리 임베딩 생성
            print("   📝 쿼리 임베딩 생성 중...")
            query_embedding = self.embedder.embed_text(query)
            
            # 2. Neptune 벡터 검색 (neptune.algo.vectors.topKByEmbedding)
            # Neptune의 벡터 검색은 파라미터로 리스트를 직접 전달할 수 없어서
            # JSON 문자열로 변환하여 쿼리에 직접 삽입합니다
            embedding_str = json.dumps(query_embedding)
            
            search_query = f"""
            CALL neptune.algo.vectors.topKByEmbedding(
                {embedding_str},
                {{topK: {top_k}, concurrency: 4}}
            )
            YIELD node, score
            WHERE node:Movie
            RETURN node.title as title,
                   node.overview as overview,
                   node.release_date as release_date,
                   score
            ORDER BY score DESC
            """
            
            result = self.neptune.execute_query(search_query)
            
            # 3. 결과 출력
            documents = result.get('results', [])
            
            if not documents:
                print("   ⚠️  검색 결과가 없습니다.")
                print("   💡 벡터 인덱스가 활성화되어 있는지 확인하세요")
                return []
            
            print(f"\n📊 검색 결과 ({len(documents)}개):")
            print("=" * 80)
            
            for doc in documents:
                title = doc.get('title', 'N/A')
                overview = doc.get('overview', 'N/A')
                release_date = doc.get('release_date', 'N/A')
                score = doc.get('score', 0)
                
                print(f"Title: {title} ({release_date})")
                print(f"Overview: {overview[:200] if overview and overview != 'N/A' else 'N/A'}...")
                print(f"Score: {score:.4f}")
                print("-" * 80)
            
            return documents
            
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            print("💡 Neptune Analytics 그래프에 벡터 인덱스(1024차원)가 필요합니다")
            import traceback
            traceback.print_exc()
            return []
    
    def perform_vector_search_cypher(self, query: str, top_k: int = 3):
        """
        벡터 검색 수행 (Neptune 벡터 인덱스 사용 - 동일한 방식)
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 결과 수
        """
        print(f"\n🔍 Neptune 벡터 검색 수행: '{query}'")
        
        try:
            # 쿼리 임베딩 생성
            print("   📝 쿼리 임베딩 생성 중...")
            query_embedding = self.embedder.embed_text(query)
            
            # Neptune 벡터 검색 (neptune.algo.vectors.topKByEmbedding)
            # 이 방식은 Neptune Analytics의 벡터 인덱스를 사용합니다
            # 임베딩 벡터는 JSON 문자열로 변환하여 쿼리에 직접 삽입
            embedding_str = json.dumps(query_embedding)
            
            cypher_query = f"""
            CALL neptune.algo.vectors.topKByEmbedding(
                {embedding_str},
                {{topK: {top_k}, concurrency: 4}}
            )
            YIELD node, score
            WHERE node:Movie
            RETURN node.title AS title, 
                   node.overview AS overview,
                   node.release_date as release_date,
                   score
            ORDER BY score DESC
            """
            
            result = self.neptune.execute_query(cypher_query)
            
            # 결과 출력
            documents = result.get('results', [])
            
            if not documents:
                print("   ⚠️  검색 결과가 없습니다.")
                print("   💡 벡터 인덱스가 활성화되어 있는지 확인하세요")
                return []
            
            print(f"\n📊 검색 결과 ({len(documents)}개):")
            print("=" * 80)
            
            for doc in documents:
                title = doc.get('title', 'N/A')
                overview = doc.get('overview', 'N/A')
                release_date = doc.get('release_date', 'N/A')
                score = doc.get('score', 0)
                
                print(f"Title: {title} ({release_date})")
                print(f"Overview: {overview[:200] if overview and overview != 'N/A' else 'N/A'}...")
                print(f"Score: {score:.4f}")
                print("-" * 80)
            
            return documents
            
        except Exception as e:
            print(f"❌ 벡터 검색 실패: {e}")
            print("💡 Neptune Analytics 그래프에 벡터 인덱스(1024차원)가 필요합니다")
            import traceback
            traceback.print_exc()
            return []


    def perform_vector_search_with_hop(self, query: str, top_k: int = 3, hop_depth: int = 1):
        """
        벡터 검색 후 그래프 hop을 통해 관련 정보 가져오기
        
        Args:
            query: 검색 쿼리 텍스트
            top_k: 반환할 결과 수
            hop_depth: hop 깊이 (1 또는 2)
        """
        print(f"\n🔍 벡터 검색 + {hop_depth}-Hop 그래프 탐색: '{query}'")
        print(f"   Top-K: {top_k}")
        
        try:
            # 쿼리 임베딩 생성
            print("   📝 쿼리 임베딩 생성 중...")
            query_embedding = self.embedder.embed_text(query)
            embedding_str = json.dumps(query_embedding)
            
            # Neptune 벡터 검색 + 1-hop 관계 탐색
            if hop_depth == 1:
                search_query = f"""
                CALL neptune.algo.vectors.topKByEmbedding(
                    {embedding_str},
                    {{topK: {top_k}, concurrency: 4}}
                )
                YIELD node, score
                WHERE node:Movie
                WITH node as movie, score
                OPTIONAL MATCH (movie)-[:HAS_GENRE]->(g:Genre)
                OPTIONAL MATCH (actor:Actor)-[:ACTED_IN]->(movie)
                OPTIONAL MATCH (director:Director)-[:DIRECTED]->(movie)
                OPTIONAL MATCH (movie)-[:PRODUCED_BY]->(pc:ProductionCompany)
                RETURN movie.title AS title,
                       movie.overview AS overview,
                       movie.release_date AS release_date,
                       movie.runtime AS runtime,
                       movie.budget AS budget,
                       movie.revenue AS revenue,
                       score,
                       collect(DISTINCT g.genre_name) AS genres,
                       collect(DISTINCT actor.name)[..5] AS top_actors,
                       collect(DISTINCT director.name) AS directors,
                       collect(DISTINCT pc.company_name)[..3] AS production_companies
                ORDER BY score DESC
                """
            else:  # hop_depth == 2
                # 2-hop: 유사한 영화 → 그 영화의 배우 → 그 배우의 다른 영화
                search_query = f"""
                CALL neptune.algo.vectors.topKByEmbedding(
                    {embedding_str},
                    {{topK: {top_k}, concurrency: 4}}
                )
                YIELD node, score
                WHERE node:Movie
                WITH node as movie, score
                OPTIONAL MATCH (movie)-[:HAS_GENRE]->(g:Genre)
                OPTIONAL MATCH (actor:Actor)-[:ACTED_IN]->(movie)
                OPTIONAL MATCH (director:Director)-[:DIRECTED]->(movie)
                OPTIONAL MATCH (movie)-[:PRODUCED_BY]->(pc:ProductionCompany)
                OPTIONAL MATCH (actor)-[:ACTED_IN]->(related_movie:Movie)
                WHERE related_movie <> movie
                RETURN movie.title AS title,
                       movie.overview AS overview,
                       movie.release_date AS release_date,
                       movie.runtime AS runtime,
                       score,
                       collect(DISTINCT g.genre_name) AS genres,
                       collect(DISTINCT actor.name)[..5] AS top_actors,
                       collect(DISTINCT director.name) AS directors,
                       collect(DISTINCT pc.company_name)[..3] AS production_companies,
                       collect(DISTINCT related_movie.title)[..5] AS related_movies_by_actors
                ORDER BY score DESC
                """
            
            result = self.neptune.execute_query(search_query)
            documents = result.get('results', [])
            
            if not documents:
                print("   ⚠️  검색 결과가 없습니다.")
                return []
            
            print(f"\n📊 검색 결과 ({len(documents)}개) with {hop_depth}-Hop:")
            print("=" * 80)
            
            for i, doc in enumerate(documents, 1):
                title = doc.get('title', 'N/A')
                overview = doc.get('overview', 'N/A')
                release_date = doc.get('release_date', 'N/A')
                runtime = doc.get('runtime', 'N/A')
                score = doc.get('score', 0)
                genres = doc.get('genres', [])
                actors = doc.get('top_actors', [])
                directors = doc.get('directors', [])
                companies = doc.get('production_companies', [])
                
                print(f"\n{i}. {title} ({release_date})")
                print(f"   Score: {score:.4f}")
                print(f"   Runtime: {runtime} min")
                
                if genres and genres != [None]:
                    print(f"   Genres: {', '.join([g for g in genres if g])}")
                
                if directors and directors != [None]:
                    print(f"   Directors: {', '.join([d for d in directors if d])}")
                
                if actors and actors != [None]:
                    print(f"   Top Actors: {', '.join([a for a in actors if a])}")
                
                if companies and companies != [None]:
                    print(f"   Production: {', '.join([c for c in companies if c])}")
                
                if hop_depth == 2:
                    related = doc.get('related_movies_by_actors', [])
                    if related and related != [None]:
                        print(f"   Related Movies (by actors): {', '.join([r for r in related if r])}")
                
                if overview and overview != 'N/A':
                    print(f"   Overview: {overview[:150]}...")
                
                print("-" * 80)
            
            return documents
            
        except Exception as e:
            print(f"❌ 벡터 검색 + Hop 실패: {e}")
            import traceback
            traceback.print_exc()
            return []


def main():
    """메인 함수"""
    print("=" * 80)
    print("Neptune Analytics 벡터 검색 시작")
    print("=" * 80)
    
    # Vector Search 초기화
    search = VectorSearch(bedrock_region='us-west-2')
    
    # Step 1: 벡터 인덱스 확인
    search.create_or_reset_vector_index()
    
    # Step 2: 벡터 검색 수행
    query = "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son."
    
    # 방법 1: 기본 벡터 검색
    print("\n" + "=" * 80)
    print("방법 1: 기본 벡터 검색")
    print("=" * 80)
    search.perform_vector_search(query, top_k=3)
    
    # 방법 2: 벡터 검색 + 1-Hop
    print("\n" + "=" * 80)
    print("방법 2: 벡터 검색 + 1-Hop (장르, 배우, 감독, 제작사)")
    print("=" * 80)
    search.perform_vector_search_with_hop(query, top_k=3, hop_depth=1)
    
    # 방법 3: 벡터 검색 + 2-Hop
    print("\n" + "=" * 80)
    print("방법 3: 벡터 검색 + 2-Hop (관련 영화 포함)")
    print("=" * 80)
    search.perform_vector_search_with_hop(query, top_k=2, hop_depth=2)
    
    print("\n" + "=" * 80)
    print("✅ 벡터 검색 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
