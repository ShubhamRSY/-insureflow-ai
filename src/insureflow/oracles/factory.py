from __future__ import annotations

from insureflow.config import settings
from insureflow.oracles.aplus_client import APlusClient
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.oracle_agent import OracleAgent


def _oracle_mode() -> str:
    return (settings.oracle_mode or "simulated").lower()


def build_clue_client() -> CLUEClient:
    return CLUEClient(
        api_key=settings.clue_api_key,
        base_url=settings.clue_api_url,
        mode=_oracle_mode(),
        query_path=settings.clue_query_path,
    )


def build_ncci_client() -> NCCIClient:
    return NCCIClient(
        api_key=settings.ncci_api_key or settings.verisk_api_key,
        base_url=settings.ncci_api_url,
        mode=_oracle_mode(),
        query_path=settings.ncci_query_path,
    )


def build_aplus_client() -> APlusClient:
    return APlusClient(
        api_key=settings.aplus_api_key or settings.verisk_api_key,
        base_url=settings.aplus_api_url,
        mode=_oracle_mode(),
        query_path=settings.aplus_query_path,
    )


def build_cat_client() -> CatastropheModelClient:
    return CatastropheModelClient(
        api_key=settings.cat_api_key or settings.verisk_api_key,
        base_url=settings.cat_api_url,
        mode=_oracle_mode(),
        query_path=settings.cat_query_path,
    )


def build_oracle_agent() -> OracleAgent:
    return OracleAgent(
        clue_client=build_clue_client(),
        aplus_client=build_aplus_client(),
        ncci_client=build_ncci_client(),
        cat_model=build_cat_client(),
    )
