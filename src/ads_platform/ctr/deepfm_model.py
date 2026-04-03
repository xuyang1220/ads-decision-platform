from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


class DeepFMNetwork(nn.Module):
    """Compact DeepFM network for inference and small-scale training.

    This is a practical starter implementation, not a final large-scale serving model.
    """

    def __init__(
        self,
        field_bucket_sizes: list[int],
        num_dense_features: int,
        embedding_dim: int = 8,
        mlp_hidden_dims: tuple[int, ...] = (64, 32),
    ):
        super().__init__()
        self.field_bucket_sizes = list(field_bucket_sizes)
        self.num_dense_features = num_dense_features
        self.embedding_dim = embedding_dim
        self.embeddings = nn.ModuleList(
            [nn.Embedding(num_embeddings=size, embedding_dim=embedding_dim) for size in self.field_bucket_sizes]
        )
        self.linear_embeddings = nn.ModuleList(
            [nn.Embedding(num_embeddings=size, embedding_dim=1) for size in self.field_bucket_sizes]
        )
        self.dense_linear = nn.Linear(num_dense_features, 1)
        deep_input_dim = num_dense_features + len(self.field_bucket_sizes) * embedding_dim

        layers: list[nn.Module] = []
        prev_dim = deep_input_dim
        for hidden_dim in mlp_hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, 1))
        self.mlp = nn.Sequential(*layers)

    def forward(self, dense_x: torch.Tensor, sparse_x: torch.Tensor) -> torch.Tensor:
        linear_term = self.dense_linear(dense_x)
        first_order_sparse = []
        fm_embeddings = []

        for field_idx, (emb, linear_emb) in enumerate(zip(self.embeddings, self.linear_embeddings, strict=True)):
            field_ids = sparse_x[:, field_idx]
            fm_vec = emb(field_ids)
            fm_embeddings.append(fm_vec)
            first_order_sparse.append(linear_emb(field_ids))

        linear_sparse_term = torch.stack(first_order_sparse, dim=1).sum(dim=1)
        fm_stack = torch.stack(fm_embeddings, dim=1)
        summed = fm_stack.sum(dim=1)
        summed_square = summed.pow(2)
        square_summed = fm_stack.pow(2).sum(dim=1)
        fm_term = 0.5 * (summed_square - square_summed).sum(dim=1, keepdim=True)

        deep_input = torch.cat([dense_x, fm_stack.flatten(start_dim=1)], dim=1)
        deep_term = self.mlp(deep_input)
        logits = linear_term + linear_sparse_term + fm_term + deep_term
        return torch.sigmoid(logits).squeeze(-1)


@dataclass(slots=True)
class TorchInferenceWrapper:
    model: DeepFMNetwork
    device: str = "cpu"

    def __post_init__(self) -> None:
        self.model.eval()
        self.model.to(self.device)

    @torch.no_grad()
    def predict(self, features: dict[str, list[float] | list[int] | dict]) -> float:
        dense = torch.tensor([features["dense_values"]], dtype=torch.float32, device=self.device)
        sparse = torch.tensor([features["sparse_indices"]], dtype=torch.long, device=self.device)
        score = self.model(dense, sparse)
        return float(score.item())
