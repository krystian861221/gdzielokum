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
