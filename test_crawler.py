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

    resp = get_with_retry(session, "http://dummy-url.com", {}, timeout=1, max_retries=3, backoff_factor=0.1)
    assert resp.status_code == 200
    assert session.get.call_count == 3


@patch("time.sleep", return_value=None)
def test_get_with_retry_failure(mock_sleep):
    session = MagicMock()
    session.get.side_effect = requests.exceptions.Timeout("Connection timed out")

    with pytest.raises(requests.exceptions.Timeout):
        get_with_retry(session, "http://dummy-url.com", {}, timeout=1, max_retries=3, backoff_factor=0.1)
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
                <tr>
                    <td>종가/ 전일대비/ 수익률</td>
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

    # Mock Consensus JSON Response
    json_data = {
        "comp": [
            {
                "ACCOUNT_NM": "PER",
                "D_4": " 10.5 ", "D_5": " 9.2 ", "D_6": " 8.5 ", "D_7": " 7.8 "
            },
            {
                "ACCOUNT_NM": "PBR",
                "D_4": " 1.2 ", "D_5": " 1.1 ", "D_6": " 1.0 ", "D_7": " 0.9 "
            },
            {
                "ACCOUNT_NM": "EPS",
                "D_4": " 6000 ", "D_5": " 7500 ", "D_6": " 8000 ", "D_7": " 9000 "
            },
            {
                "ACCOUNT_NM": "영업이익(억원)",
                "D_4": " 10,000.5 ", "D_5": " 12,000 ", "D_6": " 14,000 ", "D_7": " 15,000 "
            }
        ]
    }
    mock_resp_json = MagicMock()
    mock_resp_json.status_code = 200
    mock_resp_json.json.return_value = json_data

    session.get.side_effect = [mock_resp_main, mock_resp_json]

    result, err = crawl_stock(session, "005930", fallback_name="삼성전자")
    
    assert err is None
    assert result["gicode"] == "005930"
    assert result["name"] == "테스트전자"
    assert result["current_price"] == "70,000"
    assert result["market_cap"] == "420,000"
    assert result["PER"] == ["10.5", "9.2", "8.5", "7.8"]
    assert result["PBR"] == ["1.2", "1.1", "1.0", "0.9"]
    assert result["EPS"] == ["6000", "7500", "8000", "9000"]
    assert result["영업이익"] == ["10,000", "12,000", "14,000", "15,000"]


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
@patch("crawler.load_existing_stocks", return_value={"005930": {"gicode": "005930", "name": "삼성전자", "current_price": "60,000", "PER": ["1","2","3","4"], "PBR": ["1","2","3","4"], "EPS": ["1","2","3","4"], "영업이익": ["1","2","3","4"]}})
@patch("crawler.crawl_stock")
@patch("time.sleep", return_value=None)
@patch("os.makedirs")
@patch("builtins.open")
def test_main_flow(mock_open, mock_makedirs, mock_sleep, mock_crawl, mock_load, tmp_path):
    # Setup mock CSV contents
    # target-gicodes.csv format: 업종, 기업명, 종목코드
    csv_content = "업종,기업명,종목코드\n반도체,삼성전자,005930\n자동차,현대차,005380\n"
    
    # Mocking open for target-gicodes.csv and saving to stocks.json
    mock_file_csv = MagicMock()
    mock_file_csv.__enter__.return_value = csv_content.splitlines()
    
    mock_file_json = MagicMock()
    
    def open_side_effect(filename, mode="r", encoding=None):
        if filename == "target-gicodes.csv":
            return mock_file_csv
        else:
            return mock_file_json
            
    mock_open.side_effect = open_side_effect
    
    # Simulate: Samsung successfully crawled, Hyundai fails to crawl (should fallback to existing but Hyundai is not in existing, so ignored/logged)
    mock_crawl.side_effect = [
        ({"gicode": "005930", "name": "삼성전자", "current_price": "70,000", "market_cap": "4,200,000", "years": ["2025","2026","2027","2028"], "PER": ["1","2","3","4"], "PBR": ["1","2","3","4"], "EPS": ["1","2","3","4"], "영업이익": ["1","2","3","4"]}, None),
        (None, "HTTP 404")
    ]
    
    with patch("os.path.exists", side_effect=lambda path: path == "target-gicodes.csv"):
        with patch("json.dump") as mock_json_dump:
            with patch("crawler.write_github_summary") as mock_summary:
                main()
                
                # Check JSON dump contains crawled samsung electronic
                mock_json_dump.assert_called_once()
                written_data = mock_json_dump.call_args[0][0]
                assert len(written_data) == 1
                assert written_data[0]["gicode"] == "005930"
                assert written_data[0]["category"] == "반도체"
                
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
