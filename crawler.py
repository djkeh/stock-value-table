import os
import re
import sys
import csv
import json
import time
import random
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}
MAX_CONSECUTIVE_FAILURES = 5

def clean_and_format_op(val_str):
    """
    Cleans a number string (e.g. '436,010.51' or '3,563,998') 
    by removing commas, rounding to the nearest integer, 
    and formatting back with commas.
    """
    if not val_str:
        return "-"
    val_str = val_str.strip()
    if val_str == "" or val_str == "-" or val_str == "N/A":
        return "-"
    try:
        val_clean = val_str.replace(',', '')
        val_float = float(val_clean)
        val_rounded = round(val_float)
        return f"{val_rounded:,}"
    except ValueError:
        return val_str

def get_with_retry(session, url, headers, timeout=5, max_retries=3, backoff_factor=2):
    """
    Performs a GET request with retry logic for connection/timeout issues
    and transient HTTP errors using a requests.Session.
    """
    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=headers, timeout=timeout)
            if resp.status_code in [500, 502, 503, 504]:
                raise requests.exceptions.HTTPError(f"Status {resp.status_code}")
            return resp
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            if attempt == max_retries - 1:
                raise e
            sleep_time = backoff_factor ** attempt
            print(f"      [Retry] Connection failed ({e}). Retrying in {sleep_time}s... ({attempt + 1}/{max_retries})")
            time.sleep(sleep_time)

def extract_perfor_trend(html_text):
    """
    Extracts the embedded `perforTrend` JSON object from FnGuide Consensus HTML.
    """
    match = re.search(r'perforTrend\s*:\s*\{', html_text)
    if not match:
        raise ValueError("perforTrend data not found in consensus page")
    start_idx = match.end() - 1
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(html_text, start_idx)
    return data

def crawl_stock(session, gicode, fallback_name=""):
    try:
        # 1. Fetch and Parse Main Page
        main_url = f"https://wcomp.fnguide.com/CompanyInfo/Snapshot?cmp_cd={gicode}"
        resp_main = get_with_retry(session, main_url, headers=headers, timeout=5)
        if resp_main.status_code != 200:
            print(f"[{gicode}] Error fetching main page: {resp_main.status_code}")
            return None, f"Error fetching main page: HTTP {resp_main.status_code}"
        
        soup_main = BeautifulSoup(resp_main.content, 'lxml')
        
        # - giName
        gi_name_el = soup_main.find(id='giName')
        gi_name = gi_name_el.text.strip() if gi_name_el else fallback_name
        
        # - 시가총액 and 현재가 from 시세현황 table
        table_sise = soup_main.find('table', class_='us_table_ty1')
        market_cap = "-"
        current_price = "-"
        
        if table_sise:
            for row in table_sise.find_all('tr'):
                cells = [cell.text.strip() for cell in row.find_all(['th', 'td'])]
                if not cells:
                    continue
                
                # Extract 시가총액 (보통주)
                for i, cell in enumerate(cells):
                    if cell.startswith("시가총액(보통주)"):
                        if i + 1 < len(cells):
                            market_cap = cells[i+1].strip()
                
                # Extract 현재가 (종가 from Row 0)
                if cells[0].startswith("종가/ 전일대비"):
                    val = cells[1]
                    current_price = val.split('/')[0].strip()
 
        # 2. Fetch and Parse Consensus Page (embedded perforTrend JSON)
        consensus_url = f"https://wcomp.fnguide.com/CompanyInfo/Consensus?cmp_cd={gicode}"
        resp_consensus = get_with_retry(session, consensus_url, headers=headers, timeout=5)
        if resp_consensus.status_code != 200:
            print(f"[{gicode}] Error fetching consensus page: {resp_consensus.status_code}")
            return None, f"Error fetching consensus page: HTTP {resp_consensus.status_code}"
        if isinstance(getattr(resp_consensus, "url", None), str) and "/Error/" in resp_consensus.url:
            print(f"[{gicode}] Consensus page redirected to error: {resp_consensus.url}")
            return None, f"Consensus page redirected to error: {resp_consensus.url}"

        perfor_trend = extract_perfor_trend(resp_consensus.text)
        header = perfor_trend.get("header") or []
        target_headers = header[-4:]
        if not target_headers:
            return None, "Empty header in consensus perforTrend"

        years = [str(h.get("YYMM", "")).split("/")[0] for h in target_headers]
        target_keys = [h.get("CD", "") for h in target_headers]
        n_years = len(target_keys)
        
        pbr_list = ["-"] * n_years
        per_list = ["-"] * n_years
        eps_list = ["-"] * n_years
        op_list = ["-"] * n_years
        
        def extract_clean_values(row):
            values = []
            for k in target_keys:
                raw = row.get(k)
                cleaned = raw.strip() if isinstance(raw, str) else ""
                values.append(cleaned if cleaned else "-")
            return values

        for item in perfor_trend.get("data") or []:
            if item.get("LVL") not in (None, 1):
                continue
            account_nm = (item.get("NAME") or "").strip()
            
            if account_nm == "PBR":
                pbr_list = extract_clean_values(item)
            elif account_nm == "PER":
                per_list = extract_clean_values(item)
            elif account_nm == "EPS":
                eps_list = [clean_and_format_op(val) for val in extract_clean_values(item)]
            elif account_nm == "영업이익":
                op_list = [clean_and_format_op(val) for val in extract_clean_values(item)]
        
        return {
            "gicode": gicode,
            "name": gi_name,
            "current_price": current_price,
            "market_cap": market_cap,
            "years": years,
            "PBR": pbr_list,
            "PER": per_list,
            "EPS": eps_list,
            "영업이익": op_list
        }, None
    except Exception as e:
        print(f"Error crawling {gicode}: {e}")
        return None, str(e)

def write_github_summary(successful_count, failures, aborted=False):
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_file:
        return
    
    total = successful_count + len(failures)
    
    lines = []
    lines.append("# 📈 주식 정보 크롤링 리포트 (Stock Crawl Report)")
    lines.append("")
    
    if failures:
        if aborted:
            lines.append("> [!CAUTION]")
            lines.append(f"> **연속 실패로 인해 크롤링이 조기 중단되었습니다.** ({len(failures)}개 종목 실패)")
        else:
            lines.append("> [!WARNING]")
            lines.append(f"> **일부 종목 수집 중 에러가 발생했습니다.** ({len(failures)}개 종목 실패)")
        lines.append("")
        lines.append("### 📊 수집 현황 (Crawl Status)")
        lines.append(f"- **전체 종목**: {total}개")
        lines.append(f"- **성공**: {successful_count}개")
        lines.append(f"- **실패**: {len(failures)}개")
        lines.append("")
        lines.append("### ❌ 실패 상세 정보 (Failure Details)")
        lines.append("| 종목명 | 종목코드 | 에러 원인 |")
        lines.append("| :--- | :--- | :--- |")
        for f in failures:
            lines.append(f"| {f['name']} | `{f['gicode']}` | {f['error']} |")
    else:
        lines.append("> [!NOTE]")
        lines.append("> **모든 종목이 성공적으로 수집되었습니다.**")
        lines.append("")
        lines.append("### 📊 수집 현황 (Crawl Status)")
        lines.append(f"- **전체 종목**: {total}개")
        lines.append(f"- **성공**: {successful_count}개")
        lines.append(f"- **실패**: {len(failures)}개")
        
    try:
        with open(summary_file, 'a', encoding='utf-8') as sf:
            sf.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"Error writing to GITHUB_STEP_SUMMARY: {e}")

def load_existing_stocks(filepath="data/stocks.json"):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {item["gicode"]: item for item in data if "gicode" in item}
        except Exception as e:
            print(f"Warning: Failed to load existing stocks from {filepath}: {e}")
            
    # If local file is not found (like in a clean GitHub Actions runner),
    # attempt to fetch the last deployed data from the gh-pages branch.
    repo = os.environ.get('GITHUB_REPOSITORY')
    if repo:
        remote_url = f"https://raw.githubusercontent.com/{repo}/gh-pages/data/stocks.json"
        print(f"Attempting to fetch previous stocks.json from: {remote_url}")
        try:
            resp = requests.get(remote_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                print("Successfully fetched previous stocks data from gh-pages branch.")
                return {item["gicode"]: item for item in data if "gicode" in item}
            else:
                print(f"Notice: Could not fetch remote stocks.json (HTTP {resp.status_code})")
        except Exception as e:
            print(f"Warning: Failed to fetch remote stocks.json: {e}")
            
    return {}

def save_crawl_metadata(filepath="data/meta.json"):
    kst = timezone(timedelta(hours=9))
    metadata = {
        "last_crawled_at": datetime.now(kst).isoformat(timespec="seconds")
    }
    parent_dir = os.path.dirname(filepath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

def main():
    csv_path = "target-gicodes.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return
        
    stocks_path = "data/stocks.json"
    existing_stocks = load_existing_stocks(stocks_path)
    
    stocks_data = []
    failures = []
    successful_crawl_count = 0
    consecutive_failures = 0
    aborted = False
    
    with requests.Session() as session:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # Skip header
            for row in reader:
                if not row or len(row) < 3:
                    continue
                category, name, gicode = row[0].strip(), row[1].strip(), row[2].strip()
                print(f"Crawling {name} ({gicode}) in category {category}...")
                stock_info, error = crawl_stock(session, gicode, fallback_name=name)
                if stock_info:
                    stock_info["category"] = category
                    stocks_data.append(stock_info)
                    successful_crawl_count += 1
                    consecutive_failures = 0
                    print(f"Successfully crawled {name}.")
                else:
                    failures.append({
                        "name": name,
                        "gicode": gicode,
                        "error": error
                    })
                    consecutive_failures += 1
                    # If crawling fails, try to preserve existing data for this stock
                    if gicode in existing_stocks:
                        saved_info = existing_stocks[gicode]
                        saved_info["category"] = category
                        stocks_data.append(saved_info)
                        print(f"Failed to crawl {name}: {error}. Retained existing cached data.")
                    else:
                        print(f"Failed to crawl {name}: {error}. No existing cached data available.")
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        print(f"Aborting crawl: {consecutive_failures} consecutive failures reached.")
                        aborted = True
                        break
                # Sleep 2~3 seconds randomly between requests to respect the server and prevent timeouts/blocking
                time.sleep(random.uniform(2.0, 3.0))

    if aborted or successful_crawl_count == 0:
        write_github_summary(successful_crawl_count, failures, aborted=aborted)
        sys.exit(1)

    # Recalculate derived metrics (like disparity_rate)
    from recalculate import recalculate_data
    recalculate_data(stocks_data)

    # Save output to data/stocks.json and crawl metadata to data/meta.json
    os.makedirs("data", exist_ok=True)
    with open(stocks_path, "w", encoding="utf-8") as f:
        json.dump(stocks_data, f, ensure_ascii=False, indent=2)
    save_crawl_metadata()
    print("All crawl data written to data/stocks.json.")

    # Write GitHub Actions Job Summary
    write_github_summary(successful_crawl_count, failures, aborted=False)

    if failures:
        sys.exit(2)

if __name__ == '__main__':
    main()
