import os
import csv
import json
import time
import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}

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

def get_with_retry(url, headers, timeout=10, max_retries=3, backoff_factor=2):
    """
    Performs a GET request with retry logic for connection/timeout issues
    and transient HTTP errors.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code in [500, 502, 503, 504]:
                raise requests.exceptions.HTTPError(f"Status {resp.status_code}")
            return resp
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            if attempt == max_retries - 1:
                raise e
            sleep_time = backoff_factor ** attempt
            print(f"      [Retry] Connection failed ({e}). Retrying in {sleep_time}s... ({attempt + 1}/{max_retries})")
            time.sleep(sleep_time)

def crawl_stock(gicode, fallback_name=""):
    try:
        # 1. Fetch and Parse Main Page
        main_url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode={gicode}"
        resp_main = get_with_retry(main_url, headers=headers, timeout=10)
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
                if cells[0] == "종가/ 전일대비/ 수익률":
                    val = cells[1]
                    current_price = val.split('/')[0].strip()

        # 2. Fetch and Parse Consensus JSON
        # Path: /SVO2/json/data/01_06/01_{gicode}_A_D.json (Annual, Consolidated)
        json_url = f"https://comp.fnguide.com/SVO2/json/data/01_06/01_{gicode}_A_D.json"
        resp_json = get_with_retry(json_url, headers=headers, timeout=10)
        if resp_json.status_code != 200:
            print(f"[{gicode}] Error fetching consensus JSON: {resp_json.status_code}")
            return None, f"Error fetching consensus JSON: HTTP {resp_json.status_code}"
            
        resp_json.encoding = 'utf-8-sig'
        jsondata = resp_json.json()
        
        # Target years: 2025 (D_4), 2026 (D_5), 2027 (D_6), 2028 (D_7)
        # We also collect the headers for years to ensure correctness
        years = ["2025", "2026", "2027", "2028"]
        target_keys = ['D_4', 'D_5', 'D_6', 'D_7']
        
        pbr_list = ["-"] * 4
        per_list = ["-"] * 4
        eps_list = ["-"] * 4
        op_list = ["-"] * 4
        
        for item in jsondata.get('comp', []):
            account_nm = item.get('ACCOUNT_NM', '')
            
            if account_nm.startswith("PBR"):
                pbr_list = [item.get(k, '-').strip() for k in target_keys]
            elif account_nm.startswith("PER"):
                per_list = [item.get(k, '-').strip() for k in target_keys]
            elif account_nm.startswith("EPS"):
                eps_list = [item.get(k, '-').strip() for k in target_keys]
            elif account_nm.startswith("영업이익"):
                raw_ops = [item.get(k, '-').strip() for k in target_keys]
                op_list = [clean_and_format_op(val) for val in raw_ops]
        
        # Replace empty values with "-"
        pbr_list = [v if v != "" else "-" for v in pbr_list]
        per_list = [v if v != "" else "-" for v in per_list]
        eps_list = [v if v != "" else "-" for v in eps_list]
        op_list = [v if v != "" else "-" for v in op_list]
        
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

def write_github_summary(successful_count, failures):
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_file:
        return
    
    total = successful_count + len(failures)
    
    lines = []
    lines.append("# 📈 주식 정보 크롤링 리포트 (Stock Crawl Report)")
    lines.append("")
    
    if failures:
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
            resp = requests.get(remote_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                print("Successfully fetched previous stocks data from gh-pages branch.")
                return {item["gicode"]: item for item in data if "gicode" in item}
            else:
                print(f"Notice: Could not fetch remote stocks.json (HTTP {resp.status_code})")
        except Exception as e:
            print(f"Warning: Failed to fetch remote stocks.json: {e}")
            
    return {}

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
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # Skip header
        for row in reader:
            if not row or len(row) < 2:
                continue
            name, gicode = row[0].strip(), row[1].strip()
            print(f"Crawling {name} ({gicode})...")
            stock_info, error = crawl_stock(gicode, fallback_name=name)
            if stock_info:
                stocks_data.append(stock_info)
                successful_crawl_count += 1
                print(f"Successfully crawled {name}.")
            else:
                failures.append({
                    "name": name,
                    "gicode": gicode,
                    "error": error
                })
                # If crawling fails, try to preserve existing data for this stock
                if gicode in existing_stocks:
                    stocks_data.append(existing_stocks[gicode])
                    print(f"Failed to crawl {name}: {error}. Retained existing cached data.")
                else:
                    print(f"Failed to crawl {name}: {error}. No existing cached data available.")
            # Sleep 1 second between requests to respect the server and prevent timeouts/blocking
            time.sleep(1.0)
    
    # Save output to data/stocks.json
    os.makedirs("data", exist_ok=True)
    with open(stocks_path, "w", encoding="utf-8") as f:
        json.dump(stocks_data, f, ensure_ascii=False, indent=2)
    print("All crawl data written to data/stocks.json.")

    # Write GitHub Actions Job Summary
    write_github_summary(successful_crawl_count, failures)

if __name__ == '__main__':
    main()
