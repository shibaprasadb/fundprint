"""The browser stand-in for rapidfuzz must pick the same fund name as the real library."""
import importlib.util
import sys
from pathlib import Path

import pytest

rapidfuzz = pytest.importorskip("rapidfuzz")  # the real one, installed on desktop only
from rapidfuzz import fuzz as real_fuzz, process as real_process, utils as real_utils  # noqa: E402

STUB = Path(__file__).resolve().parents[1] / "web" / "rapidfuzz_stub"


def load_stub():
    spec = importlib.util.spec_from_file_location("stub_rapidfuzz", STUB / "__init__.py",
                                                  submodule_search_locations=[str(STUB)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stub_rapidfuzz"] = mod
    spec.loader.exec_module(mod)
    return mod


CASES = [
    ("HDFC Flexi Cap Fund - Direct Plan - Growth Option",
     ["HDFC FLEXI CAP FUND - DIRECT PLAN - GROWTH", "HDFC FLEXI CAP FUND - DIRECT PLAN - IDCW", "HDFC TOP 100 FUND - DIRECT PLAN"]),
    ("Axis Bluechip Fund - Direct Growth",
     ["AXIS BLUECHIP FUND - DIRECT PLAN - GROWTH", "AXIS BLUECHIP FUND - REGULAR PLAN - GROWTH"]),
    ("Nippon India Small Cap Fund",
     ["Nippon India Small Cap Fund - Growth Plan", "Nippon India Small Cap Fund - IDCW Plan", "Nippon India Multi Cap Fund"]),
]


@pytest.mark.parametrize("query,choices", CASES)
def test_same_pick_as_real_rapidfuzz(query, choices):
    stub = load_stub()
    mine = stub.process.extractOne(query, choices, processor=stub.utils.default_process,
                                   scorer=stub.fuzz.token_sort_ratio)
    real = real_process.extractOne(query, choices, processor=real_utils.default_process,
                                   scorer=real_fuzz.token_sort_ratio)
    assert mine[0] == real[0] and mine[2] == real[2]
    assert abs(mine[1] - real[1]) < 15        # scores differ a little; the pick is what matters


def test_returns_three_values_like_the_real_one():
    stub = load_stub()
    key, score, pos = stub.process.extractOne("a b", ["b a", "zzz"], processor=stub.utils.default_process,
                                              scorer=stub.fuzz.token_sort_ratio)
    assert key == "b a" and score == 100 and pos == 0


def test_statement_with_ambiguous_fund_parses_with_the_stub(tmp_path):
    """Parse a fund that matches several database rows, with the stub standing in for rapidfuzz."""
    import subprocess
    (tmp_path / "rapidfuzz").symlink_to(STUB, target_is_directory=True)   # found before the real one
    root = Path(__file__).resolve().parents[1]
    code = ("import sys, rapidfuzz; assert 'stub' in rapidfuzz.__doc__.lower() or 'stand-in' in rapidfuzz.__doc__.lower();"
            f"sys.path.insert(0, {str(root)!r});"
            "from fundprint.parse import parse_cas;"
            f"p = parse_cas(open({str(root / 'tests/fixtures/sample_cas_multimatch.pdf')!r}, 'rb').read(), '');"
            "print(p.schemes['isin'].tolist(), len(p.txns))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={"PYTHONPATH": str(tmp_path), "PATH": "/usr/bin:/bin"})
    assert out.returncode == 0, out.stderr[-500:]
    assert "INF044D01583" in out.stdout
