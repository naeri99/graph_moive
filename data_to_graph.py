import os
from tool import get_neptune_client
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings("ignore")


def clean_value(value):
    """NaN, None, inf 값을 안전하게 처리"""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        if np.isnan(value) or np.isinf(value):
            return 0
        return float(value)
    return str(value)


class CreateGraph:
    """Neptune Analytics용 그래프 생성 클래스"""

    def __init__(self):
        self.neptune = get_neptune_client()
        print("✅ Neptune 클라이언트 초기화 완료")

    def close(self):
        print("Neptune 연결 종료")

    def db_cleanup(self):
        print("🗑️  데이터베이스 정리 중...")
        self.neptune.delete_all_data(confirm=True)
        print("✅ 데이터베이스 정리 완료")

    def create_constraints_indexes(self):
        print("ℹ️  Neptune Analytics는 제약조건을 자동 관리합니다")
        # Neptune Analytics는 별도의 제약조건 생성이 필요 없음


    def load_movies(self, csv_file, limit):
        limit_text = f"최대 {limit}개" if limit else "전체"
        print(f"📽️  영화 데이터 로딩 중: {csv_file} ({limit_text})")
        
        # CSV 파일 읽기
        if limit:
            df = pd.read_csv(csv_file, nrows=limit)
        else:
            df = pd.read_csv(csv_file)
        
        # NaN 값을 None으로 변환
        df = df.where(pd.notna(df), None)
        
        # 배치 처리
        batch_size = 100
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # UNWIND를 사용한 배치 삽입
            movies_data = []
            for _, row in batch.iterrows():
                tmdb_id = clean_value(row.get('tmdbId'))
                
                # tmdbId가 정수로 변환 가능한지 확인
                try:
                    if tmdb_id is not None:
                        tmdb_id_int = int(tmdb_id)
                    else:
                        continue
                except (ValueError, TypeError):
                    continue
                
                runtime_val = clean_value(row.get('runtime'))
                budget_val = clean_value(row.get('budget'))
                revenue_val = clean_value(row.get('revenue'))
                
                movie = {
                    'tmdbId': tmdb_id_int,
                    'title': clean_value(row.get('title')) or 'None',
                    'original_title': clean_value(row.get('original_title')) or 'None',
                    'adult': 'Yes' if clean_value(row.get('adult')) == 1 else 'No',
                    'budget': int(budget_val) if budget_val else 0,
                    'original_language': clean_value(row.get('original_language')) or 'None',
                    'revenue': int(revenue_val) if revenue_val else 0,
                    'tagline': clean_value(row.get('tagline')) or 'None',
                    'overview': clean_value(row.get('overview')) or 'None',
                    'release_date': clean_value(row.get('release_date')) or 'None',
                    'runtime': float(runtime_val) if runtime_val else 0.0,
                    'belongs_to_collection': clean_value(row.get('belongs_to_collection')) or 'None'
                }
                movies_data.append(movie)
            
            if movies_data:
                query = """
                UNWIND $movies AS movie
                MERGE (m:Movie {tmdbId: movie.tmdbId})
                SET m.title = movie.title,
                    m.original_title = movie.original_title,
                    m.adult = movie.adult,
                    m.budget = movie.budget,
                    m.original_language = movie.original_language,
                    m.revenue = movie.revenue,
                    m.tagline = movie.tagline,
                    m.overview = movie.overview,
                    m.release_date = movie.release_date,
                    m.runtime = movie.runtime,
                    m.belongs_to_collection = movie.belongs_to_collection
                """
                
                self.neptune.execute_query(query, {'movies': movies_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 영화 {total}개 로딩 완료")

    def load_genres(self, csv_file):
        print(f"🎭 장르 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            genres_data = []
            for _, row in batch.iterrows():
                tmdb_id = clean_value(row.get('tmdbId'))
                genre_id = clean_value(row.get('genre_id'))
                
                # tmdbId와 genre_id가 정수로 변환 가능한지 확인
                try:
                    if tmdb_id is not None and genre_id is not None:
                        genres_data.append({
                            'tmdbId': int(tmdb_id),
                            'genre_id': int(genre_id),
                            'genre_name': clean_value(row.get('genre_name')) or 'Unknown'
                        })
                except (ValueError, TypeError):
                    continue
            
            if genres_data:
                query = """
                UNWIND $genres AS genre
                MATCH (m:Movie {tmdbId: genre.tmdbId})
                MERGE (g:Genre {genre_id: genre.genre_id})
                SET g.genre_name = genre.genre_name
                MERGE (m)-[:HAS_GENRE]->(g)
                """
                
                self.neptune.execute_query(query, {'genres': genres_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 장르 {total}개 로딩 완료")

    def load_production_companies(self, csv_file):
        print(f"🏢 제작사 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            companies_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    company_id = clean_value(row.get('company_id'))
                    if tmdb_id is not None and company_id is not None:
                        companies_data.append({
                            'tmdbId': int(tmdb_id),
                            'company_id': int(company_id),
                            'company_name': clean_value(row.get('company_name')) or 'Unknown'
                        })
                except (ValueError, TypeError):
                    continue
            
            if companies_data:
                query = """
                UNWIND $companies AS company
                MATCH (m:Movie {tmdbId: company.tmdbId})
                MERGE (pc:ProductionCompany {company_id: company.company_id})
                SET pc.company_name = company.company_name
                MERGE (m)-[:PRODUCED_BY]->(pc)
                """
                
                self.neptune.execute_query(query, {'companies': companies_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 제작사 {total}개 로딩 완료")

    def load_production_countries(self, csv_file):
        print(f"🌍 제작 국가 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            countries_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    country_code = clean_value(row.get('country_code'))
                    if tmdb_id is not None and country_code is not None:
                        countries_data.append({
                            'tmdbId': int(tmdb_id),
                            'country_code': str(country_code),
                            'country_name': clean_value(row.get('country_name')) or 'Unknown'
                        })
                except (ValueError, TypeError):
                    continue
            
            if countries_data:
                query = """
                UNWIND $countries AS country
                MATCH (m:Movie {tmdbId: country.tmdbId})
                MERGE (c:Country {country_code: country.country_code})
                SET c.country_name = country.country_name
                MERGE (m)-[:PRODUCED_IN]->(c)
                """
                
                self.neptune.execute_query(query, {'countries': countries_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 제작 국가 {total}개 로딩 완료")

    def load_spoken_languages(self, csv_file):
        print(f"🗣️  언어 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            languages_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    language_code = clean_value(row.get('language_code'))
                    if tmdb_id is not None and language_code is not None:
                        languages_data.append({
                            'tmdbId': int(tmdb_id),
                            'language_code': str(language_code),
                            'language_name': clean_value(row.get('language_name')) or 'Unknown'
                        })
                except (ValueError, TypeError):
                    continue
            
            if languages_data:
                query = """
                UNWIND $languages AS lang
                MATCH (m:Movie {tmdbId: lang.tmdbId})
                MERGE (l:SpokenLanguage {language_code: lang.language_code})
                SET l.language_name = lang.language_name
                MERGE (m)-[:HAS_LANGUAGE]->(l)
                """
                
                self.neptune.execute_query(query, {'languages': languages_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 언어 {total}개 로딩 완료")

    def load_keywords(self, csv_file):
        print(f"🔑 키워드 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            keywords_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    keywords = clean_value(row.get('keywords'))
                    if tmdb_id is not None and keywords is not None:
                        keywords_data.append({
                            'tmdbId': int(tmdb_id),
                            'keywords': str(keywords)
                        })
                except (ValueError, TypeError):
                    continue
            
            if keywords_data:
                query = """
                UNWIND $keywords AS kw
                MATCH (m:Movie {tmdbId: kw.tmdbId})
                SET m.keywords = kw.keywords
                """
                
                self.neptune.execute_query(query, {'keywords': keywords_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 키워드 {total}개 로딩 완료")

    def load_person_actors(self, csv_file):
        print(f"🎬 배우 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            actors_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    actor_id = clean_value(row.get('actor_id'))
                    cast_id = clean_value(row.get('cast_id'))
                    
                    if tmdb_id is not None and actor_id is not None:
                        actors_data.append({
                            'tmdbId': int(tmdb_id),
                            'actor_id': int(actor_id),
                            'name': clean_value(row.get('name')) or 'Unknown',
                            'character': clean_value(row.get('character')) or 'None',
                            'cast_id': int(cast_id) if cast_id else 0
                        })
                except (ValueError, TypeError):
                    continue
            
            if actors_data:
                query = """
                UNWIND $actors AS actor
                MATCH (m:Movie {tmdbId: actor.tmdbId})
                MERGE (p:Person:Actor {actor_id: actor.actor_id})
                SET p.name = actor.name, p.role = 'actor'
                MERGE (p)-[a:ACTED_IN]->(m)
                SET a.character = actor.character, a.cast_id = actor.cast_id
                """
                
                self.neptune.execute_query(query, {'actors': actors_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 배우 {total}개 로딩 완료")

    def load_person_crew(self, csv_file):
        print(f"🎥 제작진 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        # Director와 Producer만 필터링
        df = df[df['job'].isin(['Director', 'Producer'])]
        
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            crew_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    crew_id = clean_value(row.get('crew_id'))
                    
                    if tmdb_id is not None and crew_id is not None:
                        job = clean_value(row.get('job')) or 'Unknown'
                        crew_data.append({
                            'tmdbId': int(tmdb_id),
                            'crew_id': int(crew_id),
                            'name': clean_value(row.get('name')) or 'Unknown',
                            'job': job
                        })
                except (ValueError, TypeError):
                    continue
            
            if crew_data:
                # Director 처리
                directors = [c for c in crew_data if c['job'] == 'Director']
                if directors:
                    query = """
                    UNWIND $crew AS person
                    MATCH (m:Movie {tmdbId: person.tmdbId})
                    MERGE (p:Person:Director {crew_id: person.crew_id})
                    SET p.name = person.name, p.role = 'Director'
                    MERGE (p)-[:DIRECTED]->(m)
                    """
                    self.neptune.execute_query(query, {'crew': directors})
                
                # Producer 처리
                producers = [c for c in crew_data if c['job'] == 'Producer']
                if producers:
                    query = """
                    UNWIND $crew AS person
                    MATCH (m:Movie {tmdbId: person.tmdbId})
                    MERGE (p:Person:Producer {crew_id: person.crew_id})
                    SET p.name = person.name, p.role = 'Producer'
                    MERGE (p)-[:PRODUCED]->(m)
                    """
                    self.neptune.execute_query(query, {'crew': producers})
                
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 제작진 {total}개 로딩 완료")

    def load_links(self, csv_file):
        print(f"🔗 링크 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            links_data = []
            for _, row in batch.iterrows():
                try:
                    tmdb_id = clean_value(row.get('tmdbId'))
                    if tmdb_id is not None:
                        links_data.append({
                            'tmdbId': int(tmdb_id),
                            'movieId': int(clean_value(row.get('movieId')) or 0),
                            'imdbId': clean_value(row.get('imdbId')) or ''
                        })
                except (ValueError, TypeError):
                    continue
            
            if links_data:
                query = """
                UNWIND $links AS link
                MATCH (m:Movie {tmdbId: link.tmdbId})
                SET m.movieId = link.movieId, m.imdbId = link.imdbId
                """
                
                self.neptune.execute_query(query, {'links': links_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 링크 {total}개 로딩 완료")

    def load_ratings(self, csv_file):
        print(f"⭐ 평점 데이터 로딩 중: {csv_file}")
        
        df = pd.read_csv(csv_file)
        batch_size = 500
        total = len(df)
        
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            
            ratings_data = []
            for _, row in batch.iterrows():
                try:
                    movie_id = clean_value(row.get('movieId'))
                    user_id = clean_value(row.get('userId'))
                    rating = clean_value(row.get('rating'))
                    timestamp = clean_value(row.get('timestamp'))
                    
                    if movie_id is not None and user_id is not None:
                        ratings_data.append({
                            'movieId': int(movie_id),
                            'userId': int(user_id),
                            'rating': float(rating) if rating else 0.0,
                            'timestamp': int(timestamp) if timestamp else 0
                        })
                except (ValueError, TypeError):
                    continue
            
            if ratings_data:
                query = """
                UNWIND $ratings AS rating
                MATCH (m:Movie {movieId: rating.movieId})
                MERGE (u:Person:User {user_id: rating.userId})
                SET u.role = 'user'
                MERGE (u)-[r:RATED]->(m)
                SET r.rating = rating.rating, r.timestamp = rating.timestamp
                """
                
                self.neptune.execute_query(query, {'ratings': ratings_data})
                print(f"  ✅ {i+1}-{min(i+batch_size, total)} 처리 완료")
        
        print(f"✅ 평점 {total}개 로딩 완료")



def main():
    """Neptune Analytics에 영화 데이터 로딩"""
    
    print("=" * 80)
    print("Neptune Analytics 데이터 로딩 시작")
    print("=" * 80)
    
    graph = CreateGraph()
    
    # 데이터베이스 정리 (선택)
    # graph.db_cleanup()
    
    # 제약조건 생성 (Neptune은 자동 관리)
    graph.create_constraints_indexes()
    
    # 데이터 로딩
    movie_limit = None  # 전체 영화 로딩
    data_path = "./data"
    
    try:
        # # 영화 로딩 (전체)
        # graph.load_movies(f'{data_path}/normalized_movies.csv', movie_limit)
        
        # # 장르 로딩
        # graph.load_genres(f'{data_path}/normalized_genres.csv')
        
        # # 제작사 로딩
        # graph.load_production_companies(f'{data_path}/normalized_production_companies.csv')
        
        # # 제작 국가 로딩
        # graph.load_production_countries(f'{data_path}/normalized_production_countries.csv')
        
        # # 언어 로딩
        # graph.load_spoken_languages(f'{data_path}/normalized_spoken_languages.csv')
        
        # # 키워드 로딩
        # graph.load_keywords(f'{data_path}/normalized_keywords.csv')
        
        # # 배우 로딩
        # graph.load_person_actors(f'{data_path}/normalized_cast.csv')
        
        # # 제작진 로딩
        # graph.load_person_crew(f'{data_path}/normalized_crew.csv')
        
        # # 링크 로딩
        # graph.load_links(f'{data_path}/normalized_links.csv')
        
        # # 평점 로딩
        graph.load_ratings(f'{data_path}/normalized_ratings_small.csv')
        
        print("\n" + "=" * 80)
        print("✅ 데이터 로딩 완료!")
        print("=" * 80)
        
        # 통계 확인
        stats = graph.neptune.get_stats()
        print(f"\n📊 최종 통계:")
        print(f"   총 노드: {stats['total_nodes']}")
        print(f"   총 관계: {stats['total_relationships']}")
        print(f"   노드 레이블: {stats['node_labels']}")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        graph.close()


if __name__ == "__main__":
    main()