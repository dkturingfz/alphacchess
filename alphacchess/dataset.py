from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from .notation import iccs_to_action
from .versions import VERSION_METADATA
from .xiangqi_game import XiangqiState


class DatasetBuilder:
    def build(self, records: List[Dict]) -> Dict:
        normalized = []
        for record in records:
            state = XiangqiState.from_fen(record["initial_fen"])
            actions = []
            for mv in record["moves_iccs"]:
                action = iccs_to_action(mv)
                if action not in state.legal_actions():
                    raise ValueError(f"Illegal move {mv} for position {state.to_fen()}")
                actions.append(action)
                state.apply_action(action)
            normalized.append(
                {
                    "initial_fen": record["initial_fen"],
                    "moves_iccs": list(record["moves_iccs"]),
                    "moves_action": actions,
                    "final_fen": state.to_fen(),
                    "result": state.returns(),
                }
            )

        payload = {
            "metadata": dict(VERSION_METADATA),
            "records": normalized,
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload["metadata"]["content_sha256"] = hashlib.sha256(raw).hexdigest()
        return payload

    def build_to_path(self, records: List[Dict], out_path: str) -> Dict:
        payload = self.build(records)
        Path(out_path).write_text(json.dumps(payload, indent=2))
        return payload
