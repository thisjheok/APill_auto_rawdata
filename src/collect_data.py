import requests
import pandas as pd
import math
import time
import os
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv
import json

def fetch_all_data(base_url, params, max_retries=3, delay=1):
    all_items = []
    
    try:
        response = requests.get(base_url, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Raw Response Content: {response.text[:1000]}")
        
        if response.status_code != 200:
            raise Exception(f"API 응답 실패: Status Code {response.status_code}")
            
        if not response.text:
            raise Exception("API 응답이 비어있습니다")
            
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 에러: {str(e)}")
            print(f"응답 내용: {response.text}")
            raise
        
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

def clean_text(text):
    """Excel에 저장 가능한 형태로 텍스트 정제"""
    if not isinstance(text, str):
        return text
    
    # 줄바꿈 문자를 공백으로 변경
    text = text.replace('\n', ' ')
    # 탭 문자를 공백으로 변경
    text = text.replace('\t', ' ')
    # 연속된 공백을 하나의 공백으로 변경
    text = ' '.join(text.split())
    # 텍스트 길이 제한 (예: 32,767자)
    text = text[:32000] if len(text) > 32000 else text
    
    return text

def main():
    load_dotenv()
    
    base_url = "http://apis.data.go.kr/1471000/HtfsInfoService03/getHtfsItem01"
    api_key = str(os.getenv('API_KEY')).strip()
    
    if not api_key:
        raise ValueError("API_KEY가 .env 파일에 설정되지 않았습니다.")
    
    masked_key = api_key[:4] + "*" * (len(api_key)-8) + api_key[-4:]
    print(f"Using API key: {masked_key}")
    
    params = {
        'serviceKey': api_key,
        'pageNo': '1',
        'numOfRows': '100',
        'type': 'json'
    }
    
    full_url = requests.Request('GET', base_url, params=params).prepare().url
    print(f"Full URL: {full_url}")
    
    print("데이터 수집을 시작합니다...")
    
    try:
        all_data = fetch_all_data(base_url, params)
        print(f"총 수집된 데이터 개수: {len(all_data)}")
        
        if not all_data:
            print("수집된 데이터가 없습니다.")
            return
        
        # 데이터프레임 생성
        df = pd.DataFrame(all_data)
        
        # 모든 컬럼의 데이터 정제
        for column in df.columns:
            df[column] = df[column].apply(clean_text)
        
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
        
        for field in fields:
            if field not in df.columns:
                df[field] = ""
        
        df = df[fields]
        
        current_date = datetime.now().strftime("%Y%m%d")
        excel_file = f"api_data_{current_date}.xlsx"
        
        # Excel 파일로 저장
        df.to_excel(excel_file, index=False, engine='openpyxl')
        print(f"데이터가 '{excel_file}' 파일로 저장되었습니다.")
        
    except Exception as e:
        print(f"프로그램 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main()