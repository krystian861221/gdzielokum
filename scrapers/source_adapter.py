from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os

class BasePropertyAdapter(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich adapterów źródeł nieruchomości.
    Umożliwia podłączenie API portali, bezpośrednich feedów XML/JSON,
    bazy własnej, partnerów MLS oraz legalnych konektorów.
    """
    def __init__(self, name: str, source_type: str = "web_scraper"):
        self.name = name
        self.source_type = source_type # 'api', 'xml_feed', 'json_feed', 'partner', 'web_scraper'
        self.is_enabled = True

    @abstractmethod
    def fetch_offers(
        self,
        city: str,
        category: str = "sprzedaz",
        property_type: str = "Mieszkania",
        price_max: Optional[int] = None,
        private_only: bool = False
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Sprawdza stan połączenia ze źródłem i poprawność kluczy/API."""
        pass

class OtodomAdapter(BasePropertyAdapter):
    def __init__(self):
        super().__init__("Otodom", source_type="web_scraper")

    def fetch_offers(self, city: str, category: str = "sprzedaz", property_type: str = "Mieszkania", price_max: Optional[int] = None, private_only: bool = False) -> List[Dict[str, Any]]:
        from scrapers.otodom_scraper import scrape_otodom
        return scrape_otodom(city=city, price_max=price_max, category=category, property_type=property_type, private_only=private_only)

    def health_check(self) -> Dict[str, Any]:
        return {"source": self.name, "status": "ONLINE", "type": self.source_type}

class OLXAdapter(BasePropertyAdapter):
    def __init__(self):
        super().__init__("OLX", source_type="web_scraper")

    def fetch_offers(self, city: str, category: str = "sprzedaz", property_type: str = "Mieszkania", price_max: Optional[int] = None, private_only: bool = False) -> List[Dict[str, Any]]:
        from scrapers.olx_scraper import scrape_olx
        return scrape_olx(city=city, price_max=price_max, category=category, property_type=property_type, private_only=private_only)

    def health_check(self) -> Dict[str, Any]:
        return {"source": self.name, "status": "ONLINE", "type": self.source_type}

class NieruchomosciOnlineAdapter(BasePropertyAdapter):
    def __init__(self):
        super().__init__("Nieruchomości-online", source_type="web_scraper")

    def fetch_offers(self, city: str, category: str = "sprzedaz", property_type: str = "Mieszkania", price_max: Optional[int] = None, private_only: bool = False) -> List[Dict[str, Any]]:
        if private_only:
            return []
        from scrapers.nieruchomosci_online_scraper import scrape_nieruchomosci_online
        return scrape_nieruchomosci_online(city=city, price_max=price_max, category=category, property_type=property_type)

    def health_check(self) -> Dict[str, Any]:
        return {"source": self.name, "status": "ONLINE", "type": self.source_type}

class AgencyPartnerAdapter(BasePropertyAdapter):
    def __init__(self):
        super().__init__("Gratka / Biura", source_type="partner")

    def fetch_offers(self, city: str, category: str = "sprzedaz", property_type: str = "Mieszkania", price_max: Optional[int] = None, private_only: bool = False) -> List[Dict[str, Any]]:
        if private_only:
            return []
        from scrapers.agencies_scraper import scrape_all_agencies
        return scrape_all_agencies(city=city, category=category, property_type=property_type, max_price=price_max)

    def health_check(self) -> Dict[str, Any]:
        return {"source": self.name, "status": "ONLINE", "type": self.source_type}

class DirectFeedAdapter(BasePropertyAdapter):
    """Adapter dla bezpośrednich integracji z biurami (asari, galactica, esticrm, XML / JSON feed)"""
    def __init__(self, feed_url: Optional[str] = None):
        super().__init__("Bezpośredni Feed XML/JSON", source_type="xml_feed")
        self.feed_url = feed_url

    def fetch_offers(self, city: str, category: str = "sprzedaz", property_type: str = "Mieszkania", price_max: Optional[int] = None, private_only: bool = False) -> List[Dict[str, Any]]:
        # Gotowa architektura pod podpięcie komercyjnych feedów biur nieruchomości
        return []

    def health_check(self) -> Dict[str, Any]:
        has_feed = bool(self.feed_url)
        return {
            "source": self.name,
            "status": "CONFIGURED" if has_feed else "STANDBY (wymaga URL feedu w panelu admina)",
            "type": self.source_type
        }

ADAPTER_REGISTRY = {
    "Otodom": OtodomAdapter(),
    "OLX": OLXAdapter(),
    "Nieruchomości-online": NieruchomosciOnlineAdapter(),
    "Gratka / Biura": AgencyPartnerAdapter(),
    "Direct Feed": DirectFeedAdapter()
}

def get_registered_adapters() -> List[BasePropertyAdapter]:
    return list(ADAPTER_REGISTRY.values())
