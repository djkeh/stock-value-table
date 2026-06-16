import os
import sys
import json

def calculate_disparity_rate(market_cap_str, op_list):
    """
    Calculates the disparity rate between target market cap and current market cap.
    Target Market Cap = Most future observable operating profit * 10
    Disparity Rate (%) = (Target Market Cap - Market Cap) / Market Cap * 100
    Returns a string rounded to 1 decimal place (e.g. "135.0") or "-" if unavailable.
    """
    if not market_cap_str or not op_list:
        return "-"
    
    mcap_clean = market_cap_str.replace(",", "").strip()
    if mcap_clean in ["", "-", "N/A"]:
        return "-"
    try:
        mcap_val = float(mcap_clean)
        if mcap_val <= 0:
            return "-"
    except ValueError:
        return "-"
    
    # Find the most future observable operating profit (reversed search)
    target_op_str = None
    for op in reversed(op_list):
        if op and op.strip() not in ["", "-", "N/A"]:
            target_op_str = op.strip()
            break
            
    if not target_op_str:
        return "-"
        
    try:
        op_clean = target_op_str.replace(",", "")
        op_val = float(op_clean)
        target_mcap = op_val * 10
        rate = (target_mcap - mcap_val) / mcap_val * 100
        return f"{rate:.1f}"
    except ValueError:
        return "-"

def recalculate_data(stocks_list):
    """
    Recalculates all derived metrics (like disparity_rate) for the given stocks in-place.
    """
    for item in stocks_list:
        if "gicode" in item:
            market_cap = item.get("market_cap", "-")
            op_list = item.get("영업이익", [])
            item["disparity_rate"] = calculate_disparity_rate(market_cap, op_list)

def main():
    if len(sys.argv) < 2:
        print("Usage: python recalculate.py <filepath>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error: Failed to read or parse JSON from '{filepath}': {e}")
        sys.exit(1)
        
    if not isinstance(data, list):
        print(f"Error: Expected a JSON array in '{filepath}'.")
        sys.exit(1)
        
    recalculate_data(data)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully recalculated metrics in '{filepath}'.")
    except Exception as e:
        print(f"Error: Failed to write updated JSON to '{filepath}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
