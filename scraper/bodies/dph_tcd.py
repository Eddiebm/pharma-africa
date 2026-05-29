"""
Direction de la Pharmacie et des Médicaments (DPH) - Chad
Portal URL: https://www.sante.gov.td

This portal appears to be a government health ministry website with no direct public drug registration search functionality.
The provided HTML snippet indicates a "FETCH_ERROR: [Errno 8] nodename nor servname provided, or not known", suggesting the target URL is either invalid, unreachable, or does not host the expected content.
As there is no apparent public API or searchable database of registered medicines, this scraper will return an empty list.
"""
import re
import logging
from datetime import date
import httpx
from bs4 import BeautifulSoup

from base import BaseRegulatoryScraper, RegistrationRecord
from normalize import parse_date, normalize_status, clean

COUNTRY_CODE = "TCD"
BODY_CODE = "DPH_TCD"
PORTAL_URL = "https://www.sante.gov.td"

# If the portal provides no search functionality, we will not attempt to scrape it.
# A log warning will be issued, and an empty list will be returned.


class ChadScraper(BaseRegulatoryScraper):
    body_code = BODY_CODE
    country_code = COUNTRY_CODE
    source_url = PORTAL_URL

    def fetch(self) -> list[RegistrationRecord]:
        self.log(f"Attempting to access portal: {self.source_url}")
        
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                # The fetch_error in the provided HTML snippet suggests the site might not be accessible or is returning an error.
                # If the site does not provide a searchable drug registry, we log a warning and return an empty list.
                # A simple GET request is made to check for basic accessibility and content.
                response = client.get(self.source_url)
                response.raise_for_status() # Raise an exception for bad status codes

                # Basic check to see if the response content is likely an error or not a searchable page.
                # If the content is too short, or contains common error indicators, we assume no search is available.
                if len(response.text) < 500 or "FETCH_ERROR" in response.text or "Page not found" in response.text:
                    self.warn("Portal does not appear to host a public drug registration search. Returning empty list.")
                    return []
                
                # Further inspection would be needed here if a table or form elements suggesting a search were present.
                # Since no such elements are indicated and the error message is prominent, we proceed with returning empty.
                self.warn("Portal accessed, but no clear drug search functionality detected. Returning empty list.")
                return []

        except httpx.HTTPStatusError as e:
            self.warn(f"HTTP error accessing {self.source_url}: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.RequestError as e:
            self.warn(f"Request error accessing {self.source_url}: {e}")
            return []
        except Exception as e:
            self.warn(f"An unexpected error occurred while accessing {self.source_url}: {e}")
            return []
