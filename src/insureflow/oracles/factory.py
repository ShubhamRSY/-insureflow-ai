from __future__ import annotations

from insureflow.config import settings
from insureflow.oracles.aplus_client import APlusClient
from insureflow.oracles.bureau_client import CreditBureauClient
from insureflow.oracles.cat_model_client import CatastropheModelClient
from insureflow.oracles.clue_client import CLUEClient
from insureflow.oracles.ncci_client import NCCIClient
from insureflow.oracles.oracle_agent import OracleAgent
from insureflow.oracles.osha_client import OSHAClient
from insureflow.oracles.public_records_client import PublicRecordsClient
from insureflow.oracles.rating_agency_client import CreditRatingAgencyClient


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


def build_bureau_client() -> CreditBureauClient:
    return CreditBureauClient(
        api_key=settings.bureau_api_key,
        base_url=settings.bureau_api_url,
        mode=_oracle_mode(),
        query_path=settings.bureau_query_path,
    )


def build_public_records_client() -> PublicRecordsClient:
    return PublicRecordsClient(
        api_key=settings.public_records_api_key,
        base_url=settings.public_records_api_url,
        mode=_oracle_mode(),
        query_path=settings.public_records_query_path,
    )


def build_osha_client() -> OSHAClient:
    return OSHAClient(
        api_key=settings.osha_api_key,
        base_url=settings.osha_api_url,
        mode=_oracle_mode(),
        query_path=settings.osha_query_path,
    )


def build_rating_agency_client() -> CreditRatingAgencyClient:
    return CreditRatingAgencyClient(
        api_key=settings.rating_agency_api_key,
        base_url=settings.rating_agency_api_url,
        mode=_oracle_mode(),
        query_path=settings.rating_agency_query_path,
    )


def build_oracle_agent() -> OracleAgent:
    return OracleAgent(
        clue_client=build_clue_client(),
        aplus_client=build_aplus_client(),
        ncci_client=build_ncci_client(),
        cat_model=build_cat_client(),
        bureau_client=build_bureau_client(),
        public_records_client=build_public_records_client(),
        osha_client=build_osha_client(),
        rating_agency_client=build_rating_agency_client(),
    )
