# 펫케어 시스템

반려동물 관리 웹 애플리케이션

## 실행 방법

1. PostgreSQL에 데이터베이스 생성 후 init_database.sql 실행
2. app.py의 DB_CONFIG 수정 (host, port, password 등)
3. 실행:
```
pip install -r requirements.txt
python app.py
```
4. 브라우저에서 http://localhost:5000 접속

## 테스트 계정

- owner1@test.com / password123 (반려인)
- vet1@test.com / password123 (수의사)
- sitter1@test.com / password123 (펫시터)
- shop1@test.com / password123 (펫샵)

## 주요 기능

- 회원가입/로그인 (역할별: 반려인, 수의사, 펫시터, 펫샵)
- 반려동물 등록/관리
- 수의사 예약
- 펫시터 예약
- 상품 주문
- 진료 기록 작성
