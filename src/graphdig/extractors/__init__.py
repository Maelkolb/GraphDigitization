from graphdig.extractors.base import ExtractParams, LineExtractor


def get_extractor(name: str) -> LineExtractor:
    if name == "lineformer_local":
        from graphdig.extractors.lineformer_local import LineFormerLocal

        return LineFormerLocal()
    if name == "colab_bundle":
        from graphdig.extractors.colab_bundle import ColabBundle

        return ColabBundle()
    if name == "stub":
        from graphdig.extractors.stub import StubExtractor

        return StubExtractor()
    raise ValueError(f"unknown extractor backend: {name}")


__all__ = ["ExtractParams", "LineExtractor", "get_extractor"]
