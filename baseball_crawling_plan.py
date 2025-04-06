#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!pip install beautifulsoup4
#!pip install schedule


# In[25]:





# In[2]:


import mysql.connector
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

# 경기장 매핑
team_to_stadium = {
    "잠실": "서울 잠실야구장",
    "광주": "광주 기아 챔피언스 필드",
    "대구": "대구 삼성 라이온즈 파크",
    "사직": "부산 사직야구장",
    "대전": "대전 한화생명 볼 파크",
    "고척": "서울 고척스카이돔",
    "창원": "창원 NC 파크",
    "문학": "인천 SSG 랜더스필드",
    "수원": "수원 KT 위즈 파크"
}

# MySQL 연결
def connect_to_mysql():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="baseball"
    )
    return conn, conn.cursor()

# 메인 함수
def job():
    conn, cursor = connect_to_mysql()

    # 3일 후 기준 날짜
    today = datetime.today().date()
    url = f"https://statiz.sporki.com/schedule/?m=daily&date={today}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    print(f"==== {today} 경기 정보 ====")

    game_boxes = soup.select("div.item_box")

    for game_box in game_boxes:
        header = game_box.select_one("div.box_head")
        if not header:
            continue

        if "경기취소" in header.text:
            continue

        # 1. 시간 추출 (정규식)
        time_match = re.search(r"\d{2}:\d{2}", header.text)
        if not time_match:
            print(f"[경고] 시간 파싱 실패: {header.text}")
            continue
        time = time_match.group()  # 예: "14:00"

        # 2. 경기장 추출
        try:
            stadium_kor = header.select_one("span:nth-of-type(2)").text.strip("()")
            stadium = team_to_stadium.get(stadium_kor, "팀 매칭안됨")
        except Exception as e:
            print(f"[에러] 경기장 파싱 실패: {e}")
            continue

        # 3. 팀 추출
        try:
            team_rows = game_box.select("tbody tr")
            away_team = team_rows[0].select_one("td").text.strip()
            home_team = team_rows[1].select_one("td").text.strip()
        except Exception as e:
            print(f"[에러] 팀 정보 파싱 실패: {e}")
            continue

        # 4. datetime 결합
        try:
            game_datetime = datetime.strptime(f"{today} {time}", "%Y-%m-%d %H:%M")
        except ValueError:
            print(f"[에러] datetime 변환 실패: {today} {time}")
            continue

        print(f"▶ {away_team} vs {home_team} @ {stadium} - {game_datetime}")

        # 5. DB INSERT
        insert_query = """
        INSERT INTO GameResult (home_team, away_team, game_date, stadium)
        VALUES (%s, %s, %s, %s)
        """
        values = (home_team, away_team, game_datetime, stadium)

        try:
            cursor.execute(insert_query, values)
        except mysql.connector.Error as err:
            print(f"[쿼리 오류] {err}")
            conn.rollback()

    conn.commit()
    cursor.close()
    conn.close()

# 실행
job()


# In[35]:


# 매일 02시에 job 함수 실행
schedule.every().day.at("02:00").do(job)

while True:
    print("실행중..")
    schedule.run_pending()  # 예정된 작업을 확인하고 실행
    time.sleep(60)  # 60초마다 확인

