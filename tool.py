import boto3
import json
from typing import Optional, Dict, Any


# Neptune Analytics 연결 설정
NEPTUNE_GRAPH_ID = "g-z8n5so6q32"
NEPTUNE_REGION = "us-east-1"
NEPTUNE_ARN = "arn:aws:neptune-graph:us-east-1:476114117552:graph/g-z8n5so6q32"


class NeptuneAnalyticsClient:
    """Neptune Analytics 접속 클라이언트"""
    
    def __init__(self, graph_id: str = NEPTUNE_GRAPH_ID, region: str = NEPTUNE_REGION):
        """
        Args:
            graph_id: Neptune Analytics 그래프 ID (기본: g-z8n5so6q32)
            region: AWS 리전 (기본: us-east-1)
        """
        self.graph_id = graph_id
        self.region = region
        self.arn = NEPTUNE_ARN
        
        # Neptune 연결 세션 구성
        self.session = boto3.Session(region_name=region)
        self.client = self.session.client('neptune-graph')
        
        print(f"✅ Neptune 연결 준비 완료")
        print(f"   Graph ID: {self.graph_id}")
        print(f"   Region: {self.region}")
        
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        openCypher 쿼리 실행
        
        Args:
            query: openCypher 쿼리 문자열
            parameters: 쿼리 파라미터 (선택)
            
        Returns:
            쿼리 결과
        """
        try:
            request = {
                'graphIdentifier': self.graph_id,
                'queryString': query,
                'language': 'OPEN_CYPHER'
            }
            
            if parameters:
                request['parameters'] = parameters
            
            # 쿼리 실행
            response = self.client.execute_query(**request)
            
            # 응답 파싱
            payload = response['payload'].read().decode('utf-8')
            result = json.loads(payload)
            
            return result
            
        except Exception as e:
            print(f"❌ 쿼리 실행 실패: {e}")
            raise
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        try:
            result = self.execute_query("MATCH (n) RETURN count(n) as count LIMIT 1")
            count = result.get('results', [{}])[0].get('count', 0)
            print(f"✅ 연결 성공! 총 노드 수: {count}")
            return True
        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            return False
    
    def delete_all_data(self, confirm: bool = False) -> bool:
        """
        그래프의 모든 데이터 삭제
        
        Args:
            confirm: True로 설정해야 실행됨 (안전장치)
            
        Returns:
            성공 여부
        """
        if not confirm:
            print("⚠️  경고: 모든 데이터를 삭제하려면 confirm=True로 호출하세요")
            return False
        
        try:
            # 모든 노드와 관계 삭제
            print("🗑️  모든 데이터 삭제 중...")
            self.execute_query("MATCH (n) DETACH DELETE n")
            
            # 확인
            result = self.execute_query("MATCH (n) RETURN count(n) as count")
            count = result.get('results', [{}])[0].get('count', 0)
            
            if count == 0:
                print("✅ 모든 데이터 삭제 완료")
                return True
            else:
                print(f"⚠️  {count}개 노드가 남아있습니다")
                return False
                
        except Exception as e:
            print(f"❌ 삭제 실패: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """그래프 통계"""
        try:
            # 노드 수
            node_result = self.execute_query("MATCH (n) RETURN count(n) as count")
            node_count = node_result.get('results', [{}])[0].get('count', 0)
            
            # 관계 수
            rel_result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.get('results', [{}])[0].get('count', 0)
            
            # 레이블별 노드 수
            label_result = self.execute_query(
                "MATCH (n) RETURN labels(n)[0] as label, count(*) as count"
            )
            labels = {r['label']: r['count'] for r in label_result.get('results', [])}
            
            stats = {
                'total_nodes': node_count,
                'total_relationships': rel_count,
                'node_labels': labels
            }
            
            return stats
            
        except Exception as e:
            print(f"❌ 통계 조회 실패: {e}")
            return {}


# 전역 Neptune 클라이언트 인스턴스
def get_neptune_client() -> NeptuneAnalyticsClient:
    """Neptune 클라이언트 싱글톤 인스턴스 반환"""
    if not hasattr(get_neptune_client, '_instance'):
        get_neptune_client._instance = NeptuneAnalyticsClient()
    return get_neptune_client._instance


# # 사용 예제
# if __name__ == "__main__":
#     print("=" * 60)
#     print("Neptune Analytics 연결 테스트")
#     print("=" * 60)
    
#     # 클라이언트 생성
#     neptune = get_neptune_client()
    
#     # 연결 테스트
#     neptune.test_connection()
    
#     # 통계 확인
#     print("\n📊 현재 그래프 통계:")
#     stats = neptune.get_stats()
#     print(json.dumps(stats, indent=2, ensure_ascii=False))
    # neptune.delete_all_data(True)
    # 모든 데이터 삭제 (주석 해제하여 사용)
    # print("\n🗑️  데이터 삭제:")
    # neptune.delete_all_data(confirm=True)
    # 
    # # 삭제 후 통계
    # print("\n📊 삭제 후 통계:")
    # stats = neptune.get_stats()
    # print(json.dumps(stats, indent=2, ensure_ascii=False))