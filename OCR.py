#!/usr/bin/env python
# coding: utf-8



# PaddlePaddle 설치
#!pip install paddlepaddle

# PaddleOCR 설치
#!pip install paddlepaddle-ocr

# fastapi 설치
#!pip install "fastapi[all]"


from fastapi import FastAPI, UploadFile, File
from PIL import Image
from io import BytesIO
import re
import numpy as np
from paddleocr import PaddleOCR

# OCR 인스턴스 생성
ocr = PaddleOCR(use_angle_cls=True, lang='korean', show_log=False)

# FastAPI 앱 인스턴스
app = FastAPI()

    # 팀명 리스트
team_keywords = ["LG", "두산", "SSG", "NC", "삼성", "KIA", "KT", "한화"]
    
# 날짜 패턴 (YYYY/MM/DD, YYYY-MM-DD, 2025년 3월 27일 등)
date_pattern = r"(\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{4}년\s?\d{1,2}월\s?\d{1,2}일)"


# 좌석 패턴 (~석, ~구역, ~열, ~번이 포함된 부분) -> 이부분 애매함... ㅜㅜ
seat_pattern = r"((\w+루\s?[\w가-힣]*\s?(석|존))|\w+구역|\d+열|\d+번)"
@app.post("/upload_paperTicket")
async def upload_paperTicket(file: UploadFile = File(...)):
    # 파일을 메모리에 로드
    image_bytes = await file.read()

    # 이미지 파일을 BytesIO로 변환하여 PIL 이미지로 처리
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image = np.array(image)
    
    # OCR 수행
    result = ocr.ocr(image, cls=True)

    # 결과에서 텍스트만 리스트로 저장
    extracted_texts = [line[1][0] for line in result[0]]
    ocr_text = " ".join(extracted_texts)  # 여러 줄을 하나의 문자열로 합침
        
    # away_team 찾기 (OCR 텍스트에서 팀명 포함된 부분 찾기)
    away_team_matches = [word for word in extracted_texts if any(team in word for team in team_keywords)]
    away_team = " ".join(away_team_matches) if away_team_matches else ""
    
    # 날짜 찾기 (가장 마지막 번째 날짜만 가져오기)
    date_matches = re.findall(date_pattern, ocr_text)
    ticket_date = date_matches[-1] if date_matches else ""
    
    # 날짜 변환
    if "년" in ticket_date:
        year, month, day = ticket_date.split('년')[0], ticket_date.split('년')[1].split('월')[0], ticket_date.split('월')[1].split('일')[0]
        ticket_date = f"{year}/{month}/{day}"
    elif "/" in ticket_date:
        year, month, day = ticket_date.split('/')
        ticket_date = f"{year}/{month}/{day}"
    elif "-" in ticket_date:
        year, month, day = ticket_date.split('-')
        ticket_date = f"{year}/{month}/{day}"
    else:
        print("날짜가 제대로 추출되지 않았습니다.")  # 날짜 추출 오류 출력
        ticket_date = None
    
    # 좌석 정보 찾기 (좌석 관련 단어 포함된 것 찾기)
    seat_matches = re.findall(seat_pattern, ocr_text)
    
    # 튜플에서 첫 번째 값만 추출하여 결합
    seat = " ".join(match[0] for match in seat_matches if match[0]) if seat_matches else ""
    
    # 누락된 항목 확인
    missing_fields = []
    if not away_team:
        missing_fields.append("팀명을 찾을 수 없습니다.")
    if not ticket_date:
        missing_fields.append("날짜를 찾을 수 없습니다.")
    if not seat:
        missing_fields.append("좌석 정보를 찾을 수 없습니다.")

    # 실패 응답
    if missing_fields:
        return {
            "status": "fail",
            "message": "티켓 정보를 인식하지 못하였습니다.",
            "details": missing_fields
        }

    ticket_info = {
            "away_team": away_team,
            "ticket_date": ticket_date,
            "seat": seat
    }

    # 결과 반환
    return ticket_info
