import os
import json
import pytest
import requests
from unittest.mock import MagicMock, patch
from crawler import (
    clean_and_format_op,
    get_with_retry,
    crawl_stock,
    load_existing_stocks,
    write_github_summary,
    save_crawl_metadata,
    main
)
# -------------------------------------------------------------------------
# 1. clean_and_format_op Tests
# -------------------------------------------------------------------------
def test_clean_and_format_op():
    assert clean_and_format_op("436,010.51") == "436,011"
    assert clean_and_format_op("3,563,998") == "3,563,998"
    assert clean_and_format_op("12.6") == "13"
    assert clean_and_format_op("-12.5") == "-12"
    assert clean_and_format_op("-") == "-"
    assert clean_and_format_op("N/A") == "-"
    assert clean_and_format_op("") == "-"
    assert clean_and_format_op(None) == "-"
    assert clean_and_format_op("invalid_number") == "invalid_number"


# -------------------------------------------------------------------------
# 2. get_with_retry Tests
# -------------------------------------------------------------------------
def test_get_with_retry_success():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    session.get.return_value = mock_resp

    resp = get_with_retry(session, "http://dummy-url.com", {}, timeout=1)
    assert resp.status_code == 200
    assert session.get.call_count == 1


@patch("time.sleep", return_value=None)
def test_get_with_retry_retry_and_success(mock_sleep):
    session = MagicMock()
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 500  # Will trigger raise HTTPError
    
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200

    # Simulate: 1st attempt Timeout, 2nd attempt HTTP 500, 3rd attempt 200 OK
    session.get.side_effect = [
        requests.exceptions.Timeout("Timeout!"),
        mock_resp_fail,
        mock_resp_success
    ]

    resp = get_with_retry(session, "http://dummy-url.com", {}, timeout=1, max_retries=3)
    assert resp.status_code == 200
    assert session.get.call_count == 3


@patch("time.sleep", return_value=None)
def test_get_with_retry_failure(mock_sleep):
    session = MagicMock()
    session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    with pytest.raises(requests.exceptions.Timeout):
        get_with_retry(session, "http://dummy-url.com", {}, timeout=1, max_retries=3)
    assert session.get.call_count == 3


# -------------------------------------------------------------------------
# 3. crawl_stock Tests
# -------------------------------------------------------------------------
def test_crawl_stock_success():
    session = MagicMock()
    
    # Mock Main Page Response
    html_content = """
    <html>
        <body>
            <span id="giName">테스트전자</span>
            <table class="us_table_ty1">
                <tr></tr>
                <tr>
                    <td>종가/ 전일대비/수익률</td>
                    <td>70,000 / +500 / +0.72%</td>
                </tr>
                <tr>
                    <td>시가총액(보통주) 어쩌구</td>
                    <td>420,000</td>
                </tr>
            </table>
        </body>
    </html>
    """
    mock_resp_main = MagicMock()
    mock_resp_main.status_code = 200
    mock_resp_main.content = html_content.encode('utf-8')

    # Mock Consensus Page Response (wcomp.fnguide.com/CompanyInfo/Consensus)
    perfor_trend = {
        "header": [
            {"YYMM": "2023/12", "EP_CHK": " ", "CD": "VAL1"},
            {"YYMM": "2024/12", "EP_CHK": " ", "CD": "VAL2"},
            {"YYMM": "2025/12", "EP_CHK": " ", "CD": "VAL3"},
            {"YYMM": "2026/12", "EP_CHK": "E", "CD": "VAL4"},
            {"YYMM": "2027/12", "EP_CHK": "E", "CD": "VAL5"},
            {"YYMM": "2028/12", "EP_CHK": "E", "CD": "VAL6"},
        ],
        "data": [
            {
                "NAME": "영업이익", "LVL": 1,
                "VAL1": "5000", "VAL2": "8000",
                "VAL3": "10000.5", "VAL4": "12000", "VAL5": "14000", "VAL6": "15000"
            },
            {
                "NAME": "    전년동기대비", "LVL": 2,
                "VAL1": "10.0", "VAL2": "20.0",
                "VAL3": "30.0", "VAL4": "20.0", "VAL5": "16.7", "VAL6": "7.1"
            },
            {
                "NAME": "EPS", "LVL": 1,
                "VAL1": "3000", "VAL2": "4000",
                "VAL3": "6563.57", "VAL4": "7500.00", "VAL5": None, "VAL6": "9000"
            },
            {
                "NAME": "PER", "LVL": 1,
                "VAL1": "15.0", "VAL2": "12.0",
                "VAL3": " 10.5 ", "VAL4": " 9.2 ", "VAL5": " 8.5 ", "VAL6": " 7.8 "
            },
            {
                "NAME": "PBR", "LVL": 1,
                "VAL1": "1.5", "VAL2": "1.3",
                "VAL3": " 1.2 ", "VAL4": " 1.1 ", "VAL5": " 1.0 ", "VAL6": " 0.9 "
            },
        ]
    }
    consensus_html = f"""
    <html>
        <body>
            <script>
                $(document).ready(function () {{
                    consensus.init({{
                        cmp_cd: '005930',
                        perforTrend: {json.dumps(perfor_trend, ensure_ascii=False)},
                        perforTrendChart: {{}}
                    }});
                }});
            </script>
        </body>
    </html>
    """
    mock_resp_consensus = MagicMock()
    mock_resp_consensus.status_code = 200
    mock_resp_consensus.url = "https://wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd=005930"
    mock_resp_consensus.text = consensus_html

    session.get.side_effect = [mock_resp_main, mock_resp_consensus]

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    
    assert err is None
    assert result["gicode"] == "005930"
    assert result["name"] == "테스트전자"
    assert result["current_price"] == "70,000"
    assert result["market_cap"] == "420,000"
    assert result["years"] == ["2025", "2026", "2027", "2028"]
    assert result["PER"] == ["10.5", "9.2", "8.5", "7.8"]
    assert result["PBR"] == ["1.2", "1.1", "1.0", "0.9"]
    assert result["EPS"] == ["6,564", "7,500", "-", "9,000"]
    assert result["영업이익"] == ["10,000", "12,000", "14,000", "15,000"]
    
    # Assert URLs were called with wcomp.fnguide.com and cmp_cd
    first_call_url = session.get.call_args_list[0][0][0]
    second_call_url = session.get.call_args_list[1][0][0]
    assert "wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd=005930" in first_call_url
    assert "wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd=005930" in second_call_url


def test_crawl_stock_fetch_main_fail():
    session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    session.get.return_value = mock_resp

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "Error fetching main page: HTTP 404" in err


# -------------------------------------------------------------------------
# 4. load_existing_stocks Tests
# -------------------------------------------------------------------------
def test_load_existing_stocks_local_file(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    f = d / "stocks.json"
    dummy_data = [
        {"gicode": "005930", "name": "삼성전자", "category": "IT"}
    ]
    f.write_text(json.dumps(dummy_data), encoding="utf-8")

    stocks = load_existing_stocks(filepath=str(f))
    assert "005930" in stocks
    assert stocks["005930"]["name"] == "삼성전자"


@patch.dict(os.environ, {"GITHUB_REPOSITORY": "test-owner/test-repo"})
def test_load_existing_stocks_remote_fallback():
    # If local file is missing, and GITHUB_REPOSITORY is set, it attempts to fetch from remote
    with patch("os.path.exists", return_value=False):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [
                {"gicode": "000660", "name": "SK하이닉스"}
            ]
            mock_get.return_value = mock_resp

            stocks = load_existing_stocks(filepath="non-existent.json")
            
            assert "000660" in stocks
            assert stocks["000660"]["name"] == "SK하이닉스"
            mock_get.assert_called_once_with(
                "https://raw.githubusercontent.com/test-owner/test-repo/gh-pages/data/stocks.json",
                timeout=5
            )


# -------------------------------------------------------------------------
# 5. write_github_summary Tests
# -------------------------------------------------------------------------
def test_write_github_summary(tmp_path):
    summary_file = tmp_path / "summary.md"
    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        failures = [{"name": "에러기업", "gicode": "999999", "error": "HTTP 500"}]
        write_github_summary(5, failures)
        
        content = summary_file.read_text(encoding="utf-8")
        assert "주식 정보 크롤링 리포트" in content
        assert "성공**: 5개" in content
        assert "실패**: 1개" in content
        assert "에러기업" in content


# -------------------------------------------------------------------------
# 6. Main Flow Integration Test (Mocked)
# -------------------------------------------------------------------------
@patch("crawler.load_existing_stocks")
@patch("crawler.crawl_stock")
@patch("time.sleep", return_value=None)
@patch("os.makedirs")
@patch("builtins.open")
def test_main_flow(mock_open, mock_makedirs, mock_sleep, mock_crawl, mock_load):
    # CSV content with:
    # 1. Header (skipped)
    # 2. Samsung (005930) - crawl fails, but exists in cache (recovered)
    # 3. Hyundai (005380) - crawl succeeds (added)
    # 4. Kia (000270) - crawl fails, does not exist in cache (skipped)
    # 5. Malformed/short row - (skipped)
    csv_content = (
        "업종,기업명,종목코드\n"
        "반도체,삼성전자,005930\n"
        "자동차,현대차,005380\n"
        "자동차,기아,000270\n"
        "\n"
    )
    
    mock_file_csv = MagicMock()
    mock_file_csv.__enter__.return_value = csv_content.splitlines()
    
    mock_file_json = MagicMock()
    
    def open_side_effect(filename, mode="r", encoding=None):
        if filename == "target-gicodes.csv":
            return mock_file_csv
        else:
            return mock_file_json
            
    mock_open.side_effect = open_side_effect
    
    # Cache has Samsung electronics data, but not Hyundai or Kia
    mock_load.return_value = {
        "005930": {
            "gicode": "005930",
            "name": "삼성전자",
            "current_price": "60,000",
            "market_cap": "4,000,000",
            "disparity_rate": "1.2",
            "years": ["2025","2026","2027","2028"],
            "PER": ["1","2","3","4"],
            "PBR": ["1","2","3","4"],
            "EPS": ["1","2","3","4"],
            "영업이익": ["1","2","3","4"]
        }
    }
    
    # crawl_stock outcomes:
    # - Samsung: crawl fails
    # - Hyundai: crawl succeeds
    # - Kia: crawl fails
    mock_crawl.side_effect = [
        (None, "Connection error"),
        ({"gicode": "005380", "name": "현대차", "current_price": "200,000", "market_cap": "50,000,000", "disparity_rate": "-100.0", "years": ["2025","2026","2027","2028"], "PER": ["1","2","3","4"], "PBR": ["1","2","3","4"], "EPS": ["1","2","3","4"], "영업이익": ["1","2","3","4"]}, None),
        (None, "HTTP 404")
    ]
    
    with patch("os.path.exists", side_effect=lambda path: path == "target-gicodes.csv"):
        with patch("json.dump") as mock_json_dump:
            with patch("crawler.write_github_summary") as mock_summary:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 2
                
                # Check JSON dump was called for stocks.json and meta.json
                assert mock_json_dump.call_count == 2
                written_data = mock_json_dump.call_args_list[0][0][0]
                written_meta = mock_json_dump.call_args_list[1][0][0]
                assert "last_crawled_at" in written_meta
                assert len(written_data) == 2
                
                samsung_data = next(s for s in written_data if s["gicode"] == "005930")
                assert samsung_data["current_price"] == "60,000"
                assert samsung_data["category"] == "반도체"
                assert samsung_data["disparity_rate"] == "-100.0"
                
                hyundai_data = next(s for s in written_data if s["gicode"] == "005380")
                assert hyundai_data["current_price"] == "200,000"
                assert hyundai_data["category"] == "자동차"
                assert hyundai_data["disparity_rate"] == "-100.0"
                
                mock_summary.assert_called_once()


# -------------------------------------------------------------------------
# 7. Real Network Smoke Test (Samsung Electronics 005930)
# -------------------------------------------------------------------------
@pytest.mark.smoke
def test_crawl_stock_real():
    """
    Smoke Test: Connects to FnGuide to fetch Samsung Electronics (A005930) data.
    Ensures that FnGuide schema hasn't changed and requests are not blocked.
    """
    session = requests.Session()
    # Apply standard headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    })
    
    try:
        stock_info, error = crawl_stock(session, "A005930", fallback_name="삼성전자")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Smoke test failed due to network exception: {e}")
        
    assert error is None, f"Crawl failed with error: {error}"
    assert stock_info is not None, "Crawl result is None"
    
    # Verify exact schema structure
    assert stock_info["gicode"] == "A005930"
    assert "삼성전자" in stock_info["name"]
    
    # Check numeric-like values (PBR, PER, EPS, 영업이익, current_price, market_cap)
    assert stock_info["current_price"] != "-"
    assert stock_info["market_cap"] != "-"
    
    assert len(stock_info["years"]) == 4
    assert len(stock_info["PBR"]) == 4
    assert len(stock_info["PER"]) == 4
    assert len(stock_info["EPS"]) == 4
    assert len(stock_info["영업이익"]) == 4
    
    # Check that years include 2025~2028
    assert stock_info["years"] == ["2025", "2026", "2027", "2028"]
    
    print(f"\n[Smoke Test Success] Samsung electronics data: {stock_info}")


# -------------------------------------------------------------------------
# 8. Error Handling and Main Entry Point Tests
# -------------------------------------------------------------------------
@patch("time.sleep", return_value=None)
def test_crawl_stock_consensus_page_fail(mock_sleep):
    session = MagicMock()
    # Main page OK
    mock_resp_main = MagicMock()
    mock_resp_main.status_code = 200
    mock_resp_main.content = '<html><body><span id="giName">테스트전자</span></body></html>'.encode('utf-8')
    
    # Consensus page returns 404
    mock_resp_consensus = MagicMock()
    mock_resp_consensus.status_code = 404
    
    def get_side_effect(url, **kwargs):
        if "Snapshot" in url or "SVD_Main.asp" in url:
            return mock_resp_main
        else:
            return mock_resp_consensus
            
    session.get.side_effect = get_side_effect
    
    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "Error fetching consensus page: HTTP 404" in err


def test_crawl_stock_consensus_error_redirect():
    session = MagicMock()
    mock_resp_main = MagicMock()
    mock_resp_main.status_code = 200
    mock_resp_main.content = '<html><body><span id="giName">테스트전자</span></body></html>'.encode('utf-8')

    mock_resp_consensus = MagicMock()
    mock_resp_consensus.status_code = 200
    mock_resp_consensus.url = "https://wcomp.fnguide.com/Error/NotFound?404"
    mock_resp_consensus.text = "<html><title>페이지 없음</title></html>"

    session.get.side_effect = [mock_resp_main, mock_resp_consensus]

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "redirected to error" in err


def test_crawl_stock_consensus_missing_perfor_trend():
    session = MagicMock()
    mock_resp_main = MagicMock()
    mock_resp_main.status_code = 200
    mock_resp_main.content = '<html><body><span id="giName">테스트전자</span></body></html>'.encode('utf-8')

    mock_resp_consensus = MagicMock()
    mock_resp_consensus.status_code = 200
    mock_resp_consensus.url = "https://wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd=005930"
    mock_resp_consensus.text = "<html><body>No consensus script</body></html>"

    session.get.side_effect = [mock_resp_main, mock_resp_consensus]

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "perforTrend data not found" in err


def test_crawl_stock_consensus_empty_header():
    session = MagicMock()
    mock_resp_main = MagicMock()
    mock_resp_main.status_code = 200
    mock_resp_main.content = '<html><body><span id="giName">테스트전자</span></body></html>'.encode('utf-8')

    mock_resp_consensus = MagicMock()
    mock_resp_consensus.status_code = 200
    mock_resp_consensus.url = "https://wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd=005930"
    mock_resp_consensus.text = 'consensus.init({ perforTrend: {"header": [], "data": []} });'

    session.get.side_effect = [mock_resp_main, mock_resp_consensus]

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "Empty header" in err


def test_crawl_stock_exception():
    session = MagicMock()
    session.get.side_effect = ValueError("Unexpected exception during crawl")
    
    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    assert result is None
    assert "Unexpected exception during crawl" in err


def test_write_github_summary_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        write_github_summary(5, [])


def test_write_github_summary_all_success(tmp_path):
    summary_file = tmp_path / "summary_success.md"
    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        write_github_summary(5, [])
        content = summary_file.read_text(encoding="utf-8")
        assert "모든 종목이 성공적으로 수집되었습니다." in content
        assert "성공**: 5개" in content
        assert "실패**: 0개" in content


def test_write_github_summary_io_exception(tmp_path):
    summary_file = tmp_path / "summary_error.md"
    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            write_github_summary(5, [])


@patch.dict(os.environ, {}, clear=True)
def test_load_existing_stocks_parse_exception(tmp_path):
    f = tmp_path / "corrupted.json"
    f.write_text("invalid json contents", encoding="utf-8")
    stocks = load_existing_stocks(filepath=str(f))
    assert stocks == {}


@patch.dict(os.environ, {"GITHUB_REPOSITORY": "test-owner/test-repo"})
def test_load_existing_stocks_remote_http_fail():
    with patch("os.path.exists", return_value=False):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_get.return_value = mock_resp
            
            stocks = load_existing_stocks(filepath="non-existent.json")
            assert stocks == {}
            
            mock_get.side_effect = requests.exceptions.ConnectionError("Network down")
            stocks_err = load_existing_stocks(filepath="non-existent.json")
            assert stocks_err == {}


@patch("crawler.load_existing_stocks", return_value={})
@patch("crawler.crawl_stock")
@patch("time.sleep", return_value=None)
@patch("os.makedirs")
@patch("builtins.open")
def test_main_consecutive_failures_abort(mock_open, mock_makedirs, mock_sleep, mock_crawl, mock_load):
    csv_content = (
        "업종,기업명,종목코드\n"
        "업종1,종목1,A000001\n"
        "업종1,종목2,A000002\n"
        "업종1,종목3,A000003\n"
        "업종1,종목4,A000004\n"
        "업종1,종목5,A000005\n"
        "업종1,종목6,A000006\n"
    )
    mock_file_csv = MagicMock()
    mock_file_csv.__enter__.return_value = csv_content.splitlines()
    mock_open.return_value = mock_file_csv
    mock_crawl.return_value = (None, "Consensus page redirected to error")

    with patch("os.path.exists", side_effect=lambda path: path == "target-gicodes.csv"):
        with patch("json.dump") as mock_json_dump:
            with patch("crawler.write_github_summary") as mock_summary:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
                # Aborts after 5 consecutive failures without attempting the 6th stock
                assert mock_crawl.call_count == 5
                # Does not overwrite data/stocks.json on fatal abort
                mock_json_dump.assert_not_called()
                mock_summary.assert_called_once()
                _, kwargs = mock_summary.call_args
                assert kwargs.get("aborted") is True


@patch("crawler.load_existing_stocks", return_value={})
@patch("crawler.crawl_stock")
@patch("time.sleep", return_value=None)
@patch("os.makedirs")
@patch("builtins.open")
def test_main_zero_success_exits_one(mock_open, mock_makedirs, mock_sleep, mock_crawl, mock_load):
    csv_content = (
        "업종,기업명,종목코드\n"
        "업종1,종목1,A000001\n"
        "업종1,종목2,A000002\n"
    )
    mock_file_csv = MagicMock()
    mock_file_csv.__enter__.return_value = csv_content.splitlines()
    mock_open.return_value = mock_file_csv
    mock_crawl.return_value = (None, "HTTP 500")

    with patch("os.path.exists", side_effect=lambda path: path == "target-gicodes.csv"):
        with patch("json.dump") as mock_json_dump:
            with patch("crawler.write_github_summary") as mock_summary:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1
                mock_json_dump.assert_not_called()
                mock_summary.assert_called_once()


@patch("crawler.load_existing_stocks", return_value={})
@patch("crawler.crawl_stock")
@patch("time.sleep", return_value=None)
@patch("os.makedirs")
@patch("builtins.open")
def test_main_all_success_exits_zero(mock_open, mock_makedirs, mock_sleep, mock_crawl, mock_load):
    csv_content = (
        "업종,기업명,종목코드\n"
        "자동차,현대차,005380\n"
    )
    mock_file_csv = MagicMock()
    mock_file_csv.__enter__.return_value = csv_content.splitlines()
    mock_file_json = MagicMock()
    mock_open.side_effect = lambda filename, *args, **kwargs: mock_file_csv if filename == "target-gicodes.csv" else mock_file_json
    mock_crawl.return_value = (
        {
            "gicode": "005380", "name": "현대차", "current_price": "200,000",
            "market_cap": "50,000,000", "years": ["2025", "2026", "2027", "2028"],
            "PER": ["1", "2", "3", "4"], "PBR": ["1", "2", "3", "4"],
            "EPS": ["1", "2", "3", "4"], "영업이익": ["1", "2", "3", "4"]
        },
        None,
    )

    with patch("os.path.exists", side_effect=lambda path: path == "target-gicodes.csv"):
        with patch("json.dump") as mock_json_dump:
            with patch("crawler.write_github_summary") as mock_summary:
                main()
                assert mock_json_dump.call_count == 2
                assert "last_crawled_at" in mock_json_dump.call_args_list[1][0][0]
                mock_summary.assert_called_once()


def test_write_github_summary_aborted(tmp_path):
    summary_file = tmp_path / "summary_aborted.md"
    with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_file)}):
        failures = [{"name": f"종목{i}", "gicode": f"A00000{i}", "error": "Error"} for i in range(1, 6)]
        write_github_summary(0, failures, aborted=True)
        content = summary_file.read_text(encoding="utf-8")
        assert "조기 중단" in content
        assert "실패**: 5개" in content


def test_save_crawl_metadata(tmp_path):
    meta_file = tmp_path / "data" / "meta.json"
    save_crawl_metadata(str(meta_file))
    assert meta_file.exists()
    content = json.loads(meta_file.read_text(encoding="utf-8"))
    assert "last_crawled_at" in content
    assert content["last_crawled_at"].endswith("+09:00")


@patch("crawler.load_existing_stocks", return_value={})
def test_main_csv_missing(mock_load):
    with patch("os.path.exists", return_value=False):
        with patch("builtins.print") as mock_print:
            main()
            mock_print.assert_any_call("Error: target-gicodes.csv not found.")


# The redundant malformed CSV and cache recovery test has been merged into test_main_flow above.


def test_run_as_main():
    import runpy
    # Mock os.path.exists to return False so that main() exits immediately
    # without running the actual crawl loop or making network calls.
    with patch("os.path.exists", return_value=False):
        runpy.run_path("crawler.py", run_name="__main__")

