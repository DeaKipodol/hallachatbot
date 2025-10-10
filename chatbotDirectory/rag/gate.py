"""Regulation gate logic for RAG."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from .. import character
from ..common import client, model


@dataclass(slots=True)
class GateDecision:
    is_regulation: bool
    reason: str | None = None


class RegulationGate:
    """RAG 여부를 판단하는 책임을 가집니다. 레그여부와 자신의 판단이유를 반환하는역할입니다."""

    def __init__(
        self,
        *,
        openai_client=client,
        model_name: str | None = None,
        debug_fn: Callable[[str], None] | None = None,
    ) -> None:
        self._client = openai_client
        self._model_name = model_name or model.advanced
        self._debug = debug_fn or (lambda _: None)

    def decide(self, question: str) -> GateDecision:
        self._debug(
            f"gate.decide: evaluating question='{question[:60]}...' with model={self._model_name}"
        )
        prompt = [
            {"role": "system", "content": character.decide_rag},
            {"role": "user", "content": question},
        ]

        schema = {
            "type": "object",
            "properties": {
                "is_regulation": {"type": "boolean"},
                "reason": {"type": "string"},
            },
            "required": ["is_regulation", "reason"],
            "additionalProperties": False,
        }

        try:
            response = self._client.responses.create(
                model=self._model_name,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "rag_gate_schema",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            raw = (getattr(response, "output_text", "") or "").strip()
            payload = json.loads(raw) if raw else {}
            is_reg = bool(payload.get("is_regulation"))
            reason = (payload.get("reason") or "").strip() or None
            if reason:
                self._debug(f"gate.decide: reason='{reason}'")
            self._debug(f"gate.decide: decision={is_reg}")
            return GateDecision(is_regulation=is_reg, reason=reason)
        except Exception as exc:
            self._debug(f"gate.decide: structured output failure -> {exc}")
            keywords = ["학사", "규정", "졸업", "수강", "성적", "장학", "징계"]
            fallback = any(keyword in question for keyword in keywords)
            self._debug(f"gate.decide: keyword fallback decision={fallback}")
            return GateDecision(is_regulation=fallback)
