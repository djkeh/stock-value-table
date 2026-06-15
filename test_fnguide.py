import requests
from bs4 import BeautifulSoup
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}

def clean_and_format_op(val_str):
    """
    Cleans a number string (e.g. '436,010.51' or '3,563,998') 
    by removing commas, rounding to the nearest integer, 
    and formatting back with commas.
    """
    if not val_str or val_str == '-':
        return val_str
    try:
        val_clean = val_str.replace(',', '')
        val_float = float(val_clean)
        val_rounded = round(val_float)
        return f"{val_rounded:,}"
    except ValueError:
        return val_str

def crawl_samsung():
    gicode = "A005930"
    
    # 1. Fetch and Parse Main Page
    main_url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?pGB=1&gicode={gicode}"
    resp_main = requests.get(main_url, headers=headers)
    if resp_main.status_code != 200:
        raise Exception(f"Failed to fetch main page: {resp_main.status_code}")
    
    soup_main = BeautifulSoup(resp_main.content, 'lxml')
    
    # - giName
    gi_name_el = soup_main.find(id='giName')
    gi_name = gi_name_el.text.strip() if gi_name_el else "Not Found"
    
    # - 시가총액 and 현재가 from 시세현황 table
    table_sise = soup_main.find('table', class_='us_table_ty1')
    market_cap = None
    current_price = None
    
    if table_sise:
        for row in table_sise.find_all('tr'):
            cells = [cell.text.strip() for cell in row.find_all(['th', 'td'])]
            if not cells:
                continue
            
            # Extract 시가총액 (보통주)
            for i, cell in enumerate(cells):
                if cell.startswith("시가총액(보통주)"):
                    if i + 1 < len(cells):
                        # E.g. '18,854,249'
                        market_cap = cells[i+1].strip()
            
            # Extract 현재가 (종가 from row 0)
            if cells[0] == "종가/ 전일대비/ 수익률":
                val = cells[1]
                current_price = val.split('/')[0].strip()

    # 2. Fetch and Parse Consensus JSON
    # We use the direct JSON endpoint that provides the table data for the Consensus page.
    # Annual (A) and Consolidated (D)
    json_url = f"https://comp.fnguide.com/SVO2/json/data/01_06/01_{gicode}_A_D.json"
    resp_json = requests.get(json_url, headers=headers)
    if resp_json.status_code != 200:
        raise Exception(f"Failed to fetch consensus JSON: {resp_json.status_code}")
        
    resp_json.encoding = 'utf-8-sig'
    jsondata = resp_json.json()
    
    # Years mapping: 2025 (D_4), 2026 (D_5), 2027 (D_6), 2028 (D_7)
    target_keys = ['D_4', 'D_5', 'D_6', 'D_7']
    
    pbr_list = []
    per_list = []
    eps_list = []
    op_list = [] # 영업이익
    
    for item in jsondata.get('comp', []):
        account_nm = item.get('ACCOUNT_NM', '')
        
        if account_nm.startswith("PBR"):
            pbr_list = [item.get(k, '') for k in target_keys]
        elif account_nm.startswith("PER"):
            per_list = [item.get(k, '') for k in target_keys]
        elif account_nm.startswith("EPS"):
            eps_list = [item.get(k, '') for k in target_keys]
        elif account_nm.startswith("영업이익"):
            # 영업이익 values need cleaning and formatting
            raw_ops = [item.get(k, '') for k in target_keys]
            op_list = [clean_and_format_op(val) for val in raw_ops]
            
    return {
        "종목명": gi_name,
        "시가총액": market_cap,
        "현재가": current_price,
        "PBR": pbr_list,
        "PER": per_list,
        "EPS": eps_list,
        "영업이익": op_list
    }

if __name__ == '__main__':
    crawled = crawl_samsung()
    
    expected = {
        "종목명": "삼성전자",
        "시가총액": "18,854,249",
        "현재가": "322,500",
        "PBR": ["1.87", "3.05", "2.03", "1.50"],
        "PER": ["18.27", "7.39", "5.68", "5.60"],
        "EPS": ["6,563.57", "43,628", "56,761", "57,625"],
        "영업이익": ["436,011", "3,563,998", "4,673,105", "4,629,076"]
    }
    
    print("=== Crawled Results ===")
    print(json.dumps(crawled, ensure_ascii=False, indent=2))
    
    print("\n=== Expected Results ===")
    print(json.dumps(expected, ensure_ascii=False, indent=2))
    
    # Compare
    mismatch = False
    for k, v in expected.items():
        crawled_val = crawled.get(k)
        if crawled_val != v:
            print(f"Mismatch in '{k}': expected {v}, got {crawled_val}")
            mismatch = True
            
    if not mismatch:
        print("\nSUCCESS: All crawled values match expected results perfectly!")
    else:
        print("\nFAILURE: Some values do not match expected results.")
        
    # Write results to file
    with open("test_result.json", "w", encoding="utf-8") as f:
        json.dump({"crawled": crawled, "expected": expected, "success": not mismatch}, f, ensure_ascii=False, indent=2)
