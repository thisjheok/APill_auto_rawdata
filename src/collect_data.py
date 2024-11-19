import requests
import pandas as pd
import math
import time
import os
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

def fetch_all_data(base_url, params, max_retries=3, delay=1):
    all_items = []
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['header']['resultCode'] != "00":
            raise Exception(f"API 응답 에러: {data['header']['resultMsg']}")
        
        body = data['body']
        total_count = body['totalCount']
        num_of_rows = body['numOfRows']
        total_pages = math.ceil(total_count / num_of_rows)
        
        print(f"총 데이터 개수: {total_count}")
        print(f"총 페이지 수: {total_pages}")
        
        for page in tqdm(range(1, total_pages + 1), desc="데이터 수집 중"):
            params['pageNo'] = str(page)
            success = False
            retries = 0
            
            while not success and retries < max_retries:
                try:
                    response = requests.get(base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data['header']['resultCode'] != "00":
                        raise Exception(f"페이지 {page} 응답 에러: {data['header']['resultMsg']}")
                    
                    items = data['body']['items']
                    for item_wrapper in items:
                        all_items.append(item_wrapper['item'])
                    
                    success = True
                    
                except Exception as e:
                    retries += 1
                    print(f"페이지 {page} 요청 중 에러 발생: {e}. 재시도 {retries}/{max_retries}...")
                    time.sleep(delay)
            
            if not success:
                print(f"페이지 {page}를 {max_retries}번 시도했지만 실패했습니다.")
                break
    
    except Exception as e:
        print(f"데이터 수집 중 오류 발생: {str(e)}")
        raise
    
    return all_items

def main():
    # .env 파일 로드
    load_dotenv()
    
    base_url = "http://apis.data.go.kr/1471000/HtfsInfoService03/getHtfsItem01"
    
    # API 키를 .env 파일에서 가져오기
    api_key = os.getenv('API_KEY')
    
    if not api_key:
        raise ValueError("API_KEY가 .env 파일에 설정되지 않았습니다.")
    
    params = {
        'ServiceKey': api_key,
        'pageNo': '1',
        'numOfRows': '100',
        'type': 'json'
    }
    
    print("데이터 수집을 시작합니다...")
    
    try:
        all_data = fetch_all_data(base_url, params)
        print(f"총 수집된 데이터 개수: {len(all_data)}")
        
        if not all_data:
            print("수집된 데이터가 없습니다.")
            return
        
        df = pd.DataFrame(all_data)
        
        fields = [
            "ENTRPS",
            "PRDUCT",
            "STTEMNT_NO",
            "REGIST_DT",
            "DISTB_PD",
            "SUNGSANG",
            "SRV_USE",
            "PRSRV_PD",
            "INTAKE_HINT1",
            "MAIN_FNCTN",
            "BASE_STANDARD"
        ]
        
        # 필드가 모두 있는지 확인하고, 없는 필드는 빈 값으로 채움
        for field in fields:
            if field not in df.columns:
                df[field] = ""
        
        df = df[fields]
        
        current_date = datetime.now().strftime("%Y%m%d")
        excel_file = f"api_data_{current_date}.xlsx"
        
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"데이터가 '{excel_file}' 파일로 저장되었습니다.")
        
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main()