import os
import json
import pytest
from unittest.mock import MagicMock, patch
from recalculate import (
    calculate_disparity_rate,
    recalculate_data
)

# -------------------------------------------------------------------------
# 1. calculate_disparity_rate Tests
# -------------------------------------------------------------------------
def test_calculate_disparity_rate():
    # Samsung Electronics Example:
    # market_cap = "19,701,959", op_list = ['436,011', '3,563,998', '4,673,105', '4,629,076']
    # Target Market Cap = 4,629,076 * 10 = 46,290,760
    # Disparity = (46,290,760 - 19,701,959) / 19,701,959 * 100 = 134.955... -> 135.0%
    assert calculate_disparity_rate("19,701,959", ['436,011', '3,563,998', '4,673,105', '4,629,076']) == "135.0"
    
    # Fallback to previous years when D_7 is missing:
    assert calculate_disparity_rate("19,701,959", ['436,011', '3,563,998', '4,673,105', '-']) == "137.2"
    assert calculate_disparity_rate("19,701,959", ['436,011', '3,563,998', '-', '-']) == "80.9"
    assert calculate_disparity_rate("19,701,959", ['436,011', '-', '-', '-']) == "-77.9"
    
    # All operating profits missing:
    assert calculate_disparity_rate("19,701,959", ['-', '-', '-', '-']) == "-"
    
    # Missing market cap:
    assert calculate_disparity_rate("-", ['436,011', '3,563,998', '4,673,105', '4,629,076']) == "-"
    assert calculate_disparity_rate("", ['436,011', '3,563,998', '4,673,105', '4,629,076']) == "-"
    assert calculate_disparity_rate(None, ['436,011', '3,563,998', '4,673,105', '4,629,076']) == "-"
    assert calculate_disparity_rate("0", ['436,011']) == "-"
    assert calculate_disparity_rate("-10", ['436,011']) == "-"
    assert calculate_disparity_rate("invalid", ['436,011']) == "-"
    
    # Missing/empty op_list:
    assert calculate_disparity_rate("100", []) == "-"
    assert calculate_disparity_rate("100", None) == "-"
    
    # Invalid numbers in op_list:
    assert calculate_disparity_rate("100", ["invalid_op"]) == "-"


# -------------------------------------------------------------------------
# 2. recalculate_data Tests
# -------------------------------------------------------------------------
def test_recalculate_data():
    data = [
        {
            "gicode": "A005930",
            "market_cap": "19,701,959",
            "영업이익": ['436,011', '3,563,998', '4,673,105', '4,629,076']
        },
        {
            "gicode": "A005380",
            "market_cap": "50,000,000",
            "영업이익": ["1", "2", "3", "4"]
        },
        {
            "name": "no_gicode_row"
        }
    ]
    recalculate_data(data)
    assert data[0]["disparity_rate"] == "135.0"
    assert data[1]["disparity_rate"] == "-100.0"
    assert "disparity_rate" not in data[2]


# -------------------------------------------------------------------------
# 3. CLI Main Program Flow Tests
# -------------------------------------------------------------------------
def test_recalculate_main_success(tmp_path):
    import recalculate
    f = tmp_path / "stocks.json"
    dummy_data = [
        {
            "gicode": "A005930",
            "market_cap": "19,701,959",
            "영업이익": ['436,011', '3,563,998', '4,673,105', '4,629,076']
        }
    ]
    f.write_text(json.dumps(dummy_data), encoding="utf-8")
    with patch("sys.argv", ["recalculate.py", str(f)]):
        recalculate.main()
    
    updated_data = json.loads(f.read_text(encoding="utf-8"))
    assert updated_data[0]["disparity_rate"] == "135.0"


def test_recalculate_main_missing_args():
    import recalculate
    with patch("sys.argv", ["recalculate.py"]):
        with pytest.raises(SystemExit) as excinfo:
            recalculate.main()
        assert excinfo.value.code == 1


def test_recalculate_main_file_not_found():
    import recalculate
    with patch("sys.argv", ["recalculate.py", "non_existent_file.json"]):
        with pytest.raises(SystemExit) as excinfo:
            recalculate.main()
        assert excinfo.value.code == 1


def test_recalculate_main_parse_error(tmp_path):
    import recalculate
    f = tmp_path / "invalid.json"
    f.write_text("invalid json", encoding="utf-8")
    with patch("sys.argv", ["recalculate.py", str(f)]):
        with pytest.raises(SystemExit) as excinfo:
            recalculate.main()
        assert excinfo.value.code == 1


def test_recalculate_main_not_a_list(tmp_path):
    import recalculate
    f = tmp_path / "dict.json"
    f.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with patch("sys.argv", ["recalculate.py", str(f)]):
        with pytest.raises(SystemExit) as excinfo:
            recalculate.main()
        assert excinfo.value.code == 1


def test_recalculate_main_write_error(tmp_path):
    import recalculate
    import builtins
    f = tmp_path / "read_only.json"
    f.write_text("[]", encoding="utf-8")
    
    original_open = builtins.open
    def mock_open(file, mode="r", *args, **kwargs):
        if "w" in mode:
            raise IOError("Permission denied")
        return original_open(file, mode, *args, **kwargs)
        
    with patch("sys.argv", ["recalculate.py", str(f)]):
        with patch("builtins.open", mock_open):
            with pytest.raises(SystemExit) as excinfo:
                recalculate.main()
            assert excinfo.value.code == 1


def test_recalculate_run_as_main(tmp_path):
    import runpy
    f = tmp_path / "stocks.json"
    f.write_text("[]", encoding="utf-8")
    with patch("sys.argv", ["recalculate.py", str(f)]):
        runpy.run_path("recalculate.py", run_name="__main__")
