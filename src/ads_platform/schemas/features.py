from abc import ABC, abstractmethod
from typing import Mapping, Any
from request import RequestContext, AdCandidate


class FeatureTransformer(ABC):
    @abstractmethod
    def transform(
        self,
        request: RequestContext,
        candidate: AdCandidate,
    ) -> Mapping[str, Any]:
        raise NotImplementedError