from dataclasses import dataclass, field
from datetime import date
from abc import ABC, abstractmethod
from typing import Optional
import logging


@dataclass
class RegistrationRecord:
    inn: str
    brand_name: Optional[str]
    country_code: str
    registration_no: Optional[str]
    holder: Optional[str]
    local_agent: Optional[str]
    status: str  # 'active' | 'expired' | 'suspended' | 'pending' | 'alert' | 'unknown'
    expiry_date: Optional[date]
    dosage_forms: list[str] = field(default_factory=list)
    source_url: str = ""
    source_type: str = "scrape"  # 'scrape' | 'document' | 'manual'
    raw: dict = field(default_factory=dict)


class BaseRegulatoryScraper(ABC):
    body_code: str = ""
    country_code: str = ""
    source_url: str = ""

    @abstractmethod
    def fetch(self) -> list[RegistrationRecord]:
        ...

    def log(self, msg: str):
        logging.info(f"[{self.body_code}] {msg}")

    def warn(self, msg: str):
        logging.warning(f"[{self.body_code}] {msg}")
