# stock-value-table

> 대한민국 상장주식의 주요 시세 및 4개년 컨센서스 재무 지표를 FnGuide에서 자동 수집하여 시각화하는 정적 웹서비스

## Features

* **FnGuide 데이터 크롤링:** 파이썬 스크립트를 통해 메인 시세(종가, 시가총액) 및 4개년(2025~2028) 재무 지표(영업이익, EPS, PER, PBR) 수집
* **자동 업데이트 스케줄러:** GitHub Actions 워크플로를 이용해 평일 오후 4시 30분(KST)마다 데이터를 자동 갱신하고 GitHub Pages로 자동 배포
* **프리미엄 UI 대시보드:** 글래스모피즘(Glassmorphism) 스타일 기반의 아름다운 카드 및 아코디언 행 확장형 테이블 디자인 적용
* **다크/라이트 테마:** OS 시스템 테마를 자동으로 감지하며 사용자 수동 토글 및 설정 기억 기능 제공
* **반응형 웹 디자인:** 모바일 기기(가로폭 600px 미만)에서는 카드가 1열 배치로 자동 변환되어 가독성 확보

## Prerequisites

* Python 3.12 이상
* Node.js 20 이상 (테스트 실행 및 커버리지 측정용)
* Web Browser (Chrome, Safari, Firefox, Edge 등)

## Installation

1. 저장소를 클론합니다.
   ```bash
   git clone https://github.com/djkeh/stock-value-table.git
   cd stock-value-table
   ```

2. 파이썬 가상환경을 생성하고 활성화합니다.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. 필요한 종속성 패키지를 설치합니다.
    ```bash
    # 크롤러용 기본 의존성 설치
    pip install -r requirements.txt
    
    # 크롤러 테스트 및 커버리지 측정용 추가 의존성 설치
    pip install pytest pytest-mock pytest-cov
    ```

4. 프런트엔드 테스트용 패키지를 설치합니다.
    ```bash
    npm install
    ```

## Usage

### 1. 데이터 크롤링 실행
로컬 환경에서 크롤링 스크립트를 구동하여 [data/stocks.json](file:///Users/uno/Documents/github/stock-value-table/data/stocks.json) 파일을 갱신합니다.
```bash
python crawler.py
```

### 2. 웹 서버 구동
로컬 로드 및 동작 검증을 위해 가벼운 웹 서버를 띄워 확인합니다.
```bash
python3 -m http.server 8000
```
웹 브라우저에서 `http://localhost:8000` 주소로 접속합니다.

### 3. 테스트 및 커버리지 실행

#### Python 크롤러 테스트
단위 테스트 및 FnGuide 실 서비스 접근 Smoke 테스트를 실행합니다.
```bash
# 전체 테스트 실행
.venv/bin/pytest test_crawler.py -v

# 커버리지 측정 (100% 도달 파일은 제외하고 요약만 터미널에 컴팩트하게 출력)
.venv/bin/pytest --cov=crawler test_crawler.py --cov-report=json --cov-report=term:skip-covered
```

#### Frontend UI 테스트
가상 DOM(JSDOM) 격리 환경 하에 테이블 렌더링, 아코디언 토글, 다국어 정렬, 테마 전환 동작을 검증합니다.
```bash
# 전체 테스트 실행
npm run test

# 커버리지 측정 (터미널에는 최소 요약만 출력, html 리포트는 coverage/ 폴더에 빌드)
npm run test:coverage
```

## Configuration

* **[target-gicodes.csv](file:///Users/uno/Documents/github/stock-value-table/target-gicodes.csv):** 
  크롤러가 수집할 상장기업 목록 정의 파일입니다. 첫 행에 헤더(`종목명,종목코드`)를 포함한 뒤 쉼표로 종목명과 종목코드를 나열합니다. 새로운 수집 대상을 추가하려면 이 파일의 하단에 행을 추가하면 됩니다.
  ```csv
  종목명,종목코드
  삼성전자,A005930
  sk하이닉스,A000660
  ...
  ```

## Project Structure

```text
stock-value-table/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 자동 수집, 테스트 & 배포 파이프라인
├── data/
│   └── stocks.json             # 크롤러가 생성하는 재무 데이터 파일
├── target-gicodes.csv          # 크롤링 대상 종목 목록 설정 파일
├── crawler.py                  # FnGuide 크롤러 스크립트 (Python)
├── test_crawler.py             # 크롤러 단위 테스트 및 Smoke 테스트 (Python)
├── requirements.txt            # 파이썬 의존성 패키지 정의 파일
├── package.json                # Node.js 프로젝트 설정 및 테스트 의존성 파일
├── vitest.config.js            # Vitest 및 커버리지 보고서 설정 파일
├── app.js                      # 프런트엔드 데이터 렌더링 및 인터랙션 로직
├── app.test.js                 # 프런트엔드 UI/DOM 및 정렬/테마 테스트 스크립트
├── index.html                  # 메인 웹 문서
└── index.css                   # 스타일시트 (테마 및 애니메이션)
```
