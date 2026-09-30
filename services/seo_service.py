import json
import html
from typing import Dict, Any

def generate_seo_meta_tags(offer: Dict[str, Any], city: str) -> str:
    """
    Generuje meta tagi HTML, Open Graph oraz znacznik schema.org RealEstateListing
    zgodny z wytycznymi Google dla nieruchomości.
    """
    title = offer.get("title", f"Nieruchomość w {city.capitalize()}")
    clean_title = html.escape(title)
    price = offer.get("total_price", 0)
    area = offer.get("area", 0)
    desc = offer.get("description", f"Atrakcyjna nieruchomość w miejscowości {city.capitalize()}. Metraż {area} m2, cena {price} zł.")[:160]
    clean_desc = html.escape(desc)
    img_url = offer.get("image", "https://gdzielokum.pl/static/og_cover.jpg")
    url = offer.get("url", f"https://gdzielokum.pl/nieruchomosci/{city}")

    schema_data = {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": clean_title,
        "description": clean_desc,
        "url": url,
        "image": img_url,
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": "PLN",
            "availability": "https://schema.org/InStock"
        },
        "contentLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": city.capitalize(),
                "addressCountry": "PL"
            }
        }
    }

    schema_json = json.dumps(schema_data, ensure_ascii=False)

    return f"""
    <!-- SEO & Social OpenGraph Tags -->
    <meta name="title" content="{clean_title} | GdzieLokum 2.0">
    <meta name="description" content="{clean_desc}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{clean_title} | GdzieLokum">
    <meta property="og:description" content="{clean_desc}">
    <meta property="og:image" content="{img_url}">
    <meta property="og:url" content="{url}">
    <script type="application/ld+json">
    {schema_json}
    </script>
    """
