# contextual_bandit.py
import json
import numpy as np
import random
from typing import List
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from models import Base, engine  # ensure models.Base is the same SQLAlchemy Base used by your models

SessionLocal = sessionmaker(bind=engine)

class BanditState(Base):
    __tablename__ = "bandit_state"
    id = Column(Integer, primary_key=True, index=True)
    bandit_name = Column(String, index=True)
    action_id = Column(Integer, index=True)
    d = Column(Integer)
    A_json = Column(Text)
    b_json = Column(Text)

Base.metadata.create_all(bind=engine)

class LinUCB:
    def __init__(self, bandit_name: str, actions: List[int], d: int, alpha: float = 1.0):
        self.bandit_name = bandit_name
        self.actions = list(actions)
        self.d = d
        self.alpha = alpha
        self._load_state()

    def _default_state(self):
        return {a: {"A": np.eye(self.d), "b": np.zeros(self.d)} for a in self.actions}

    def _load_state(self):
        self.state = {}
        session = SessionLocal()
        rows = session.query(BanditState).filter(BanditState.bandit_name == self.bandit_name).all()
        if not rows:
            # initialize default and persist
            st = self._default_state()
            for a, s in st.items():
                row = BanditState(
                    bandit_name=self.bandit_name,
                    action_id=int(a),
                    d=self.d,
                    A_json=json.dumps(s["A"].tolist()),
                    b_json=json.dumps(s["b"].tolist())
                )
                session.add(row)
            session.commit()
            session.close()
            self.state = st
            return

        for r in rows:
            try:
                A = np.array(json.loads(r.A_json), dtype=float)
                b = np.array(json.loads(r.b_json), dtype=float)
                if A.shape != (self.d, self.d) or b.shape != (self.d,):
                    raise ValueError("dimension mismatch")
                self.state[int(r.action_id)] = {"A": A, "b": b}
            except Exception:
                self.state[int(r.action_id)] = {"A": np.eye(self.d), "b": np.zeros(self.d)}
        session.close()

        # ensure all actions exist
        for a in self.actions:
            if a not in self.state:
                self.state[a] = {"A": np.eye(self.d), "b": np.zeros(self.d)}
                self._persist_action(a)

    def _persist_action(self, action_id: int):
        s = self.state[action_id]
        session = SessionLocal()
        row = session.query(BanditState).filter(
            BanditState.bandit_name == self.bandit_name,
            BanditState.action_id == action_id
        ).first()
        if row:
            row.A_json = json.dumps(s["A"].tolist())
            row.b_json = json.dumps(s["b"].tolist())
        else:
            row = BanditState(
                bandit_name=self.bandit_name,
                action_id=int(action_id),
                d=self.d,
                A_json=json.dumps(s["A"].tolist()),
                b_json=json.dumps(s["b"].tolist())
            )
            session.add(row)
        session.commit()
        session.close()

    def choose(self, x_context: np.ndarray, eps: float = 0.1):
        """
        x_context: shape (d,)
        returns: chosen_action_id, scores (dict)
        """
        assert x_context.shape == (self.d,)
        # epsilon-greedy exploration
        if random.random() < eps:
            chosen = random.choice(self.actions)
            return chosen, {}

        scores = {}
        for a in self.actions:
            A = self.state[a]["A"]
            b = self.state[a]["b"]
            A_inv = np.linalg.inv(A)
            theta = A_inv.dot(b)
            pta = float(theta.dot(x_context) + self.alpha * np.sqrt(x_context.dot(A_inv).dot(x_context)))
            scores[a] = pta
        chosen = max(scores, key=lambda k: scores[k])
        return chosen, scores

    def update(self, action_id: int, x_context: np.ndarray, reward: float):
        assert x_context.shape == (self.d,)
        A = self.state[action_id]["A"]
        b = self.state[action_id]["b"]
        A_new = A + np.outer(x_context, x_context)
        b_new = b + reward * x_context
        self.state[action_id]["A"] = A_new
        self.state[action_id]["b"] = b_new
        self._persist_action(action_id)
