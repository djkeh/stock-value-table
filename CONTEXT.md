# stock-value-table Domain Context

이 프로젝트는 대한민국 상장주식의 핵심 정보를 FnGuide에서 수집하여 사용자에게 테이블 형태로 보기 좋게 정리하여 보여주는 정적 웹서비스입니다.

## 용어 사전 (Glossary)

* **업종 (Sector / Category):** 기업이 속한 산업군 비즈니스 분류 영역 (예: 전기전자, 자동차, 2차전지 등).
* **기업명 (Company Name):** 상장된 기업의 공식 명칭 (한글).
* **종목코드 (Stock Code / gicode):** 한국거래소(KRX)에서 각 상장사에 부여한 6자리 고유 코드 (예: 삼성전자는 `A005930`). FnGuide 요청 파라미터에서는 앞글자 `A`를 포함하여 사용합니다.
* **시가총액 (Market Capitalization):** 보통주 기준의 시가총액. 상장주식수와 현재 주가를 곱한 값입니다.
* **현재가 (Current Price):** 정규장 종가 기준의 현재 주식 가격.
* **영업이익 (Operating Profit):** 기업의 주된 영업활동에서 발생한 이익. 분석 대상 연도(2025~2028년)에 대해 반올림하여 억 원 단위 정수로 가공합니다.
* **PER (Price-to-Earnings Ratio):** 주가수익비율. 주가를 주당순이익(EPS)으로 나눈 값으로, 낮을수록 저평가된 것으로 판단합니다.
* **PBR (Price-to-Book Ratio):** 주가순자산비율. 주가를 주당순자산(BPS)으로 나눈 값으로, 낮을수록 자산 대비 주가가 저평가된 것으로 판단합니다.
* **EPS (Earnings Per Share):** 주당순이익. 지배주주순이익을 수정평균주식수로 나눈 값입니다.
* **FnGuide 컨센서스 내장 JSON (`perforTrend`):** FnGuide 신규 도메인(`wcomp.fnguide.com`)의 컨센서스 페이지 HTML 내 `consensus.init(...)` 스크립트에 포함된 구조화된 JSON 데이터(`header`, `data`)입니다.

## 시스템 아키텍처 및 결정 사항 (Key Decisions)

### FnGuide 데이터 수집 방식

* **결정:** 시세/시가총액은 `https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd={gicode}`에서 파싱하고, 컨센서스 재무 지표는 `https://wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd={gicode}` 응답 HTML에 내장된 `perforTrend` JSON을 추출하여 파싱합니다. 수집 대상 연도는 `perforTrend.header`의 마지막 4개년을 동적으로 선택합니다.
* **트레이드오프:** 구 `comp.fnguide.com/SVO2/json/data/01_06/...` 경로가 폐지(404 에러 페이지 리다이렉트)됨에 따라 신규 `wcomp.fnguide.com` 페이지 내장 JSON을 직접 추출합니다. 향후 페이지 스크립트 구조가 변경되더라도 `perforTrend` 미검출·`/Error/` 리다이렉트 감지 및 연속 5회 실패 조기 중단으로 즉시 장애를 알립니다.

### 대상 종목 목록 관리 방식

* **결정:** 크롤링할 대상 기업 종목코드 목록은 프로젝트 루트에 [target-gicodes.csv](file:///Users/uno/Documents/github/stock-value-table/target-gicodes.csv) 파일로 직접 관리합니다.
* **구조:** 첫 번째 행에 헤더(`업종,기업명,종목코드`)를 포함하고 콤마(`,`) 구분자를 사용하는 단순 CSV 형식으로 정보를 기록하여, 파이썬 스크립트가 손쉽게 읽고 식별할 수 있도록 합니다.
