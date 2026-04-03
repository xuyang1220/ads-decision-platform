from __future__ import annotations

import hashlib
import math
from typing import Any

from ads_platform.common.utils import safe_float
from ads_platform.ctr.base import FeatureTransformer
from ads_platform.ctr.feature_spec import DeepFMFeatureSpec
from ads_platform.schemas.request import AdCandidate, RequestContext


class DeepFMFeatureTransformer(FeatureTransformer):
    """Train/serve-consistent transformer for a DeepFM-style model.

    The output is intentionally simple and serializable so it can be used by both
    local replay and online serving.
    """

    def __init__(self, feature_spec: DeepFMFeatureSpec):
        self.feature_spec = feature_spec

    @staticmethod
    def _stable_bucket(field_name: str, token: str, num_buckets: int) -> int:
        payload = f"{field_name}={token}".encode("utf-8")
        digest = hashlib.md5(payload).hexdigest()
        bucket = int(digest[:8], 16) % max(num_buckets, 1)
        return bucket

    def _raw_value(self, request: RequestContext, candidate: AdCandidate, name: str) -> Any:
        if name in candidate.features:
            return candidate.features[name]
        if name in candidate.extra:
            return candidate.extra[name]
        if name in request.extra:
            return request.extra[name]
        if hasattr(request, name):
            return getattr(request, name)
        if hasattr(candidate, name):
            return getattr(candidate, name)
        return None

    def transform(self, request: RequestContext, candidate: AdCandidate) -> dict[str, Any]:
        dense_values: list[float] = []
        sparse_indices: list[int] = []

        for feature in self.feature_spec.numeric_features:
            value = safe_float(self._raw_value(request, candidate, feature.name), feature.default)
            if feature.log1p:
                value = math.log1p(max(value, 0.0))
            dense_values.append(value)

        for feature in self.feature_spec.categorical_features:
            raw = self._raw_value(request, candidate, feature.name)
            token = feature.default_token if raw is None else str(raw)
            sparse_indices.append(self._stable_bucket(feature.name, token, feature.num_buckets))

        return {
            "dense_values": dense_values,
            "sparse_indices": sparse_indices,
            "feature_names": {
                "numeric": [f.name for f in self.feature_spec.numeric_features],
                "categorical": [f.name for f in self.feature_spec.categorical_features],
            },
        }
