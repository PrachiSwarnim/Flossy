# nightly_audit.py
import os
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models import LLMInteraction
from rl_core import bandit
from utils import ai_generate
from audit_llm_responses import (
    evaluate_instruction,
    evaluate_safety,
    evaluate_coherence
)

def compute_reward(row):
    """
    Weighted reward based on your LLM QA metrics.
    Final reward ∈ [0,1]
    """
    sim = row.semantic_similarity or 0
    grd = row.groundedness or 0
    inst = (row.instruction_score or 0) / 5
    safe = (row.safety_score or 0) / 5
    coh = (row.coherence_score or 0) / 5

    accuracy = (
        0.25 * sim +
        0.25 * grd +
        0.20 * inst +
        0.15 * safe +
        0.15 * coh
    )
    return accuracy


def nightly_train():
    db: Session = SessionLocal()

    rows = (
        db.query(LLMInteraction)
        .filter(LLMInteraction.trained_once == False)
        .all()
    )

    print(f"🌙 Nightly Audit: {len(rows)} interactions to process.")

    for row in rows:
        # -------- Compute missing LLM scores --------
        if row.instruction_score is None:
            row.instruction_score = evaluate_instruction(row.response)
        if row.safety_score is None:
            row.safety_score = evaluate_safety(row.response)
        if row.coherence_score is None:
            row.coherence_score = evaluate_coherence(row.response)

        # -------- Reward --------
        reward = compute_reward(row)
        row.accuracy_score = reward

        # -------- RL UPDATE --------
        if row.action_id is not None:
            print(f"🧠 Updating bandit for action {row.action_id} with reward={reward:.3f}")
            bandit.update(row.action_id, reward)

        # mark as trained
        row.trained_once = True
        db.commit()

    db.close()
    print("🌙 Nightly RL Training Complete — weights updated.")

if __name__ == "__main__":
    nightly_train()
