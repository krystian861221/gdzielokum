"""
Moduł bazy kancelarii notarialnych w Polsce oraz kalkulator taksy notarialnej.
"""

from typing import List, Dict, Any, Optional

NOTARY_OFFICES = [
    # WROCŁAW
    {
        "id": "wro_1",
        "city": "Wrocław",
        "name": "Kancelaria Notarialna Dorota Czura & Maciej Ziemiański",
        "notaries": "not. Dorota Czura, not. Maciej Ziemiański",
        "address": "ul. Ruska 51B / 10, 50-079 Wrocław (Stare Miasto)",
        "phone": "+48 71 344 22 55",
        "email": "kancelaria@ruska.notariat.wroc.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 5.0,
        "reviews_count": 86,
        "specialization": "Transakcje deweloperskie, umowy sprzedaży mieszkań, darowizny"
    },
    {
        "id": "wro_2",
        "city": "Wrocław",
        "name": "Kancelaria Notarialna Karolina Szymańska",
        "notaries": "not. Karolina Szymańska",
        "address": "ul. Powstańców Śląskich 28/30 (Sky Tower), 53-333 Wrocław",
        "phone": "+48 71 780 12 34",
        "email": "kontakt@notariusz-skytower.pl",
        "hours": "Pn - Pt: 08:30 - 18:00 (sobota na życzenie)",
        "rating": 4.9,
        "reviews_count": 112,
        "specialization": "Umowy kredytowe z hipoteką, rynek wtórny, pełnomocnictwa"
    },
    {
        "id": "wro_3",
        "city": "Wrocław",
        "name": "Kancelaria Notarialna Rynek — Notariusz Paweł Kowalczyk",
        "notaries": "not. Paweł Kowalczyk",
        "address": "Rynek 7/8, 50-106 Wrocław",
        "phone": "+48 71 341 80 90",
        "email": "biuro@notariusz-rynek.wroclaw.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 4.9,
        "reviews_count": 94,
        "specialization": "Akty notarialne sprzedaży lokali, zniesienie współwłasności"
    },

    # WARSZAWA
    {
        "id": "waw_1",
        "city": "Warszawa",
        "name": "Kancelaria Notarialna Centrum — Joanna Wróblewska & Michał Adamczyk",
        "notaries": "not. Joanna Wróblewska, not. Michał Adamczyk",
        "address": "ul. Marszałkowska 84/92 m. 11, 00-514 Warszawa",
        "phone": "+48 22 628 40 50",
        "email": "kancelaria@notariuszmarszalkowska.pl",
        "hours": "Pn - Pt: 08:30 - 18:00",
        "rating": 5.0,
        "reviews_count": 140,
        "specialization": "Sprzedaż lokali, umowy deweloperskie, obsługa inwestorów"
    },
    {
        "id": "waw_2",
        "city": "Warszawa",
        "name": "Kancelaria Notarialna Mokotów — Notariusz Tomasz Lis",
        "notaries": "not. Tomasz Lis",
        "address": "ul. Puławska 45, 02-508 Warszawa (Mokotów)",
        "phone": "+48 22 849 10 20",
        "email": "kancelaria@notariusz-mokotow.pl",
        "hours": "Pn - Pt: 09:00 - 17:30",
        "rating": 4.9,
        "reviews_count": 98,
        "specialization": "Kredyty hipoteczne, rynek pierwotny i wtórny, testamenty"
    },
    {
        "id": "waw_3",
        "city": "Warszawa",
        "name": "Kancelaria Notarialna Wola — Notariusz Magdalena Zielińska",
        "notaries": "not. Magdalena Zielińska",
        "address": "al. Jana Pawła II 27, 00-867 Warszawa (Wola)",
        "phone": "+48 22 400 33 22",
        "email": "zielinska@notariat-wola.pl",
        "hours": "Pn - Pt: 09:00 - 18:00",
        "rating": 4.9,
        "reviews_count": 125,
        "specialization": "Sprawna obsługa flipperów i biur nieruchomości, szybkie terminy"
    },

    # KRAKÓW
    {
        "id": "krk_1",
        "city": "Kraków",
        "name": "Kancelaria Notarialna Stare Miasto — Notariusz Piotr Wójcik",
        "notaries": "not. Piotr Wójcik",
        "address": "ul. Karmelicka 16/4, 31-131 Kraków",
        "phone": "+48 12 422 15 30",
        "email": "kontakt@notariuszkarmelicka.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 5.0,
        "reviews_count": 110,
        "specialization": "Zakup mieszkań zabytkowych, rynek wtórny, intercyzy"
    },
    {
        "id": "krk_2",
        "city": "Kraków",
        "name": "Kancelaria Notarialna Grzegórzki — Notariusz Ewa Dąbrowska",
        "notaries": "not. Ewa Dąbrowska",
        "address": "al. Pokoju 1A, 31-548 Kraków",
        "phone": "+48 12 300 70 80",
        "email": "kancelaria@notariusz-grzegorzki.pl",
        "hours": "Pn - Pt: 08:30 - 17:30",
        "rating": 4.8,
        "reviews_count": 76,
        "specialization": "Inwestycje deweloperskie, umowy najmu okazjonalnego"
    },

    # POZNAŃ
    {
        "id": "poz_1",
        "city": "Poznań",
        "name": "Kancelaria Notarialna Garbary — Notariusz Andrzej Nowicki",
        "notaries": "not. Andrzej Nowicki",
        "address": "ul. Garbary 45/3, 61-869 Poznań",
        "phone": "+48 61 852 30 40",
        "email": "biuro@notariuszgarbary.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 4.9,
        "reviews_count": 92,
        "specialization": "Sprzedaż nieruchomości, wpisy do ksiąg wieczystych"
    },
    {
        "id": "poz_2",
        "city": "Poznań",
        "name": "Kancelaria Notarialna Jeżyce — Notariusz Katarzyna Kaczmarek",
        "notaries": "not. Katarzyna Kaczmarek",
        "address": "ul. Dąbrowskiego 75, 60-523 Poznań",
        "phone": "+48 61 661 22 11",
        "email": "kontakt@notariuszjezyce.pl",
        "hours": "Pn - Pt: 08:30 - 17:00",
        "rating": 4.9,
        "reviews_count": 83,
        "specialization": "Umowy przedwstępne, podziały majątku, hipoteki"
    },

    # GDAŃSK
    {
        "id": "gda_1",
        "city": "Gdańsk",
        "name": "Kancelaria Notarialna Wrzeszcz — Notariusz Grzegorz Lewicki",
        "notaries": "not. Grzegorz Lewicki",
        "address": "al. Grunwaldzka 102/2, 80-244 Gdańsk (Wrzeszcz)",
        "phone": "+48 58 344 50 60",
        "email": "kancelaria@notariuszgrunwaldzka.pl",
        "hours": "Pn - Pt: 09:00 - 17:30",
        "rating": 5.0,
        "reviews_count": 105,
        "specialization": "Apartamenty nadmorskie, rynek wtórny Trójmiasto, darowizny"
    },
    {
        "id": "gda_2",
        "city": "Gdańsk",
        "name": "Kancelaria Notarialna Śródmieście — Notariusz Anna Majewska",
        "notaries": "not. Anna Majewska",
        "address": "ul. Długa 12/14, 80-827 Gdańsk",
        "phone": "+48 58 301 22 33",
        "email": "kontakt@notariusz-gdansk.com.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 4.8,
        "reviews_count": 69,
        "specialization": "Obsługa transakcji gotówkowych i kredytowych"
    },

    # LUBIN
    {
        "id": "lub_1",
        "city": "Lubin",
        "name": "Kancelaria Notarialna Notariusz Beata Woźniak",
        "notaries": "not. Beata Woźniak",
        "address": "ul. Odrodzenia 14, 59-300 Lubin (Centrum)",
        "phone": "+48 76 846 20 30",
        "email": "kancelaria@notariusz-lubin.pl",
        "hours": "Pn - Pt: 09:00 - 16:30",
        "rating": 4.9,
        "reviews_count": 58,
        "specialization": "Sprzedaż mieszkań i domów w Zagłębiu Miedziowym, obsługa KGHM"
    },
    {
        "id": "lub_2",
        "city": "Lubin",
        "name": "Kancelaria Notarialna Notariusz Mariusz Kruk",
        "notaries": "not. Mariusz Kruk",
        "address": "ul. Mieszka I 3, 59-300 Lubin",
        "phone": "+48 76 844 55 11",
        "email": "m.kruk@notariat.lubin.pl",
        "hours": "Pn - Pt: 08:30 - 16:00",
        "rating": 4.8,
        "reviews_count": 42,
        "specialization": "Spadki, darowizny, umowy deweloperskie i kredyty"
    },

    # JELENIA GÓRA
    {
        "id": "jg_1",
        "city": "Jelenia Góra",
        "name": "Kancelaria Notarialna Notariusz Krzysztof Jaworski",
        "notaries": "not. Krzysztof Jaworski",
        "address": "ul. Bankowa 8, 58-500 Jelenia Góra",
        "phone": "+48 75 752 40 50",
        "email": "jaworski@notariusz-jg.pl",
        "hours": "Pn - Pt: 09:00 - 16:30",
        "rating": 4.9,
        "reviews_count": 51,
        "specialization": "Działki górskie, apartamenty w Karkonoszach, sprzedaż lokali"
    },

    # KATOWICE
    {
        "id": "kat_1",
        "city": "Katowice",
        "name": "Kancelaria Notarialna Katowice Centrum — Notariusz Adam Baran",
        "notaries": "not. Adam Baran",
        "address": "ul. Warszawska 15, 40-009 Katowice",
        "phone": "+48 32 253 80 90",
        "email": "kontakt@notariusz-katowice.pl",
        "hours": "Pn - Pt: 08:30 - 17:30",
        "rating": 4.9,
        "reviews_count": 89,
        "specialization": "Rynek pierwotny i wtórny na Śląsku, umowy spółek, hipoteki"
    },

    # ŁÓDŹ
    {
        "id": "lod_1",
        "city": "Łódź",
        "name": "Kancelaria Notarialna Piotrkowska — Notariusz Monika Błaszczyk",
        "notaries": "not. Monika Błaszczyk",
        "address": "ul. Piotrkowska 112 m. 6, 90-006 Łódź",
        "phone": "+48 42 630 11 22",
        "email": "kancelaria@notariusz-piotrkowska.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 4.9,
        "reviews_count": 78,
        "specialization": "Rewitalizowane kamienice, mieszkania deweloperskie, najem okazjonalny"
    },

    # SZCZECIN
    {
        "id": "szc_1",
        "city": "Szczecin",
        "name": "Kancelaria Notarialna Notariusz Jakub Kamiński",
        "notaries": "not. Jakub Kamiński",
        "address": "al. Niepodległości 22, 70-412 Szczecin",
        "phone": "+48 91 433 20 10",
        "email": "kaminski@notariusz-szczecin.pl",
        "hours": "Pn - Pt: 08:30 - 16:30",
        "rating": 4.8,
        "reviews_count": 65,
        "specialization": "Umowy kupna-sprzedaży, hipoteki bankowe, pełnomocnictwa"
    },

    # LUBLIN
    {
        "id": "lubl_1",
        "city": "Lublin",
        "name": "Kancelaria Notarialna Krakowskie Przedmieście — Notariusz Ewelina Gajewska",
        "notaries": "not. Ewelina Gajewska",
        "address": "Krakowskie Przedmieście 42/5, 20-002 Lublin",
        "phone": "+48 81 532 10 20",
        "email": "kontakt@notariusz-lublin.com",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 5.0,
        "reviews_count": 72,
        "specialization": "Transakcje mieszkaniowe, działki budowlane, rynek pierwotny"
    },

    # BYDGOSZCZ
    {
        "id": "byd_1",
        "city": "Bydgoszcz",
        "name": "Kancelaria Notarialna Notariusz Jarosław Sokołowski",
        "notaries": "not. Jarosław Sokołowski",
        "address": "ul. Gdańska 34, 85-006 Bydgoszcz",
        "phone": "+48 52 321 40 50",
        "email": "biuro@notariusz-bydgoszcz.pl",
        "hours": "Pn - Pt: 09:00 - 16:30",
        "rating": 4.8,
        "reviews_count": 59,
        "specialization": "Nieruchomości mieszkalne, darowizny, umowy deweloperskie"
    },

    # RZESZÓW
    {
        "id": "rze_1",
        "city": "Rzeszów",
        "name": "Kancelaria Notarialna Notariusz Rafał Cieślak",
        "notaries": "not. Rafał Cieślak",
        "address": "ul. 3 Maja 14/2, 35-030 Rzeszów",
        "phone": "+48 17 852 30 10",
        "email": "kancelaria@notariusz-rzeszow.pl",
        "hours": "Pn - Pt: 09:00 - 17:00",
        "rating": 4.9,
        "reviews_count": 64,
        "specialization": "Zakup lokali, domów, kredyty hipoteczne podkarpackie"
    }
]

def get_notary_offices(city: Optional[str] = None, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Filtruje listę kancelarii notarialnych wg miasta oraz frazy wyszukiwania.
    Jeśli w danym mieście brak wyników, zwraca wszystkie z zaznaczeniem ogólnopolskim.
    """
    results = NOTARY_OFFICES
    if city and city.strip():
        city_clean = city.lower().strip()
        filtered = [n for n in results if n["city"].lower() in city_clean or city_clean in n["city"].lower()]
        if filtered:
            results = filtered
    
    if search_query and search_query.strip():
        q = search_query.lower().strip()
        results = [
            n for n in results
            if q in n["name"].lower()
            or q in n["notaries"].lower()
            or q in n["address"].lower()
            or q in n["city"].lower()
            or q in n.get("specialization", "").lower()
        ]
    return results

def calculate_max_notary_fee(property_value: float) -> Dict[str, float]:
    """
    Oblicza maksymalną taksę notarialną wg Rozporządzenia Ministra Sprawiedliwości
    w sprawie maksymalnych stawek taksy notarialnej.
    """
    v = max(0.0, float(property_value))
    if v <= 3000:
        base = 100.0
    elif v <= 10000:
        base = 100.0 + (v - 3000) * 0.03
    elif v <= 30000:
        base = 310.0 + (v - 10000) * 0.02
    elif v <= 60000:
        base = 710.0 + (v - 30000) * 0.01
    elif v <= 1000000:
        base = 710.0 + 300.0 + (v - 60000) * 0.004 # 1010 zł + 0.4%
    elif v <= 2000000:
        base = 4770.0 + (v - 1000000) * 0.002
    else:
        base = min(10000.0, 6770.0 + (v - 2000000) * 0.0025)
    
    vat = round(base * 0.23, 2)
    total = round(base + vat, 2)
    return {
        "net_fee": round(base, 2),
        "vat": vat,
        "gross_fee": total
    }
