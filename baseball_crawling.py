#!/usr/bin/env python
# coding: utf-8

# In[49]:


#!pip install beautifulsoup4
#!pip install schedule


# In[45]:


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


# In[ ]:


import mysql.connector
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import schedule
import time


# In[74]:


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
    # MySQL 연결 재확인
    conn, cursor = connect_to_mysql()

    # 하루 전 날짜 가져오기
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    current_day = yesterday.day
    current_year = yesterday.year
    current_month = yesterday.month

    # 날짜에 맞는 URL 가져오기
    url = f"https://statiz.sporki.com/schedule/?year={current_year}&month={current_month}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    print(f"==== {current_month}월 {current_day}일 경기 정보 시작 ====\n")
    
    # 모든 날짜(span class="day") 태그 찾기
    day_elements = soup.find_all("span", class_="day")
    
    for day_element in day_elements:
        game_day = int(day_element.text.strip())
        if game_day == current_day:  # 하루 전 날짜와 일치하는 경우
            parent_td = day_element.find_parent("td")
            if parent_td:
                games = parent_td.find_all("li")        
                for game in games:
                    link = game.find("a")["href"]
                    teams = game.find_all("span", class_="team")
                    scores = game.find_all("span", class_="score")
                    weather = game.find("span", class_="weather")
            
                    if weather:
                        print(f"{teams[0].text} vs {teams[1].text} - 우천취소\n")
                        continue
                    
                    print(f"경기: {teams[0].text} {scores[0].text} - {scores[1].text} {teams[1].text}\n")
    
                    # 경기 상세 페이지 요청
                    base_url = "https://statiz.sporki.com"
                    smry_link = base_url + link
                    response_smry = requests.get(smry_link)
                    smry_soup = BeautifulSoup(response_smry.text, "html.parser")
                            # PitcherStat 데이터
                    PitcherStatData = []
            

                    # 승리투수, 패배투수, 세이브투수 추출
                    win_player = smry_soup.select_one('.win a').text if smry_soup.select_one('.win a') else None
                    lose_player = smry_soup.select_one('.lose a').text if smry_soup.select_one('.lose a') else None
                    save_player = smry_soup.select_one('.save a').text if smry_soup.select_one('.save a') else None
            
                    # 장소 및 날짜 추출
                    game_info = smry_soup.select_one('.score .txt')
                    if game_info:
                        game_info_text = game_info.text.strip()
                        location, date = game_info_text.split(", ")
                    else:
                        location, date = None, None
    
                    # location으로 stadium 추적
                    stadium = team_to_stadium.get(location, "팀 매칭안됨")  

                    # 날짜 포맷 변경
                    date = f"2025-{date}"
                    date = datetime.strptime(date, "%Y-%m-%d")

                    # 승리팀, 패배팀 결정
                    if int(scores[1].text.strip()) > int(scores[0].text.strip()):
                        win_team = teams[1].text  # 홈팀이 승리
                        lose_team = teams[0].text  # 원정팀이 패배
                    else:
                        win_team = teams[0].text  # 원정팀이 승리
                        lose_team = teams[1].text  # 홈팀이 패배

        
                    # GameResult 데이터 저장
                    game_result_query = """
                    INSERT INTO GameResult (home_team, away_team, game_date, stadium, score_home_team, score_away_team)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    game_result_values = (teams[1].text, teams[0].text, date, stadium, scores[1].text, scores[0].text)
                    try:
                        cursor.execute(game_result_query, game_result_values)
                        game_result_id = cursor.lastrowid  # 생성된 game_result_id 가져오기
                    except mysql.connector.Error as err:
                        print(f"쿼리 실행 중 오류: {err}")
                        # 오류가 발생하면 재연결
                        conn, cursor = connect_to_mysql()
                        cursor.execute(game_result_query, game_result_values)
                        game_result_id = cursor.lastrowid

                    # PitcherStat 데이터 저장
                    pitcher_stats_query = """
                    INSERT INTO PitcherStat (game_result_id, name, team, pitcher_type)
                    VALUES (%s, %s, %s, %s)
                    """
                    if win_player:
                        cursor.execute(pitcher_stats_query, (game_result_id, win_player, win_team, "승"))
                    if lose_player:
                        cursor.execute(pitcher_stats_query, (game_result_id, lose_player, lose_team, "패"))
                    if save_player:
                        cursor.execute(pitcher_stats_query, (game_result_id, save_player, win_team, "세"))

                    # LineUp 데이터 저장
                    log_link = smry_link.replace("summary", "gamelogs")
                    response_log = requests.get(log_link)
                    log_soup = BeautifulSoup(response_log.text, "html.parser")
            
                    lineup_boxes = log_soup.find_all("div", class_="box_type_boared")
                    
                    for box in lineup_boxes:
                        box_head_text = box.find("div", class_="box_head").text.strip()
                        if "경기로그" in box_head_text or "경기 추가 정보" in box_head_text:
                            continue
            
                        # 팀 이름 추출
                        team_names = [item.split(',')[0].strip() for item in [team.text for team in box.find_all("div", class_="box_head")]]
            
                        rows = box.select("tbody tr")
            
                        for index, row in enumerate(rows):
                            cols = row.find_all("td")
                            if len(cols) >= 4:
                                batting_order = cols[0].text.strip()
                                player_name = cols[1].text.strip()
                                position = cols[2].text.strip()
                                hand = cols[3].text.strip()
                                team = team_names[0] if index < 10 else team_names[1]
                                # 'P' 값 확인 후 정수로 변환
                                if batting_order == 'P':  # 'P'가 있을 경우 처리
                                    batting_order = 0  # 적절한 값으로 설정 (예: 0, 또는 다른 숫자)
                                # LineUp 테이블에 데이터 삽입
                                lineup_query = """
                                INSERT INTO LineUp (game_result_id, name, team, `order`, position)
                                VALUES (%s, %s, %s, %s, %s)
                                """
                                cursor.execute(lineup_query, (game_result_id, player_name, team, batting_order, position))

                    # 변경사항 저장
                    conn.commit()

    # 연결 종료
    cursor.close()
    conn.close()

job()


# In[55]:


# 매일 00시에 job 함수 실행
schedule.every().day.at("00:03").do(job)

while True:
    print("실행중..")
    schedule.run_pending()  # 예정된 작업을 확인하고 실행
    time.sleep(60)  # 60초마다 확인

