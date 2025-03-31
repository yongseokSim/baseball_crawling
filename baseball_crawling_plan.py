#!/usr/bin/env python
# coding: utf-8

# In[ ]:


#!pip install beautifulsoup4
#!pip install schedule


# In[25]:


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


# In[13]:


import mysql.connector
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import schedule
import time


# In[30]:


# MySQL 연결 설정
def connect_to_mysql():
    conn = mysql.connector.connect(
        host="localhost",       
        user="root",            
        password="1234",        
        database="baseball"     
    )
    return conn, conn.cursor()

def job():
     #MySQL 연결 재확인
    conn, cursor = connect_to_mysql()

    # 당일 날짜 가져오기
    today = (datetime.today() + timedelta(days=1)).date()
    current_day = today.day
    current_year = today.year
    current_month = today.month

    # 날짜에 맞는 URL 가져오기
    url = f"https://statiz.sporki.com/schedule/?year={current_year}&month={current_month}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    print(f"==== {current_month}월 {current_day}일 경기 정보 시작 ====\n")
    
    # 모든 날짜(span class="day") 태그 찾기
    day_elements = soup.find_all("span", class_="day")
    
    for day_element in day_elements:
        game_day = int(day_element.text.strip())
        if game_day == current_day:  # 오늘 날짜와 일치하는 경우
            parent_td = day_element.find_parent("td")
            if parent_td:
                games = parent_td.find_all("li")        
                for game in games:
                    teams = game.find_all("span", class_="team")
                    stadium = game.find("span", class_="stadium")
                    stadium = stadium.text.strip()
                    weather = game.find("span", class_="weather")
                    if weather:
                        print(f"{teams[0].text} vs {teams[1].text} - 우천취소\n")
                        continue
                    # stadium 풀네임으로 변경
                    stadium = team_to_stadium.get(stadium, "팀 매칭안됨")  

                    # 날짜 포맷 변경
                    print(f'팀: {teams[0].text} vs {teams[1].text}, 경기장: {stadium}, 날짜: {today}')


                    # GameResult 데이터 저장
                    game_result_query = """
                    INSERT INTO GameResult (home_team, away_team, game_date, stadium)
                    VALUES (%s, %s, %s, %s)
                    """
                    game_result_values = (teams[1].text, teams[0].text, today, stadium)
                    try:
                        cursor.execute(game_result_query, game_result_values)
                        game_result_id = cursor.lastrowid  # 생성된 game_result_id 가져오기
                    except mysql.connector.Error as err:
                        print(f"쿼리 실행 중 오류: {err}")
                        # 오류가 발생하면 재연결
                        conn, cursor = connect_to_mysql()
                        cursor.execute(game_result_query, game_result_values)
                        game_result_id = cursor.lastrowid

                    # 변경사항 저장
                    conn.commit()

    # 연결 종료
    cursor.close()
    conn.close()

job()


# In[35]:


# 매일 02시에 job 함수 실행
schedule.every().day.at("18:14").do(job)

while True:
    print("실행중..")
    schedule.run_pending()  # 예정된 작업을 확인하고 실행
    time.sleep(60)  # 60초마다 확인

