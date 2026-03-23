import subprocess
import sys
from pathlib import Path

from alphacchess.xiangqi_game import XiangqiState

ROOT = Path(__file__).resolve().parents[1]

SAMPLE_FILES = [
    ROOT / "data/test_positions/samples/opening_fens_sample.txt",
    ROOT / "data/test_positions/samples/middlegame_fens_sample.txt",
    ROOT / "data/test_positions/samples/endgame_fens_sample.txt",
    ROOT / "data/test_positions/samples/near_terminal_fens_sample.txt",
    ROOT / "data/test_positions/samples/regression_fens_sample.txt",
    ROOT / "data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
]


def _read_fens(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.strip().startswith("#")]


def test_curated_fen_assets_are_readable_and_legal_sane():
    for path in SAMPLE_FILES:
        assert path.exists(), f"missing sample file: {path}"
        fens = _read_fens(path)
        assert fens, f"sample file is empty: {path}"

        for fen in fens:
            state = XiangqiState.from_fen(fen)
            legal_count = len(state.legal_actions())
            assert legal_count >= 0
            if legal_count == 0:
                assert state.is_terminal()


def test_near_terminal_sample_has_terminal_or_low_legal_count():
    near_terminal = ROOT / "data/test_positions/samples/near_terminal_fens_sample.txt"
    for fen in _read_fens(near_terminal):
        state = XiangqiState.from_fen(fen)
        legal_count = len(state.legal_actions())
        assert state.is_terminal() or legal_count <= 4


def test_validate_fen_samples_cli_smoke():
    proc = subprocess.run(
        [sys.executable, "scripts/validate_fen_samples.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert '"status": "ok"' in proc.stdout
