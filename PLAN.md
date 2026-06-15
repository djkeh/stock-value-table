# 대한민국 상장주식 FnGuide 크롤링 및 데이터 시각화 웹서비스 구축 계획

대한민국 상장주식의 주요 시세 및 컨센서스 재무제표 정보를 FnGuide에서 수집하고, GitHub Pages에 정적 웹서비스로 배포하여 테이블 형태로 시각화하는 시스템을 구축합니다. GitHub Actions의 스케줄러(평일 오후 4시 30분 KST)를 통해 매일 데이터를 자동으로 갱신합니다.

## User Review Required

> [!IMPORTANT]
> **크롤링 대상 종목 관리 방식:**
> 크롤링할 대상 기업 종목코드는 프로젝트 루트에 있는 [target-gicodes.csv](file:///Users/uno/Documents/github/stock-value-table/target-gicodes.csv) 파일의 헤더 아래에 `종목명,종목코드` 목록으로 기재됩니다. 새로운 분석 대상을 추가하거나 변경하려면 이 CSV 파일을 수정하면 됩니다.
>
> **유저 입력 제한 및 정렬 제약:**
> 사용자의 의도에 따라 프런트엔드에는 별도의 검색창이나 필터링 수단(텍스트 입력창 등)이 포함되지 않습니다. 
> 정렬 기능은 `종목명` 헤더 클릭 시에만 가나다/알파벳 순(오름차순/내림차순)으로 우선 적용됩니다.

> [!TIP]
> **다크/라이트 모드 지원 및 FOUC 방지:**
> 시스템 설정(OS 테마)을 자동 반영하며 사용자가 토글 스위치로 다크/라이트 모드를 직접 설정하고 기억할 수 있는 방식을 제공합니다. 페이지 최초 로딩 시 화면이 번쩍거리는 현상(FOUC)을 방지하기 위해 헤드 영역에 가벼운 테마 초기화 인라인 스크립트를 포함합니다.

## Proposed Changes

### 백엔드 (크롤러 및 데이터 스토어)

**[NEW] [crawler.py](file:///Users/uno/Documents/github/stock-value-table/crawler.py)**

* **목록 파싱:** 프로젝트 루트의 [target-gicodes.csv](file:///Users/uno/Documents/github/stock-value-table/target-gicodes.csv)를 읽어와 종목 리스트를 파싱합니다.
* **기본 정보 수집:** 각 종목에 대해 FnGuide의 메인 페이지(`SVD_Main.asp`)를 파싱하여 `종목명`, `시가총액`, `현재가`를 크롤링합니다.
* **상세 지표 수집:** FnGuide 내부 JSON API(`01_06/01_{gicode}_A_D.json`)를 연계 호출하여 2025~2028년의 PBR, PER, EPS, 영업이익 데이터를 수집합니다.
* **데이터 저장:** 수집된 원본 수치 데이터를 정제(영업이익은 정수 반올림 가공)한 뒤 `data/stocks.json` 파일에 저장합니다.

**[NEW] [requirements.txt](file:///Users/uno/Documents/github/stock-value-table/requirements.txt)**

* **패키지 명시:** `requests`, `beautifulsoup4`, `lxml` 등 프로젝트 구동에 필요한 파이썬 라이브러리 목록을 명시하여 GitHub Actions의 파이썬 캐시(`cache: 'pip'`) 매칭 및 패키지 설치에 사용합니다.


### 프런트엔드 (웹 클라이언트)

**[NEW] [index.html](file:///Users/uno/Documents/github/stock-value-table/index.html)**

* **기본 마크업:** 웹 서비스 레이아웃을 선언하는 정적 HTML5 문서입니다.
* **웹 폰트 적용:** 시인성이 좋고 세련된 폰트(Inter 및 Outfit)를 Google Fonts로부터 호출합니다.
* **테마 초기화 스크립트:** 다크모드 Flash of Unstyled Content (FOUC) 방지를 위한 `<meta name="color-scheme" content="light dark">` 설정 및 인라인 테마 로딩 스크립트를 주입합니다.
* **DOM 구조:** 주식 목록을 보여줄 메인 테이블 구조 및 다크모드 토글 스위치 UI를 구축합니다.

**[NEW] [index.css](file:///Users/uno/Documents/github/stock-value-table/index.css)**

* **디자인 시스템:** 디자인 시스템을 바탕으로 현대적인 프리미엄 스타일(Glassmorphism, 부드러운 그래디언트 배경)을 정의합니다.
* **아코디언 애니메이션:** 테이블 행 클릭 시 아코디언 형태로 4개년 상세 카드가 펼쳐지는 애니메이션을 현대적 CSS 방식(`grid-template-rows: 0fr -> 1fr` 트랜지션)으로 구현합니다.
* **테마 스타일링:** 다크/라이트 모드에 대응하는 색상 체계(Variables)를 선언하고 미디어 쿼리 및 `localStorage` 핀 동작에 호환되도록 스타일링합니다.
* **반응형 웹:** 모바일 기기에서도 화면이 무너지지 않도록 반응형 테이블 및 레이아웃을 작성합니다.

**[NEW] [app.js](file:///Users/uno/Documents/github/stock-value-table/app.js)**

* **데이터 연동:** `data/stocks.json`을 가져와서(fetch) 동적으로 테이블 행을 그립니다.
* **행 클릭 이벤트:** 행 클릭 이벤트 발생 시 상세 정보 패널을 슬라이딩 효과와 함께 표시하는 아코디언 동작을 구현합니다.
* **가나다 정렬:** `종목명` 열의 정렬 버튼 클릭 시 오름차순/내림차순 정렬 로직을 수행합니다.
* **테마 제어:** 다크/라이트 모드 수동 토글 감지 및 `localStorage` 저장 기능을 관리합니다.

### 배포 및 자동화 (CI/CD)

**[NEW] [.github/workflows/deploy.yml](file:///Users/uno/Documents/github/stock-value-table/.github/workflows/deploy.yml)**

* **실행 트리거:** 매 평일 오후 4시 30분 KST (cron: `30 7 * * 1-5`) 및 `main` 브랜치에 코드가 push될 때 구동되는 GitHub Actions 워크플로 파일입니다.
* **Node.js 24 환경 대응:** 2026년 기준 깃헙 액션의 Node.js 20 지원이 종료(Deprecation)됨에 따라, `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` 환경변수를 설정하여 모든 자바스크립트 기반 액션들이 안정적인 Node.js 24 환경 위에서 실행되도록 구성합니다.
* **의존성 설치:** 파이썬 가상환경을 구축하고 `requests`, `beautifulsoup4`, `lxml` 패키지를 설치합니다.
* **수집 태스크:** `crawler.py` 스크립트를 구동하여 최신 데이터를 수집해 `data/stocks.json`을 새로 생성/갱신합니다.
* **자동 배포:** 수집된 데이터와 정적 파일(`index.html`, `index.css`, `app.js`)들을 결합하여 GitHub Pages(`gh-pages` 브랜치)로 자동 빌드 및 배포합니다.

## Verification Plan

### Automated Tests

* **크롤러 로직 검증:** 로컬 환경에서 가상환경 파이썬을 실행하여 `crawler.py`가 정상 작동하는지 확인하고, 생성된 `data/stocks.json`이 유효한 JSON 형식인지 체크합니다.
  ```bash
  /Users/uno/Documents/github/stock-value-table/.venv/bin/python crawler.py
  node -e "JSON.parse(require('fs').readFileSync('data/stocks.json'))"
  ```

### Manual Verification

* **테마 동작 검증:** 브라우저 개발자 도구의 강제 다크/라이트 모드 모방 기능 및 토글 버튼을 활용하여 컬러 테마가 알맞게 변하는지 확인합니다.
* **아코디언 동작 검증:** 테이블의 종목을 눌렀을 때 4개년(2025~2028년) 실적 데이터 패널이 부드럽게 펼쳐지는지 검증합니다.
* **정렬 검증:** `종목명` 정렬 작동 시 가나다/알파벳 순으로 정상 정렬 및 재배치가 일어나는지 확인합니다.
* **모바일 반응형 검증:** 브라우저 모바일 시뮬레이터로 화면 폭을 극단적으로 줄였을 때(320px 수준) 레이아웃이 무너지지 않고 정상 표기되는지 테스트합니다.
