import numpy as np


def test_pooling_ignores_padding_and_normalizes():
    from src.services.multilingual_embeddings import mean_pool

    hidden = np.array([[[3.0, 4.0], [999.0, 999.0]]])
    out = mean_pool(hidden, np.array([[1, 0]]))
    np.testing.assert_allclose(out, [[0.6, 0.8]])


def test_empty_attention_never_creates_nan():
    from src.services.multilingual_embeddings import mean_pool

    out = mean_pool(np.zeros((1, 2, 2)), np.zeros((1, 2)))
    assert np.isfinite(out).all()
