"""
벡터 검색 결과 그래프 시각화
"""

import sys
sys.path.append('/home/ec2-user/strandtest/moive')

from tool import get_neptune_client
from bedrock_embedding import BedrockEmbedding
from pyvis.network import Network
import json
import webbrowser
import os


class SearchVisualizer:
    """벡터 검색 결과 시각화 클래스"""
    
    def __init__(self, bedrock_region='us-west-2'):
        """
        Args:
            bedrock_region: Bedrock 리전
        """
        self.neptune = get_neptune_client()
        self.embedder = BedrockEmbedding(region=bedrock_region)
        print("✅ SearchVisualizer 초기화 완료")
    
    def visualize_search_results(self, query: str, top_k: int = 3, 
                                output_file: str = "search_graph.html",
                                open_browser: bool = True):
        """
        벡터 검색 결과를 인터랙티브 그래프로 시각화
        
        Args:
            query: 검색 쿼리
            top_k: 결과 수
            output_file: 출력 HTML 파일명
            open_browser: 브라우저 자동 열기
        """
        print(f"\n🎨 벡터 검색 결과 시각화: '{query}'")
        
        try:
            # 1. 쿼리 임베딩 생성
            query_embedding = self.embedder.embed_text(query)
            embedding_str = json.dumps(query_embedding)
            
            # 2. 벡터 검색 + 1-hop 관계
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
            RETURN movie.tmdbId as movie_id,
                   movie.title AS title,
                   movie.release_date AS release_date,
                   score,
                   collect(DISTINCT {{id: g.genre_id, name: g.genre_name}}) AS genres,
                   collect(DISTINCT {{id: actor.actor_id, name: actor.name}})[..5] AS actors,
                   collect(DISTINCT {{id: director.crew_id, name: director.name}}) AS directors,
                   collect(DISTINCT {{id: pc.company_id, name: pc.company_name}})[..3] AS companies
            ORDER BY score DESC
            """
            
            result = self.neptune.execute_query(search_query)
            documents = result.get('results', [])
            
            if not documents:
                print("   ⚠️  검색 결과가 없습니다.")
                return None
            
            # 3. 그래프 생성
            net = Network(height="750px", width="100%", bgcolor="#222222", 
                         font_color="white", directed=True)
            
            # 물리 엔진 설정
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -8000,
                        "centralGravity": 0.3,
                        "springLength": 200,
                        "springConstant": 0.04
                    }
                },
                "nodes": {
                    "font": {"size": 14}
                },
                "edges": {
                    "smooth": {"type": "continuous"}
                }
            }
            """)
            
            # 쿼리 노드 추가
            net.add_node("QUERY", 
                        label=f"Query\n{query[:30]}...", 
                        color="#FF6B6B",
                        size=30,
                        title=query)
            
            # 4. 노드와 엣지 추가
            for doc in documents:
                movie_id = f"movie_{doc['movie_id']}"
                title = doc['title']
                score = doc['score']
                release_date = doc.get('release_date', 'N/A')
                
                # 영화 노드
                net.add_node(movie_id,
                            label=f"{title}\n({release_date[:4]})",
                            color="#4ECDC4",
                            size=25,
                            title=f"{title}\nScore: {score:.4f}\nRelease: {release_date}")
                
                # 쿼리 → 영화 엣지
                net.add_edge("QUERY", movie_id, 
                            label=f"{score:.3f}",
                            color="#FF6B6B",
                            width=3)
                
                # 장르 노드
                genres = doc.get('genres', [])
                for genre in genres:
                    if genre and genre.get('name'):
                        genre_id = f"genre_{genre['id']}"
                        genre_name = genre['name']
                        
                        if not net.get_node(genre_id):
                            net.add_node(genre_id,
                                        label=genre_name,
                                        color="#95E1D3",
                                        size=15,
                                        shape="box",
                                        title=f"Genre: {genre_name}")
                        
                        net.add_edge(movie_id, genre_id,
                                    label="HAS_GENRE",
                                    color="#95E1D3")
                
                # 배우 노드
                actors = doc.get('actors', [])
                for actor in actors:
                    if actor and actor.get('name'):
                        actor_id = f"actor_{actor['id']}"
                        actor_name = actor['name']
                        
                        if not net.get_node(actor_id):
                            net.add_node(actor_id,
                                        label=actor_name,
                                        color="#F38181",
                                        size=15,
                                        shape="dot",
                                        title=f"Actor: {actor_name}")
                        
                        net.add_edge(actor_id, movie_id,
                                    label="ACTED_IN",
                                    color="#F38181")
                
                # 감독 노드
                directors = doc.get('directors', [])
                for director in directors:
                    if director and director.get('name'):
                        director_id = f"director_{director['id']}"
                        director_name = director['name']
                        
                        if not net.get_node(director_id):
                            net.add_node(director_id,
                                        label=director_name,
                                        color="#AA96DA",
                                        size=18,
                                        shape="triangle",
                                        title=f"Director: {director_name}")
                        
                        net.add_edge(director_id, movie_id,
                                    label="DIRECTED",
                                    color="#AA96DA")
                
                # 제작사 노드
                companies = doc.get('companies', [])
                for company in companies:
                    if company and company.get('name'):
                        company_id = f"company_{company['id']}"
                        company_name = company['name']
                        
                        if not net.get_node(company_id):
                            net.add_node(company_id,
                                        label=company_name,
                                        color="#FCBAD3",
                                        size=15,
                                        shape="diamond",
                                        title=f"Production: {company_name}")
                        
                        net.add_edge(movie_id, company_id,
                                    label="PRODUCED_BY",
                                    color="#FCBAD3")
            
            # 5. HTML 파일 저장
            net.save_graph(output_file)
            print(f"\n✅ 시각화 완료: {output_file}")
            print(f"   노드 수: {len(net.nodes)}")
            print(f"   엣지 수: {len(net.edges)}")
            
            # 6. 브라우저 열기
            if open_browser:
                file_path = os.path.abspath(output_file)
                webbrowser.open(f'file://{file_path}')
                print(f"   🌐 브라우저에서 열림")
            
            return output_file
            
        except Exception as e:
            print(f"❌ 시각화 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def visualize_2hop_search(self, query: str, top_k: int = 2,
                             output_file: str = "search_2hop_graph.html",
                             open_browser: bool = True):
        """
        2-hop 벡터 검색 결과 시각화 (배우의 다른 영화 포함)
        
        Args:
            query: 검색 쿼리
            top_k: 결과 수
            output_file: 출력 HTML 파일명
            open_browser: 브라우저 자동 열기
        """
        print(f"\n🎨 2-Hop 벡터 검색 결과 시각화: '{query}'")
        
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.embedder.embed_text(query)
            embedding_str = json.dumps(query_embedding)
            
            # 2-hop 검색
            search_query = f"""
            CALL neptune.algo.vectors.topKByEmbedding(
                {embedding_str},
                {{topK: {top_k}, concurrency: 4}}
            )
            YIELD node, score
            WHERE node:Movie
            WITH node as movie, score
            MATCH (actor:Actor)-[:ACTED_IN]->(movie)
            WITH movie, score, actor
            LIMIT 10
            OPTIONAL MATCH (actor)-[:ACTED_IN]->(related:Movie)
            WHERE related <> movie
            RETURN movie.tmdbId as movie_id,
                   movie.title as title,
                   movie.release_date as release_date,
                   score,
                   actor.actor_id as actor_id,
                   actor.name as actor_name,
                   collect(DISTINCT {{id: related.tmdbId, title: related.title}})[..3] as related_movies
            ORDER BY score DESC
            """
            
            result = self.neptune.execute_query(search_query)
            documents = result.get('results', [])
            
            if not documents:
                print("   ⚠️  검색 결과가 없습니다.")
                return None
            
            # 그래프 생성
            net = Network(height="800px", width="100%", bgcolor="#1a1a1a",
                         font_color="white", directed=True)
            
            net.set_options("""
            {
                "physics": {
                    "enabled": true,
                    "barnesHut": {
                        "gravitationalConstant": -10000,
                        "centralGravity": 0.3,
                        "springLength": 250
                    }
                }
            }
            """)
            
            # 쿼리 노드
            net.add_node("QUERY",
                        label=f"Query\n{query[:30]}...",
                        color="#FF6B6B",
                        size=35,
                        title=query)
            
            # 노드와 엣지 추가
            processed_movies = set()
            processed_actors = set()
            
            for doc in documents:
                movie_id = f"movie_{doc['movie_id']}"
                title = doc['title']
                score = doc['score']
                
                # 메인 영화 노드
                if movie_id not in processed_movies:
                    net.add_node(movie_id,
                                label=f"{title}\n({doc.get('release_date', 'N/A')[:4]})",
                                color="#4ECDC4",
                                size=30,
                                title=f"{title}\nScore: {score:.4f}")
                    
                    net.add_edge("QUERY", movie_id,
                                label=f"{score:.3f}",
                                color="#FF6B6B",
                                width=4)
                    processed_movies.add(movie_id)
                
                # 배우 노드
                actor_id = f"actor_{doc['actor_id']}"
                actor_name = doc['actor_name']
                
                if actor_id not in processed_actors:
                    net.add_node(actor_id,
                                label=actor_name,
                                color="#F38181",
                                size=20,
                                shape="dot",
                                title=f"Actor: {actor_name}")
                    processed_actors.add(actor_id)
                
                net.add_edge(actor_id, movie_id,
                            label="ACTED_IN",
                            color="#F38181")
                
                # 관련 영화 노드 (2-hop)
                related_movies = doc.get('related_movies', [])
                for related in related_movies:
                    if related and related.get('title'):
                        related_id = f"movie_{related['id']}"
                        related_title = related['title']
                        
                        if related_id not in processed_movies:
                            net.add_node(related_id,
                                        label=related_title,
                                        color="#A8E6CF",
                                        size=15,
                                        title=f"Related: {related_title}")
                            processed_movies.add(related_id)
                        
                        net.add_edge(actor_id, related_id,
                                    label="ACTED_IN",
                                    color="#A8E6CF",
                                    dashes=True)
            
            # 저장
            net.save_graph(output_file)
            print(f"\n✅ 2-Hop 시각화 완료: {output_file}")
            print(f"   노드 수: {len(net.nodes)}")
            print(f"   엣지 수: {len(net.edges)}")
            
            if open_browser:
                file_path = os.path.abspath(output_file)
                webbrowser.open(f'file://{file_path}')
                print(f"   🌐 브라우저에서 열림")
            
            return output_file
            
        except Exception as e:
            print(f"❌ 2-Hop 시각화 실패: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """메인 함수"""
    print("=" * 80)
    print("벡터 검색 결과 그래프 시각화")
    print("=" * 80)
    
    visualizer = SearchVisualizer(bedrock_region='us-west-2')
    
    # 예제 쿼리
    query = "The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son."
    
    # 1-Hop 시각화
    print("\n" + "=" * 80)
    print("1-Hop 시각화")
    print("=" * 80)
    visualizer.visualize_search_results(query, top_k=3, 
                                       output_file="search_1hop.html")
    
    # 2-Hop 시각화
    print("\n" + "=" * 80)
    print("2-Hop 시각화")
    print("=" * 80)
    visualizer.visualize_2hop_search(query, top_k=2,
                                    output_file="search_2hop.html")
    
    print("\n" + "=" * 80)
    print("✅ 시각화 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
