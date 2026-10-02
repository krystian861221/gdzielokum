"""
Moduł bazy ogłoszeń syndyków, licytacji komorniczych i przetargów nieruchomości.
Zawiera podgląd danych Ksiąg Wieczystych (KW), harmonogramy, terminy wadium i licytacji,
sygnatury akt oraz kalkulacje dyskonta dla inwestorów.
"""

from typing import List, Dict, Any, Optional

AUCTION_DEALS = [
    # WROCŁAW
    {
        "id": "auc_wro_01",
        "title": "3-pokojowe mieszkanie 64.2 m² z balkonem — Wrocław Krzyki",
        "city": "Wrocław",
        "district": "Krzyki",
        "address": "ul. Powstańców Śląskich 112/18, 53-333 Wrocław",
        "category": "Licytacja komornicza (I termin)",
        "source_name": "Portal Licytacji Komorniczych (Krajowa Rada Komornicza)",
        "source_url": "https://licytacje.komornik.pl/Notice/Details/612984",
        "case_signature": "Km 842/25",
        "court": "Sąd Rejonowy dla Wrocławia-Krzyków, I Wydział Cywilny",
        "organ_name": "Komornik Sądowy przy Sądzie Rejonowym dla Wrocławia-Krzyków Tomasz Nowak",
        "organ_phone": "+48 71 345 88 12",
        "organ_email": "wroclaw.nowak@komornik.pl",
        "market_val": 640000,
        "starting_price": 480000, # 3/4 sumy oszacowania
        "discount_pct": 25.0,
        "deposit_amount": 64000, # 10%
        "deposit_bank_account": "PL 45 1020 5226 0000 6702 0184 9911 PKO BP",
        "deposit_deadline": "2026-10-20 (do godz. 15:00)",
        "auction_date": "2026-10-22, godz. 10:00",
        "auction_location": "Sąd Rejonowy dla Wrocławia-Krzyków, ul. Podwale 30, Sala 114 (lub E-licytacje)",
        "inspection_date": "2026-10-15 w godz. 12:00 - 13:00",
        "area_m2": 64.2,
        "rooms": 3,
        "floor": 3,
        "kw_number": "WR1K/00284912/4",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny nr 18 o pow. 64.20 m², 3 pokoje, kuchnia, przedpokój, łazienka, WC. Piwnica 4.10 m².",
            "section_2": "Własność: udział 1/1 wpisany na dłużnika.",
            "section_3": "Wpis ostrzeżenia o wszczęciu egzekucji z nieruchomości w sprawie Km 842/25. Brak służebności osobistych i dożywocia.",
            "section_4": "Hipoteka umowna kaucyjna 520 000 zł na rzecz Banku. UWAGA: Zgodnie z art. 1000 Kpc hipoteki wygasają z mocy prawa po prawomocnym przysądzeniu własności!"
        },
        "description": "Lokal w dobrym stanie technicznym, ogrzewanie miejskie, instalacja miedziana, okna PCV. Wycena z operatu biegłego sądowego z sierpnia 2026 r."
    },
    {
        "id": "auc_wro_02",
        "title": "Apartament 2-pokojowy 48.5 m² — Wrocław Fabryczna (II TERMIN -33.3%)",
        "city": "Wrocław",
        "district": "Fabryczna",
        "address": "ul. Braniborska 44/22, 53-680 Wrocław",
        "category": "Licytacja komornicza (II termin)",
        "source_name": "Portal Licytacji Elektronicznych Komorników",
        "source_url": "https://elicytacje.komornik.pl/obwieszczenie/914820",
        "case_signature": "Km 1104/24",
        "court": "Sąd Rejonowy dla Wrocławia-Fabrycznej",
        "organ_name": "Komornik Sądowy Michał Wieczorek",
        "organ_phone": "+48 71 789 44 20",
        "organ_email": "kontakt@komornik-fabryczna.pl",
        "market_val": 520000,
        "starting_price": 346666, # 2/3 sumy oszacowania
        "discount_pct": 33.3,
        "deposit_amount": 52000,
        "deposit_bank_account": "PL 89 1090 2398 0000 0001 3491 5562 Santander Bank",
        "deposit_deadline": "2026-10-27 (do godz. 23:59 przez portal e-licytacji)",
        "auction_date": "2026-10-29, godz. 11:30",
        "auction_location": "Portal E-Licytacje (aukcja w 100% elektroniczna online)",
        "inspection_date": "2026-10-21 w godz. 14:00 - 15:00",
        "area_m2": 48.5,
        "rooms": 2,
        "floor": 2,
        "kw_number": "WR1K/00341908/7",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 48.50 m², 2 pokoje, aneks kuchenny, balkon 5.2 m².",
            "section_2": "Własność: 1/1.",
            "section_3": "Wpis egzekucyjny Km 1104/24. Czysty stan roszczeń osób trzecich.",
            "section_4": "Hipoteka przymusowa ZUS oraz bankowa. Wygasają w całości z podziału sumy uzyskanej z egzekucji."
        },
        "description": "Ogromna okazja dla inwestora: II termin licytacji z ceną wywołania zaledwie 346 666 zł (7 147 zł/m² w centrum Wrocławia!)."
    },
    {
        "id": "auc_wro_03",
        "title": "Sprzedaż z masy upadłości: Mieszkanie 78 m² — Syndyk Masy Upadłości",
        "city": "Wrocław",
        "district": "Śródmieście",
        "address": "ul. Sienkiewicza 88/6, 50-348 Wrocław",
        "category": "Przetarg syndyka (Masa upadłości KRZ)",
        "source_name": "Krajowy Rejestr Zadłużonych (KRZ) / MSiG",
        "source_url": "https://krz.ms.gov.pl/obwieszczenia/syndyk/wroclaw-sienkiewicza",
        "case_signature": "VIII GUp 219/25",
        "court": "Sąd Rejonowy dla Wrocławia-Fabrycznej, VIII Wydział Gospodarczy ds. Upadłościowych",
        "organ_name": "Syndyk Masy Upadłości dr Paweł Adamski",
        "organ_phone": "+48 71 322 10 90",
        "organ_email": "syndyk.adamski@kancelaria-upadlosci.pl",
        "market_val": 780000,
        "starting_price": 490000, # -37%
        "discount_pct": 37.2,
        "deposit_amount": 50000,
        "deposit_bank_account": "PL 12 1050 1575 1000 0090 3122 8841 ING Bank Śląski",
        "deposit_deadline": "2026-11-04 (wpływ na rachunek masy upadłości)",
        "auction_date": "2026-11-06, godz. 12:00 (otwarcie ofert pisemnych)",
        "auction_location": "Kancelaria Syndyka, ul. Szewska 19, Wrocław",
        "inspection_date": "2026-10-28 w godz. 10:00 - 12:00 po uprzednim zgłoszeniu",
        "area_m2": 78.0,
        "rooms": 4,
        "floor": 1,
        "kw_number": "WR1K/00192834/1",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 78.00 m², wysokie sufity 3.20m, zabytkowa kamienica po remoncie dachu.",
            "section_2": "Upadły (osoba fizyczna nieprowadząca działalności gospodarczej).",
            "section_3": "Wpis ogłoszenia upadłości. Art. 313 Prawa Upadłościowego: sprzedaż przez syndyka ma skutki sprzedaży egzekucyjnej – nabywca nabywa lokal wolny od obciążeń!",
            "section_4": "Wszystkie hipoteki zostają wykreślone na wniosek syndyka na koszt masy upadłości."
        },
        "description": "Idealne pod podział na 2 mniejsze lokale lub wynajem na pokoje (ROI szacowane na >10% netto). Pełne bezpieczeństwo zakupu od syndyka."
    },

    # WARSZAWA
    {
        "id": "auc_waw_01",
        "title": "Lokal mieszkalny 52 m² — Warszawa Mokotów (I Licytacja)",
        "city": "Warszawa",
        "district": "Mokotów",
        "address": "ul. Domaniewska 31/45, 02-672 Warszawa",
        "category": "Licytacja komornicza (I termin)",
        "source_name": "Portal Licytacji Komorniczych KRK",
        "source_url": "https://licytacje.komornik.pl/Notice/Details/619842",
        "case_signature": "Km 412/25",
        "court": "Sąd Rejonowy dla Warszawy-Mokotowa",
        "organ_name": "Komornik Sądowy Grzegorz Kozłowski",
        "organ_phone": "+48 22 843 20 10",
        "organ_email": "warszawa.mokotow@komornik.pl",
        "market_val": 820000,
        "starting_price": 615000, # 3/4
        "discount_pct": 25.0,
        "deposit_amount": 82000,
        "deposit_bank_account": "PL 32 1240 1037 1111 0010 4912 7788 Bank Pekao S.A.",
        "deposit_deadline": "2026-10-23 do godz. 16:00",
        "auction_date": "2026-10-26, godz. 09:30",
        "auction_location": "Sąd Rejonowy dla Warszawy-Mokotowa, ul. Ogrodowa 51A, Sala 208",
        "inspection_date": "2026-10-16 w godz. 11:00 - 12:00",
        "area_m2": 52.0,
        "rooms": 2,
        "floor": 4,
        "kw_number": "WA2M/00481920/3",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal 52 m², salon z aneksem, sypialnia, balkon.",
            "section_2": "Własność: 1/1 dłużnik.",
            "section_3": "Egzekucja komornicza. Brak lokatorów i praw dożywocia.",
            "section_4": "Dwie hipoteki bankowe wygasające na podstawie prawomocnego planu podziału sumy egzekucyjnej."
        },
        "description": "Blisko stacji Metro Wilanowska i Galerii Mokotów. Bardzo wysoki potencjał płynności i najmu długoterminowego."
    },
    {
        "id": "auc_waw_02",
        "title": "Przetarg Syndyka: Apartament 89 m² — Warszawa Wola (Nowe Budownictwo)",
        "city": "Warszawa",
        "district": "Wola",
        "address": "ul. Siedmiogrodzka 1/82, 01-204 Warszawa",
        "category": "Przetarg syndyka (Masa upadłości KRZ)",
        "source_name": "Krajowy Rejestr Zadłużonych (KRZ)",
        "source_url": "https://krz.ms.gov.pl/przetargi/nieruchomosci/waw-wola-89m",
        "case_signature": "XIX GUp 580/24",
        "court": "Sąd Rejonowy dla m.st. Warszawy w Warszawie, XIX Wydział Gospodarczy",
        "organ_name": "Syndyk Masy Upadłości Krzysztof Piotrowski",
        "organ_phone": "+48 22 620 90 80",
        "organ_email": "syndyk@piotrowski-upadlosci.pl",
        "market_val": 1550000,
        "starting_price": 990000, # -36%
        "discount_pct": 36.1,
        "deposit_amount": 100000,
        "deposit_bank_account": "PL 60 1090 1014 0000 0001 4410 8821 Santander Bank",
        "deposit_deadline": "2026-11-10 do godz. 15:00",
        "auction_date": "2026-11-12, godz. 11:00 (konkurs ofert pisemnych)",
        "auction_location": "Siedziba Syndyka, ul. Grzybowska 4, Warszawa",
        "inspection_date": "2026-11-03 w godz. 13:00 - 15:00",
        "area_m2": 89.0,
        "rooms": 3,
        "floor": 6,
        "kw_number": "WA4M/00512839/9",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Apartament 89 m², klimatyzacja, taras 14 m², 2 miejsca postojowe w garażu podziemnym.",
            "section_2": "Wpis upadłości konsumenckiej.",
            "section_3": "Sprzedaż ze skutkiem pierwotnym (nabycie bez jakichkolwiek długów).",
            "section_4": "Wszystkie hipoteki bankowe podlegają bezwzględnemu wykreśleniu z urzędu po planie podziału."
        },
        "description": "Luksusowy budynek z ochroną 24h, 300 m od stacji Metro Rondo Daszyńskiego. Ponad 550 000 zł zysku względem wyceny biegłego rzeczoznawcy!"
    },

    # KRAKÓW
    {
        "id": "auc_krk_01",
        "title": "Mieszkanie 41.5 m² — Kraków Krowodrza (Licytacja Komornicza II Termin)",
        "city": "Kraków",
        "district": "Krowodrza",
        "address": "ul. Kazimierza Wielkiego 40/12, 30-074 Kraków",
        "category": "Licytacja komornicza (II termin)",
        "source_name": "Portal Licytacji Komorniczych KRK",
        "source_url": "https://licytacje.komornik.pl/Notice/Details/623190",
        "case_signature": "Km 670/25",
        "court": "Sąd Rejonowy dla Krakowa-Krowodrzy",
        "organ_name": "Komornik Sądowy Piotr Stankiewicz",
        "organ_phone": "+48 12 633 40 50",
        "organ_email": "krowodrza.komornik@krakow.pl",
        "market_val": 490000,
        "starting_price": 326666, # 2/3
        "discount_pct": 33.3,
        "deposit_amount": 49000,
        "deposit_bank_account": "PL 19 1020 2892 0000 5402 0192 4811 PKO BP",
        "deposit_deadline": "2026-10-28 do godz. 14:00",
        "auction_date": "2026-10-30, godz. 10:00",
        "auction_location": "Sąd Rejonowy dla Krakowa-Krowodrzy, ul. Przy Rondzie 7, Sala K-12",
        "inspection_date": "2026-10-22 w godz. 15:00 - 16:00",
        "area_m2": 41.5,
        "rooms": 2,
        "floor": 1,
        "kw_number": "KR1P/00389102/5",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 41.5 m², 2 pokoje, oddzielna jasna kuchnia, piwnica 3 m².",
            "section_2": "Własność dłużnika.",
            "section_3": "Ostrzeżenie o egzekucji. Czysty stan prawny pod kątem praw osób trzecich.",
            "section_4": "Hipoteka bankowa – wygasa z prawomocnym przysądzeniem własności."
        },
        "description": "Świetna lokalizacja pod wynajem dla studentów AGH/UJ lub pracowników korporacji. Wyjątkowo niska cena wywoławcza: 7 871 zł/m²!"
    },

    # POZNAŃ
    {
        "id": "auc_poz_01",
        "title": "Mieszkanie 58 m² — Poznań Grunwald (Licytacja Elektroniczna I Termin)",
        "city": "Poznań",
        "district": "Grunwald",
        "address": "ul. Promienista 82/15, 60-288 Poznań",
        "category": "Licytacja komornicza (I termin)",
        "source_name": "Krajowa Rada Komornicza E-Licytacje",
        "source_url": "https://elicytacje.komornik.pl/obwieszczenie/882190",
        "case_signature": "Km 340/25",
        "court": "Sąd Rejonowy Poznań-Grunwald i Jeżyce",
        "organ_name": "Komornik Sądowy Maciej Wolski",
        "organ_phone": "+48 61 867 20 30",
        "organ_email": "poznan.wolski@komornik.pl",
        "market_val": 510000,
        "starting_price": 382500, # 3/4
        "discount_pct": 25.0,
        "deposit_amount": 51000,
        "deposit_bank_account": "PL 44 1090 1362 0000 0000 3602 9102 Santander Bank",
        "deposit_deadline": "2026-11-03 przez system e-licytacje",
        "auction_date": "2026-11-05, godz. 12:00",
        "auction_location": "System teleinformatyczny E-Licytacje (licytacja zdalna online)",
        "inspection_date": "2026-10-27 w godz. 12:00 - 13:00",
        "area_m2": 58.0,
        "rooms": 3,
        "floor": 3,
        "kw_number": "PO1P/00234190/2",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 58.00 m², 3 pokoje rozkładowe, balkon loggia.",
            "section_2": "Własność: udział 1/1.",
            "section_3": "Wpis egzekucji Km 340/25. Brak praw rzeczowych ograniczonych.",
            "section_4": "Wygasające hipoteki po zatwierdzeniu planu podziału sumy."
        },
        "description": "Mieszkanie w zadbanym bloku po termomodernizacji, idealne na flipa lub gotowiec inwestycyjny na pokoje."
    },

    # GDAŃSK
    {
        "id": "auc_gda_01",
        "title": "Apartament 65 m² z widokiem — Gdańsk Przymorze (Przetarg Spółdzielczy)",
        "city": "Gdańsk",
        "district": "Przymorze",
        "address": "ul. Obrońców Wybrzeża 15/48, 80-398 Gdańsk",
        "category": "Przetarg miejski / spółdzielczy",
        "source_name": "Przetarg Spółdzielni Mieszkaniowej Przymorze",
        "source_url": "https://przetargi.smprzymorze.gda.pl/ogloszenie/48",
        "case_signature": "Przetarg ZP-14/2026",
        "court": "Spółdzielnia Mieszkaniowa Przymorze w Gdańsku",
        "organ_name": "Zarząd SM Przymorze / Dział Członkowsko-Mieszkaniowy",
        "organ_phone": "+48 58 556 12 34",
        "organ_email": "przetargi@smprzymorze.gda.pl",
        "market_val": 790000,
        "starting_price": 580000, # -26.5%
        "discount_pct": 26.6,
        "deposit_amount": 58000,
        "deposit_bank_account": "PL 11 1020 1811 0000 0102 0014 9920 PKO BP",
        "deposit_deadline": "2026-11-09 do godz. 12:00",
        "auction_date": "2026-11-12, godz. 10:00 (licytacja ustna w siedzibie SM)",
        "auction_location": "Siedziba SM Przymorze, ul. Śląska 35, Sala Konferencyjna",
        "inspection_date": "2026-11-04 w godz. 14:00 - 16:00",
        "area_m2": 65.0,
        "rooms": 3,
        "floor": 7,
        "kw_number": "GD1G/00349012/8",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Spółdzielcze własnościowe prawo do lokalu (z założoną KW), 65 m², balkon, piwnica.",
            "section_2": "Spółdzielnia Mieszkaniowa (z prawem ustanowienia odrębnej własności).",
            "section_3": "Czyste – lokal opróżniony z osób i rzeczy, gotowy do natychmiastowego objęcia.",
            "section_4": "Brak wpisów hipotek! Czysta księga wieczysta bez jakichkolwiek roszczeń."
        },
        "description": "Lokal opróżniony, brak dłużników, natychmiastowe wydanie kluczy po przetargu i wpłacie ceny. 1 km od plaży w Jelitkowie!"
    },

    # LUBIN
    {
        "id": "auc_lub_01",
        "title": "Mieszkanie 51.2 m² — Lubin Centrum (I Licytacja Komornicza -25%)",
        "city": "Lubin",
        "district": "Centrum",
        "address": "ul. Bolesława Chrobrego 14/8, 59-300 Lubin",
        "category": "Licytacja komornicza (I termin)",
        "source_name": "Portal Licytacji Komorniczych KRK",
        "source_url": "https://licytacje.komornik.pl/Notice/Details/610429",
        "case_signature": "Km 290/25",
        "court": "Sąd Rejonowy w Lubinie, I Wydział Cywilny",
        "organ_name": "Komornik Sądowy przy Sądzie Rejonowym w Lubinie Dariusz Zając",
        "organ_phone": "+48 76 846 11 90",
        "organ_email": "lubin.zajac@komornik.pl",
        "market_val": 310000,
        "starting_price": 232500, # 3/4
        "discount_pct": 25.0,
        "deposit_amount": 31000,
        "deposit_bank_account": "PL 72 1090 2082 0000 0005 4601 2289 Santander Bank",
        "deposit_deadline": "2026-10-21 do godz. 15:00",
        "auction_date": "2026-10-23, godz. 11:00",
        "auction_location": "Sąd Rejonowy w Lubinie, ul. Wrocławska 3, Sala 102",
        "inspection_date": "2026-10-14 w godz. 13:00 - 14:00",
        "area_m2": 51.2,
        "rooms": 2,
        "floor": 2,
        "kw_number": "LE1U/00049210/6",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 51.20 m², 2 pokoje, balkon, piwnica 3.4 m².",
            "section_2": "Własność: 1/1.",
            "section_3": "Wpis wszczęcia egzekucji Km 290/25.",
            "section_4": "Wygasające hipoteki bankowe."
        },
        "description": "Tanie mieszkanie w Zagłębiu Miedziowym z wysoką stopą zwrotu z najmu pracowniczego dla KGHM i podwykonawców."
    },

    # JELENIA GÓRA
    {
        "id": "auc_jg_01",
        "title": "Apartament turystyczny 55 m² — Jelenia Góra / Cieplice (Przetarg Syndyka)",
        "city": "Jelenia Góra",
        "district": "Cieplice Zdrój",
        "address": "ul. Cervi 12/4, 58-560 Jelenia Góra",
        "category": "Przetarg syndyka (Masa upadłości KRZ)",
        "source_name": "Krajowy Rejestr Zadłużonych (KRZ)",
        "source_url": "https://krz.ms.gov.pl/ogloszenia/syndyk-cieplice-55m",
        "case_signature": "V GUp 92/25",
        "court": "Sąd Rejonowy w Jeleniej Górze, V Wydział Gospodarczy",
        "organ_name": "Syndyk Masy Upadłości Andrzej Marczak",
        "organ_phone": "+48 75 753 22 10",
        "organ_email": "kontakt@syndyk-karkonosze.pl",
        "market_val": 460000,
        "starting_price": 285000, # -38%
        "discount_pct": 38.0,
        "deposit_amount": 30000,
        "deposit_bank_account": "PL 05 1020 2124 0000 8902 0019 3321 PKO BP",
        "deposit_deadline": "2026-11-06 (wpływ na rachunek)",
        "auction_date": "2026-11-10, godz. 12:00",
        "auction_location": "Biuro Syndyka, ul. 1 Maja 30, Jelenia Góra",
        "inspection_date": "2026-10-30 w godz. 11:00 - 13:00",
        "area_m2": 55.0,
        "rooms": 2,
        "floor": 1,
        "kw_number": "JG1J/00078129/3",
        "kw_url": "https://ekw.ms.gov.pl/eukw_ogol/menu.do",
        "kw_details": {
            "section_1": "Lokal mieszkalny 55 m² w uzdrowiskowej części Cieplic, taras z widokiem na Park Zdrojowy.",
            "section_2": "Masa upadłości osoby fizycznej.",
            "section_3": "Sprzedaż w postępowaniu upadłościowym (skutek egzekucyjny – brak obciążeń).",
            "section_4": "Wszystkie hipoteki wygasają z mocy ustawy (art. 313 Prawa Upadłościowego)."
        },
        "description": "Gotowy lokal pod wynajem turystyczny (Booking / Airbnb) w kurorcie Cieplice Zdrój. Cena wywołania poniżej 5 200 zł/m²!"
    }
]

def get_auction_deals(
    city: Optional[str] = None,
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    max_price: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Filtruje listę licytacji, przetargów i ogłoszeń syndyków.
    """
    results = AUCTION_DEALS
    if city and str(city).strip():
        c_clean = str(city).lower().strip()
        filtered = [a for a in results if a["city"].lower() in c_clean or c_clean in a["city"].lower()]
        if filtered:
            results = filtered

    if category and category != "Wszystkie":
        results = [a for a in results if a.get("category") == category]

    if max_price and max_price > 0:
        results = [a for a in results if a.get("starting_price", 0) <= max_price]

    if search_query and str(search_query).strip():
        q = str(search_query).lower().strip()
        results = [
            a for a in results
            if q in a["title"].lower()
            or q in a["address"].lower()
            or q in a["city"].lower()
            or q in a["case_signature"].lower()
            or q in a["kw_number"].lower()
            or q in a.get("description", "").lower()
        ]
    return results
