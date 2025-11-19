"""
CSV에서 영화 overview를 읽어 Bedrock으로 임베딩하여 Neptune에 저장
"""

import sys
sys.path.append('/home/ec2-user/strandtest/moive')

from tool import get_neptune_client
from bedrock_embedding import BedrockEmbedding
import pandas as pd
import json
import numpy as np


def clean_value(value):
    """NaN, None 값 처리"""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    return str(value)


class MovieEmbeddingLoader:
    """CSV에서 영화 overview 임베딩 로더"""
    
    def __init__(self, csv_file, bedrock_region='us-west-2'):
        self.csv_file = csv_file
        self.neptune = get_neptune_client()
        self.embedder = BedrockEmbedding(region=bedrock_region)
        print("✅ 초기화 완료")
    
    def load_and_embed_movies(self, limit=None, batch_size=100):
        """CSV에서 영화를 읽고 임베딩하여 Neptune에 저장 (배치 최적화)"""
        print(f"\n📂 CSV 읽기: {self.csv_file}")
        
        # CSV 읽기
        if limit:
            df = pd.read_csv(self.csv_file, nrows=limit)
        else:
            df = pd.read_csv(self.csv_file)
        
        df = df.where(pd.notna(df), None)
        print(f"✅ {len(df)}개 영화 로드")
        
        # overview 필터링
        df_with_overview = df[
            (df['overview'].notna()) & 
            (df['overview'] != 'None') & 
            (df['overview'] != '')
        ].copy()
        
        total = len(df_with_overview)
        print(f"📝 overview 있음: {total}개")
        print(f"⚡ 배치 사이즈: {batch_size}개")
        
        if total == 0:
            return
        
        # 배치 처리
        success_count = 0
        error_count = 0
        skip_count = 0
        
        for i in range(0, total, batch_size):
            batch = df_with_overview.iloc[i:i+batch_size]
            batch_num = i//batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            print(f"\n📦 배치 {batch_num}/{total_batches} ({len(batch)}개) 처리 중...")
            
            batch_success = 0
            batch_skip = 0
            batch_error = 0
            
            for idx, row in batch.iterrows():
                tmdb_id = clean_value(row.get('tmdbId'))
                title = clean_value(row.get('title'))
                overview = clean_value(row.get('overview'))
                
                if not tmdb_id or not overview:
                    batch_skip += 1
                    continue
                
                try:
                    # 영화 존재 확인 (간소화)
                    check_query = f"MATCH (m:Movie {{tmdbId: {int(tmdb_id)}}}) RETURN m.tmdbId LIMIT 1"
                    check_result = self.neptune.execute_query(check_query)
                    
                    if not check_result.get('results'):
                        batch_skip += 1
                        continue
                    
                    # 임베딩 생성
                    embedding = self.embedder.embed_text(overview)
                    embedding_str = json.dumps(embedding)
                    
                    # 벡터 저장 (단일 쿼리로 최적화)
                    upsert_query = f"""
                    MATCH (m:Movie {{tmdbId: {int(tmdb_id)}}})
                    CALL neptune.algo.vectors.upsert(m, {embedding_str})
                    YIELD success
                    RETURN success
                    """
                    
                    upsert_result = self.neptune.execute_query(upsert_query)
                    
                    if upsert_result.get('results', [{}])[0].get('success'):
                        batch_success += 1
                    else:
                        batch_error += 1
                        
                except Exception as e:
                    batch_error += 1
                    if batch_error <= 3:  # 처음 3개 에러만 출력
                        print(f"  ❌ {title}: {str(e)[:50]}")
            
            # 배치 결과
            success_count += batch_success
            skip_count += batch_skip
            error_count += batch_error
            
            print(f"  ✅ 성공: {batch_success} | ⚠️ 스킵: {batch_skip} | ❌ 실패: {batch_error}")
            print(f"  📊 진행률: {i+len(batch)}/{total} ({(i+len(batch))/total*100:.1f}%)")
        
        # 최종 결과
        print("\n" + "=" * 80)
        print(f"✅ 총 성공: {success_count}")
        print(f"⚠️  총 스킵: {skip_count}")
        print(f"❌ 총 실패: {error_count}")
        print(f"📊 성공률: {success_count/(success_count+error_count)*100:.1f}%" if (success_count+error_count) > 0 else "N/A")
    
    def test_vector_search(self, query_text, top_k=5):
        """벡터 검색 테스트 (Neptune 네이티브 벡터 검색)"""
        print(f"\n🔍 검색: '{query_text}'")
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedder.embed_text(query_text)
            embedding_str = json.dumps(query_embedding)
            
            # Neptune 벡터 검색 (파라미터 없이 직접 삽입)
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
            results = result.get('results', [])
            
            if results:
                print(f"\n✅ 상위 {len(results)}개:")
                for i, r in enumerate(results, 1):
                    print(f"\n{i}. {r['title']} ({r.get('release_date', 'N/A')})")
                    print(f"   유사도 점수: {r['score']:.4f}")
                    overview = r.get('overview', '')
                    if overview:
                        print(f"   줄거리: {overview[:100]}...")
            else:
                print("❌ 결과 없음")
                print("\n💡 벡터 인덱스가 활성화되어 있는지 확인하세요")
                
        except Exception as e:
            print(f"❌ 실패: {e}")
            print("\n💡 Neptune Analytics 그래프에 벡터 인덱스(1024차원)가 필요합니다")


def main():
    csv_file = "/home/ec2-user/strandtest/moive/normalized_data/normalized_movies.csv"
    
    print("=" * 80)
    print("영화 Overview 임베딩 및 Neptune 저장")
    print("=" * 80)
    
    loader = MovieEmbeddingLoader(csv_file)
    
    # 전체 영화 처리 (배치 사이즈 100)
    print("\n📝 전체 영화 처리 시작...")
    loader.load_and_embed_movies(limit=None, batch_size=100)
    
    # 검색 테스트
    print("\n" + "=" * 80)
    print("벡터 검색 테스트")
    print("=" * 80)
    
    test_queries = [
        "action movie with great visual effects",
        "romantic comedy about love",
        "science fiction space adventure"
    ]
    
    for query in test_queries:
        loader.test_vector_search(query, top_k=3)
    
    print("\n" + "=" * 80)
    print("✅ 모든 작업 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
