# prompt_bandit.py
import json
import os
import tempfile
import threading
from typing import List

WEIGHTS_FILE = "bandit_weights.json"
LOCK = threading.Lock()

class PromptBandit:
    def __init__(self, variants: List[str], weights_file: str = WEIGHTS_FILE):
        self.variants = variants
        self.weights_file = weights_file
        self._load_or_init_weights()

    def _load_or_init_weights(self):
        # load safely, tolerate empty/corrupt file
        with LOCK:
            if not os.path.exists(self.weights_file):
                # file missing -> create default
                self.weights = [1.0] * len(self.variants)
                self._atomic_write(self.weights)
                return

            try:
                with open(self.weights_file, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                    if not raw:
                        raise ValueError("empty file")
                    parsed = json.loads(raw)
                    # validate shape
                    if not isinstance(parsed, list) or len(parsed) != len(self.variants):
                        raise ValueError("invalid shape")
                    self.weights = [float(w) for w in parsed]
            except Exception:
                # fallback: reinitialize with defaults
                self.weights = [1.0] * len(self.variants)
                self._atomic_write(self.weights)

    def _atomic_write(self, weights):
        # atomic write to avoid partial-file states
        tmp_fd, tmp_path = tempfile.mkstemp(prefix="bandit_", suffix=".tmp", dir=".")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as tf:
                json.dump(weights, tf)
                tf.flush()
                os.fsync(tf.fileno())
            os.replace(tmp_path, self.weights_file)  # atomic on POSIX
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def choose(self):
        import random
        total = sum(self.weights)
        # handle degenerate case
        if total <= 0:
            self.weights = [1.0] * len(self.variants)
            total = sum(self.weights)

        r = random.random() * total
        upto = 0.0
        for i, w in enumerate(self.weights):
            upto += w
            if r <= upto:
                return i, self.variants[i]
        return len(self.variants) - 1, self.variants[-1]

    def update(self, idx: int, reward: float):
        # reward expected to be >= 0 (but handle negative)
        with LOCK:
            # simple multiplicative update; clip to avoid collapse
            new_w = max(0.1, self.weights[idx] * (1 + float(reward)))
            self.weights[idx] = new_w
            self._atomic_write(self.weights)

    def save(self):
        with LOCK:
            self._atomic_write(self.weights)

    # convenience helpers
    def get_weights(self):
        return list(self.weights)

    @classmethod
    def init_file(cls, variants: List[str], weights_file: str = WEIGHTS_FILE):
        """Create or overwrite the weights file with defaults."""
        b = cls(variants, weights_file=weights_file)
        b.weights = [1.0] * len(variants)
        b.save()
        return b

    @classmethod
    def print_weights_file(cls, weights_file: str = WEIGHTS_FILE):
        if not os.path.exists(weights_file):
            print("weights file not found:", weights_file)
            return
        try:
            with open(weights_file, "r", encoding="utf-8") as f:
                print("weights file contents:", f.read())
        except Exception as e:
            print("could not read weights file:", e)
