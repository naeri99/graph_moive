"""
Vector Search 테스트 스크립트
"""

from vector_search import VectorSearch


def test_basic_search():
    """기본 벡터 검색 테스트"""
    print("=" * 80)
    print("벡터 검색 테스트")
    print("=" * 80)
    
    # Vector Search 초기화
    search = VectorSearch(bedrock_region='us-west-2')
    
    # 테스트 쿼리들
    test_queries = [
        "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.",
        "A young wizard discovers his magical heritage and attends a school of witchcraft.",
        "A team of superheroes must unite to save the world from an alien invasion.",
        "A romantic comedy about two people who fall in love in New York City."
    ]
    
    # 각 쿼리로 검색 수행
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"테스트 {i}/{len(test_queries)}")
        print(f"{'='*80}")
        
        results = search.perform_vector_search(query, top_k=3)
        
        if results:
            print(f"✅ {len(results)}개 결과 찾음")
        else:
            print("⚠️  결과 없음")
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)


def test_cypher_search():
    """Cypher 직접 사용 검색 테스트"""
    print("=" * 80)
    print("Cypher 벡터 검색 테스트")
    print("=" * 80)
    
    search = VectorSearch(bedrock_region='us-west-2')
    
    query = "A thrilling action movie with car chases and explosions"
    
    results = search.perform_vector_search_cypher(query, top_k=5)
    
    if results:
        print(f"\n✅ {len(results)}개 결과 찾음")
    else:
        print("\n⚠️  결과 없음")


def test_hop_search():
    """Hop 검색 테스트"""
    print("=" * 80)
    print("벡터 검색 + Hop 테스트")
    print("=" * 80)
    
    search = VectorSearch(bedrock_region='us-west-2')
    
    # 1-Hop 테스트
    print("\n" + "=" * 80)
    print("1-Hop: 영화 + 장르/배우/감독/제작사")
    print("=" * 80)
    query = "A romantic comedy about falling in love in a big city"
    results = search.perform_vector_search_with_hop(query, top_k=3, hop_depth=1)
    
    if results:
        print(f"\n✅ {len(results)}개 결과 찾음")
    
    # 2-Hop 테스트
    print("\n" + "=" * 80)
    print("2-Hop: 영화 + 관련 정보 + 배우의 다른 영화")
    print("=" * 80)
    query = "Science fiction movie about space exploration"
    results = search.perform_vector_search_with_hop(query, top_k=2, hop_depth=2)
    
    if results:
        print(f"\n✅ {len(results)}개 결과 찾음")


if __name__ == "__main__":
    # 기본 검색 테스트
    test_basic_search()
    
    # Cypher 검색 테스트
    print("\n\n")
    test_cypher_search()
    
    # Hop 검색 테스트
    print("\n\n")
    test_hop_search()
