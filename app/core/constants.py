# 챌린지 풀 (모든 대륙에서 공통 사용)
CHALLENGE_POOL = {
    'basic': [
        "산책하면서 예쁜 사진 찍고 사진 설명 작성",
        "스스로 칭찬할 점 한 가지 작성",
        "내일 나의 마음가짐 작성",
        "오늘 있었던 좋은 일 한 가지 작성",
        "추후 추가 예정"
    ],
    'book': [
        "읽고 감상평 작성",
        "마음에 드는 구절 작성",
        "다른 궁금한 책 작성"
    ],
    'music': [
        "듣고 감상평 작성",
        "마음에 드는 가사 작성",
        "함께 들은 다른 노래 작성"
    ],
    'food': [
        "내가 좋아하는 음식 작성",
        "최근에 맛있게 먹은 음식 작성",
        "먹고싶은 음식 작성"
    ]
}

# 대륙 정보 (continent_id, continent_name, display_order)
CONTINENTS = [
    (1, "아시아", 1),
    (2, "유럽", 2),
    (3, "아프리카", 3),
    (4, "북아메리카", 4),
    (5, "남아메리카", 5),
    (6, "오세아니아", 6)
]

# 챌린지 설정
MAX_BASIC_CHALLENGES_PER_CONTINENT = 5  # 대륙당 기본 챌린지 최대 횟수
CHALLENGES_PER_CONTINENT = 10  # 대륙당 총 챌린지 수
TOTAL_CONTINENTS = 6  # 총 대륙 수
RESET_DAYS = 90  # 챌린지 리셋 기간 (3개월)
MILEAGE_MIN = 50  # 마일리지 최소 금액
MILEAGE_MAX = 100  # 마일리지 최대 금액
CHALLENGES_FOR_MILEAGE = 5  # 마일리지 지급 기준 (5개 완료마다)
