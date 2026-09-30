from typing import Dict, Any, Optional

def calculate_rental_roi(
    purchase_price: float,
    monthly_rent: Optional[float] = None,
    area: Optional[float] = None,
    renovation_cost: float = 0.0,
    transaction_cost_pct: float = 3.5, # PCC 2% + notariusz/wpisy ~1.5%
    vacancy_months_per_year: float = 0.5,
    maintenance_pct: float = 5.0, # 5% czynszu na naprawy/zarzadzanie
    tax_pct: float = 8.5 # ryczałt 8.5%
) -> Dict[str, Any]:
    """
    Kalkulator Rentowności Najmu (ROI, Cap Rate, Cash Flow).
    Jeśli brak danych o cenie lub metrażu/czynszu, zwraca jawny status 'insufficient_data'.
    """
    if not purchase_price or purchase_price <= 0:
        return {
            "status": "insufficient_data",
            "message": "Brak wystarczających danych do obliczenia (wymagana cena zakupu)."
        }

    # Jeśli nie podano czynszu, szacujemy na bazie powierzchni (standard 50 zł/m2)
    if not monthly_rent or monthly_rent <= 0:
        if area and area > 10:
            monthly_rent = area * 50.0
        else:
            return {
                "status": "insufficient_data",
                "message": "Brak wystarczających danych do obliczenia (podaj miesięczny czynsz lub powierzchnię)."
            }

    tx_costs = purchase_price * (transaction_cost_pct / 100.0)
    total_investment = purchase_price + renovation_cost + tx_costs

    annual_gross_rent = monthly_rent * (12.0 - vacancy_months_per_year)
    maintenance_cost = annual_gross_rent * (maintenance_pct / 100.0)
    tax_cost = annual_gross_rent * (tax_pct / 100.0)
    annual_net_operating_income = annual_gross_rent - maintenance_cost - tax_cost

    roi_gross = (monthly_rent * 12.0 / total_investment) * 100.0
    roi_net = (annual_net_operating_income / total_investment) * 100.0
    monthly_net_cashflow = annual_net_operating_income / 12.0
    payback_years = total_investment / max(1.0, annual_net_operating_income)

    return {
        "status": "calculated",
        "total_investment": round(total_investment, 2),
        "transaction_costs": round(tx_costs, 2),
        "renovation_cost": round(renovation_cost, 2),
        "monthly_rent": round(monthly_rent, 2),
        "annual_gross_rent": round(annual_gross_rent, 2),
        "annual_net_income": round(annual_net_operating_income, 2),
        "monthly_net_cashflow": round(monthly_net_cashflow, 2),
        "roi_gross_pct": round(roi_gross, 2),
        "roi_net_pct": round(roi_net, 2),
        "payback_years": round(payback_years, 1)
    }

def calculate_flip_profit(
    purchase_price: float,
    area: float,
    renovation_standard: str = "Standard", # "Odświeżenie", "Standard", "Wysoki standard"
    arv_markup_pct: float = 25.0, # Szacowany wzrost wartości po remoncie
    transaction_cost_pct: float = 3.5,
    agency_selling_fee_pct: float = 2.0,
    holding_months: int = 4
) -> Dict[str, Any]:
    """
    Kalkulator inwestycji typu FLIP (zakup, remont, sprzedaż z zyskiem).
    """
    if not purchase_price or purchase_price <= 0 or not area or area <= 0:
        return {
            "status": "insufficient_data",
            "message": "Brak wystarczających danych do obliczenia (wymagana cena i powierzchnia)."
        }

    # Koszt remontu za m2 wg standardu rynkowego
    m2_rates = {
        "Odświeżenie": 750.0,
        "Standard": 1500.0,
        "Wysoki standard": 2400.0
    }
    cost_per_m2 = m2_rates.get(renovation_standard, 1500.0)
    renovation_budget = area * cost_per_m2

    tx_costs_buy = purchase_price * (transaction_cost_pct / 100.0)
    total_cost_basis = purchase_price + renovation_budget + tx_costs_buy

    # Szacowana cena sprzedaży po remoncie (ARV - After Repair Value)
    arv_price = (purchase_price + renovation_budget) * (1.0 + (arv_markup_pct / 100.0))
    selling_costs = arv_price * (agency_selling_fee_pct / 100.0)
    holding_costs = holding_months * 800.0 # media, czynsz administracyjny przez czas remontu

    gross_profit = arv_price - total_cost_basis - selling_costs - holding_costs
    # Podatek dochodowy (19% od zysku)
    tax_profit = max(0.0, gross_profit * 0.19)
    net_profit = gross_profit - tax_profit
    roi_on_capital = (net_profit / total_cost_basis) * 100.0

    return {
        "status": "calculated",
        "purchase_price": round(purchase_price, 2),
        "renovation_budget": round(renovation_budget, 2),
        "total_cost_basis": round(total_cost_basis, 2),
        "arv_target_price": round(arv_price, 2),
        "arv_price_m2": round(arv_price / area, 2),
        "gross_profit": round(gross_profit, 2),
        "net_profit": round(net_profit, 2),
        "roi_on_capital_pct": round(roi_on_capital, 2),
        "holding_months": holding_months
    }

def calculate_short_term_rental(
    purchase_price: float,
    area: float,
    daily_rate: float = 280.0,
    occupancy_rate_pct: float = 70.0,
    management_fee_pct: float = 20.0,
    ota_fee_pct: float = 15.0,
    monthly_utilities: float = 650.0,
    furnishing_cost: float = 25000.0,
    tax_pct: float = 8.5
) -> Dict[str, Any]:
    """
    Kalkulator Rentowności Wynajmu Krótkoterminowego (Airbnb / Booking / Dobowy).
    """
    if not purchase_price or purchase_price <= 0:
        return {
            "status": "insufficient_data",
            "message": "Brak wystarczających danych do obliczenia (wymagana cena zakupu)."
        }

    occupied_days_year = 365.0 * (occupancy_rate_pct / 100.0)
    occupied_days_month = occupied_days_year / 12.0

    monthly_gross_revenue = occupied_days_month * daily_rate
    annual_gross_revenue = monthly_gross_revenue * 12.0

    ota_cost_year = annual_gross_revenue * (ota_fee_pct / 100.0)
    management_cost_year = annual_gross_revenue * (management_fee_pct / 100.0)
    utilities_cost_year = monthly_utilities * 12.0
    tax_cost_year = annual_gross_revenue * (tax_pct / 100.0)

    annual_total_operating_costs = ota_cost_year + management_cost_year + utilities_cost_year + tax_cost_year
    annual_net_profit = annual_gross_revenue - annual_total_operating_costs
    monthly_net_profit = annual_net_profit / 12.0

    total_capital_invested = purchase_price + furnishing_cost + (purchase_price * 0.035)
    roi_short_term_net = (annual_net_profit / total_capital_invested) * 100.0

    # Porównanie z tradycyjnym najmem długoterminowym
    estimated_long_rent = area * 55.0 if area and area > 10 else 2400.0
    annual_long_net = (estimated_long_rent * 11.5) * (1.0 - 0.085 - 0.05)
    monthly_long_net = annual_long_net / 12.0
    roi_long_term_net = (annual_long_net / (purchase_price * 1.035)) * 100.0

    diff_annual_profit = annual_net_profit - annual_long_net
    diff_monthly_profit = monthly_net_profit - monthly_long_net

    return {
        "status": "calculated",
        "daily_rate": round(daily_rate, 2),
        "occupancy_rate_pct": round(occupancy_rate_pct, 1),
        "occupied_days_month": round(occupied_days_month, 1),
        "monthly_gross_revenue": round(monthly_gross_revenue, 2),
        "annual_gross_revenue": round(annual_gross_revenue, 2),
        "monthly_net_profit": round(monthly_net_profit, 2),
        "annual_net_profit": round(annual_net_profit, 2),
        "roi_short_term_net_pct": round(roi_short_term_net, 2),
        "total_capital_invested": round(total_capital_invested, 2),
        "estimated_long_rent": round(estimated_long_rent, 2),
        "monthly_long_net": round(monthly_long_net, 2),
        "annual_long_net": round(annual_long_net, 2),
        "roi_long_term_net_pct": round(roi_long_term_net, 2),
        "diff_annual_profit": round(diff_annual_profit, 2),
        "diff_monthly_profit": round(diff_monthly_profit, 2),
        "is_short_term_better": diff_annual_profit > 0
    }

def estimate_property_roi(property_dict: Dict[str, Any], city: str = "Wrocław") -> Dict[str, Any]:
    """
    Szybka estymacja ROI dla pojedynczej nieruchomości (do wyświetlenia na karcie i w porównywarce).
    """
    price = property_dict.get("total_price")
    area = property_dict.get("area")

    if not price or not isinstance(price, (int, float)) or price <= 0:
        return {
            "has_data": False,
            "roi_long_net": None,
            "roi_short_net": None,
            "est_rent_monthly": None,
            "est_short_monthly": None
        }

    city_rates = {
        "warszawa": 68.0,
        "krakow": 58.0,
        "kraków": 58.0,
        "wroclaw": 55.0,
        "wrocław": 55.0,
        "gdansk": 56.0,
        "gdańsk": 56.0,
        "poznan": 50.0,
        "poznań": 50.0,
        "katowice": 46.0,
        "lodz": 44.0,
        "łódź": 44.0
    }
    norm_city = str(city).lower().strip()
    rate_m2 = city_rates.get(norm_city, 48.0)

    calc_area = area if area and isinstance(area, (int, float)) and area > 10 else 45.0
    monthly_rent = calc_area * rate_m2

    total_inv = price * 1.035 + 10000.0
    annual_net = (monthly_rent * 11.5) * (1.0 - 0.085 - 0.05)
    roi_long_net = (annual_net / total_inv) * 100.0

    adr_city = {
        "warszawa": 320.0,
        "krakow": 290.0,
        "kraków": 290.0,
        "wroclaw": 270.0,
        "wrocław": 270.0,
        "gdansk": 310.0,
        "gdańsk": 310.0,
        "poznan": 250.0,
        "poznań": 250.0
    }
    adr = adr_city.get(norm_city, 230.0)
    st_res = calculate_short_term_rental(price, calc_area, daily_rate=adr, occupancy_rate_pct=68.0)

    return {
        "has_data": True,
        "roi_long_net": round(roi_long_net, 1),
        "roi_short_net": round(st_res.get("roi_short_term_net_pct", 0), 1),
        "est_rent_monthly": int(round(monthly_rent)),
        "est_short_monthly": int(round(st_res.get("monthly_net_profit", 0))),
        "adr": int(round(adr))
    }
