import os
import openai
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Checklist
from typing import List, Dict

# --- [추가된 Import] Vector DB & Embedding 관련 ---
from app.database import get_db
from app.models import Checklist
from app.services.vector_db_service import SessionLocal, KnowledgeBase, get_embedding # Vector DB 모델

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 체크리스트 데이터 (machine_id별)
CHECKLISTS = {
    # 아래와 같은 형식으로 기계 라벨 값 넣고
    # {"index": 1, "todo": "첫 번째 안내 말"}, ...} 으로 생성하면 됩니다~!
    "1": [  # 믹싱기
        {"index": 1, "todo": "믹서 커버 개방 시 즉각 정지가 작동하나요?", "done": False, "summary": "기계적 위험 통제"},
        {"index": 2, "todo": "유기 용제(NMP) 주입 배관의 연결부 누출 흔적이 없나요?", "done": False, "summary": "유해 물질 노출 방지"},
        {"index": 3, "todo": "국소배기장치의 풍속이 기준치 이상으로 유지되나요?", "done": False, "summary": "작업 환경 관리"},
        {"index": 4, "todo": "설비 외함 및 배관의 접지 상태가 양호한가요?", "done": False, "summary": "화재/폭발 리스크 평가"},
    ],
    "2": [  # 코터
        {"index": 1, "todo": "건조로 내부 온도 센서 및 과열 방지 장치가 정상인가요?", "done": False, "summary": "비상 대응 준비"},
        {"index": 2, "todo": "롤러 진입부에 방호 가드나 비상 정지 로프가 설치되었나요?", "done": False, "summary": "작업자 보호 장치"},
        {"index": 3, "todo": "NMP 농도 감지기가 정상 작동하며 알람이 울리나요?", "done": False, "summary": "실시간 모니터링"}
    ],
    "3": [  # 슬리터
        {"index": 1, "todo": "원형 칼날의 마모나 파손 상태가 없나요?", "done": False, "summary": "설비 무결성 유지"},
        {"index": 2, "todo": "칼날 교체 시 전원이 완전히 차단(LOTO)되었나요?", "done": False, "summary": "안전 작업 절차 준수"},
    ],
}

def get_checklist(machine_id: str, db: Session = None) -> List[Dict]:
    """
    데이터베이스에서 특정 machine_id의 체크리스트를 조회합니다.
    db가 None이면 메모리에서 조회합니다 (백업용).
    """
    if db is not None:
        try:
            checklists = db.query(Checklist).filter(Checklist.machine_id == machine_id).all()
            return [checklist.to_dict() for checklist in checklists]
        except Exception as e:
            print(f"DB 조회 중 오류 발생: {e}, 메모리에서 조회합니다.")
    
    # 백업: 메모리에서 조회
    return CHECKLISTS.get(machine_id, [])

def update_checklist_item(machine_id: str, item_index: int, done: bool, db: Session = None) -> bool:
    """
    데이터베이스에서 특정 체크리스트 항목의 done 상태를 업데이트합니다.
    db가 None이면 메모리에서 업데이트합니다 (백업용).
    
    Args:
        machine_id: 기계 ID
        item_index: 체크리스트 항목 인덱스
        done: 완료 상태
        db: 데이터베이스 세션
        
    Returns:
        bool: 업데이트 성공 여부
    """
    if db is not None:
        try:
            item = db.query(Checklist).filter(
                Checklist.machine_id == machine_id,
                Checklist.item_index == item_index
            ).first()
            
            if item:
                item.done = done
                db.commit()
                return True
            return False
        except Exception as e:
            db.rollback()
            print(f"DB 업데이트 중 오류 발생: {e}, 메모리에서 업데이트합니다.")
    
    # 백업: 메모리에서 업데이트
    if machine_id not in CHECKLISTS:
        return False
        
    checklist = CHECKLISTS[machine_id]
    for item in checklist:
        if item["index"] == item_index:
            item["done"] = done
            return True
            
    return False

def retrieve_knowledge(query: str, limit: int = 3) -> str:
    """
    질문(query)과 관련된 지식(문서, 용어)을 Vector DB에서 찾아 텍스트로 반환합니다.
    """
    db = SessionLocal()
    try:
        # 1. 질문을 벡터로 변환 (384차원)
        query_vector = get_embedding(query)
        
        # 2. DB에서 코사인 유사도가 가장 높은 데이터 검색
        results = db.query(KnowledgeBase).order_by(
            KnowledgeBase.embedding.cosine_distance(query_vector)
        ).limit(limit).all()
        
        if not results:
            return "관련된 내부 지식 문서가 없습니다."

        # 3. 검색된 내용을 하나의 문자열로 합침
        context_text = ""
        for idx, res in enumerate(results, 1):
            source_info = f"[{res.category}] {res.source}"
            context_text += f"{idx}. 출처: {source_info}\n   내용: {res.content}\n"
            if res.metadata_info:
                context_text += f"   참고: {res.metadata_info}\n"
            context_text += "\n"
            
        return context_text
        
    except Exception as e:
        print(f"RAG 검색 실패: {e}")
        return "지식 검색 중 오류 발생"
    finally:
        db.close()



def generate_report(machine_id: str, transcripts: dict) -> str:
    checklist = get_checklist(machine_id)
    
    # 점검 완료/미완료 항목 분류
    completed = []
    not_completed = []

    # RAG 검색을 위한 키워드 수집
    search_keywords = [f"{machine_id} 안전 점검"]
    
    for item in checklist:
        idx = item["index"]
        todo = item["todo"]
        key = f"{machine_id}_{idx}"

        print(key)
        
        if key in transcripts and transcripts[key]:
            completed.append(f"{idx}. {todo}: {transcripts[key]}")
        else:
            not_completed.append(f"{idx}. {todo}")
    
    # 2. [RAG] Vector DB 검색 실행
    # 기계 이름과 주요 점검 항목을 합쳐서 DB에 물어봅니다.
    rag_query = " ".join(search_keywords[:3]) # 너무 길면 잘림 방지
    print(f"[RAG] 검색 쿼리: {rag_query}")
    
    retrieved_context = retrieve_knowledge(rag_query, limit=3)
    print(f"[RAG] 검색 결과:\n{retrieved_context}")



    print(transcripts)
    print('--')
    print(completed)
    print(not_completed)
    
    # GPT 프롬프트 구성 - 배터리 공정 전문 보고서
    prompt = f"""당신은 리튬이온 배터리 제조 공정의 안전 점검 전문가입니다. 기계 {machine_id}의 점검 리포트를 작성해주세요.

**배터리 공정 배경 지식:**
- 믹싱기(1): NMP(N-Methyl-2-pyrrolidone) 등 유기용제 사용, 화재/폭발 위험, 유해물질 노출 위험
- 코터(2): 고온 건조로, 롤러 압착, NMP 증발, 기계적 위험 및 화학적 위험 복합
- 슬리터(3): 고속 회전 칼날, 기계적 위험, 정밀 절단 공정

---
### 
아래 내용은 Vector DB에서 검색된 실제 사내 지식입니다. 보고서 작성 시 적극 인용하세요.
{retrieved_context}
---

**실제 점검 데이터:**
"""
    
    if completed:
        prompt += "### 점검 완료 항목 (실제 점검 결과)\n"
        prompt += "\n".join(completed) + "\n\n"
    else:
        prompt += "### 점검 완료 항목\n없음\n\n"
    
    if not_completed:
        prompt += "### 점검 미완료 항목 (아직 점검하지 않음)\n"
        prompt += "\n".join(not_completed) + "\n\n"
    
    prompt += """**중요 지침:** 위에 '점검 완료 항목'에 명시된 내용만 실제로 점검된 것입니다. '점검 미완료 항목'은 아직 점검되지 않았으므로 추측하거나 가정하지 마십시오.

다음 구조로 상세한 A4 1장 분량의 전문 보고서를 작성해주세요:

## 📋 배터리 제조 공정 안전점검 보고서

### 1. 점검 개요
- 점검 대상 설비 및 공정 특성 설명 (2-3문단)
- 해당 공정의 주요 위험 요소 분석 (화학적/기계적/화재 위험 등)
- 점검 완료율과 전체적인 점검 현황

### 2. 점검 결과 상세 분석
**✅ 점검 완료 항목 분석:**
- 각 완료된 점검 항목에 대한 상세한 기술적 해석
- 해당 항목이 안전에 미치는 영향도 분석
- 점검 결과가 양호한 경우와 문제가 있는 경우 구분하여 설명

**⚠️ 점검 미완료 항목 영향 평가:**
- 미완료된 각 항목이 전체 안전성에 미치는 잠재적 위험도
- 해당 항목들의 긴급도 및 우선순위 평가

### 3. 위험도 종합 평가
- 현재 점검된 항목들을 바탕으로 한 설비 안전도 점수 (1-10점)
- 주요 위험 시나리오 및 발생 가능성 분석
- 배터리 공정 특성상 주의해야 할 화학적/물리적 위험 요소들

### 4. 개선 권고사항
- 점검 미완료 항목에 대한 구체적인 점검 일정 제안
- 발견된 문제점에 대한 개선 방안
- 예방 정비 및 추가 안전 조치 권고사항
- 작업자 안전 교육 필요성 검토

### 5. 종합 결론 및 조치사항
- 현재 설비 상태에 대한 전문가 의견 (5-6문장 이상)
- 즉시 조치가 필요한 사항과 중장기 개선 과제 구분
- 다음 점검까지의 안전 운영 가능 여부 판정
- 생산 연속성과 안전성 균형에 대한 권고

**작성 지침:**
- 배터리 제조업 표준 및 산업안전보건법 기준 참조
- 기술적 용어와 전문적 분석 포함
- 구체적인 수치와 명확한 판단 근거 제시
- 실무진이 즉시 활용할 수 있는 구체적 조치사항 포함
- 전체 길이는 A4 1장이 꽉 찰 정도로 상세하게 작성

각 섹션마다 충분한 설명과 분석을 포함하여 전문성 있는 보고서를 작성해주세요."""
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,  # A4 1장 분량을 위해 대폭 증대
            temperature=0.7   # 전문적이면서도 자연스러운 문체를 위해
        )
        return response.choices[0].message.content
    except Exception as e:
        # GPT 실패 시 상세한 기본 보고서
        machine_type = {"1": "믹싱기", "2": "코터", "3": "슬리터"}.get(machine_id, f"기계 {machine_id}")
        
        report = f"""## 📋 배터리 제조 공정 안전점검 보고서

### 1. 점검 개요
**점검 대상:** {machine_type} (설비 ID: {machine_id})
**점검 일시:** 시스템 자동 생성 보고서
**점검 현황:** 총 {len(checklist)}개 항목 중 {len(completed)}개 완료 ({len(completed)/len(checklist)*100:.1f}%)

배터리 제조 공정에서 {machine_type}는 핵심적인 역할을 담당하며, 특히 화학적 위험요소와 기계적 위험요소가 복합적으로 존재하는 설비입니다. 
본 점검은 작업자 안전 확보와 설비 안정성 유지를 목적으로 수행되었습니다.

### 2. 점검 결과 상세 분석\n"""
        
        if completed:
            report += "**✅ 점검 완료 항목 분석:**\n"
            for item in completed:
                report += f"- {item}\n"
            report += f"\n위 {len(completed)}개 항목이 정상적으로 점검 완료되어 해당 부분의 안전성이 확인되었습니다.\n\n"
        else:
            report += "**✅ 점검 완료 항목:**\n점검이 완료된 항목이 없어 현재 설비의 안전 상태를 평가할 수 없습니다.\n\n"
        
        if not_completed:
            report += "**⚠️ 점검 미완료 항목:**\n"
            for item in not_completed:
                report += f"- {item}\n"
            report += f"\n위 {len(not_completed)}개 항목이 아직 점검되지 않아 잠재적 위험 요소가 존재할 수 있습니다.\n\n"
        
        report += f"""### 3. 위험도 종합 평가
**설비 안전도 점수:** {len(completed)*2 if len(completed) <= 5 else 10}/10점
**주요 위험 요소:** 배터리 공정 특성상 유기용제, 고온, 기계적 위험이 복합적으로 존재

### 4. 개선 권고사항
- 미완료 점검 항목에 대한 즉시 점검 실시 필요
- 정기 점검 주기 준수 및 점검 이력 관리 체계화
- 작업자 안전 교육 정기 실시

### 5. 종합 결론 및 조치사항
현재 점검 완료율은 {len(completed)/len(checklist)*100:.1f}%로"""
        
        if len(completed) == len(checklist):
            report += " 모든 항목이 완료되어 설비 운영에 문제가 없는 것으로 판단됩니다. "
            report += "점검 결과를 바탕으로 안전한 운영이 가능하며, 다음 정기 점검까지 현재 상태를 유지하시기 바랍니다."
        elif len(completed) == 0:
            report += " 점검이 전혀 수행되지 않았습니다. "
            report += "설비 운영 전 반드시 전체 점검 항목을 완료하여야 하며, 점검 완료 전까지는 설비 가동을 중단하는 것을 권고합니다."
        else:
            report += f" 부분적으로 완료된 상태입니다. "
            report += f"점검된 {len(completed)}개 항목은 정상으로 확인되었으나, 나머지 {len(not_completed)}개 항목의 점검이 완료되어야 "
            report += "종합적인 안전 상태 평가가 가능합니다. 미완료 항목에 대한 신속한 점검을 통해 안전성을 확보하시기 바랍니다."
        
        return report
