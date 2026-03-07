"""
Device pricing service for fetching current market prices from e-commerce platforms.

This service provides device pricing information from various sources.
"""

import logging
from typing import Optional, Dict, Any, List
from app.models.material_analysis import DevicePricing, PlatformLink


logger = logging.getLogger(__name__)


# E-commerce platform configurations for India
ECOMMERCE_PLATFORMS_IN = {
    "flipkart": {
        "name": "Flipkart",
        "icon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
        "search_url": "https://www.flipkart.com/search?q={query}",
        "display_order": 1
    },
    "amazon": {
        "name": "Amazon",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
        "search_url": "https://www.amazon.in/s?k={query}",
        "display_order": 2
    },
    "snapdeal": {
        "name": "Snapdeal",
        "icon": "https://www.snapdeal.com/favicon.ico",
        "search_url": "https://www.snapdeal.com/search?keyword={query}",
        "display_order": 3
    },
    "croma": {
        "name": "Croma",
        "icon": "https://www.croma.com/favicon.ico",
        "search_url": "https://www.croma.com/search?q={query}",
        "display_order": 4
    },
    "reliance_digital": {
        "name": "Reliance Digital",
        "icon": "https://www.reliancedigital.in/favicon.ico",
        "search_url": "https://www.reliancedigital.in/search?q={query}",
        "display_order": 5
    },
    "vijay_sales": {
        "name": "Vijay Sales",
        "icon": "https://www.vijaysales.com/favicon.ico",
        "search_url": "https://www.vijaysales.com/search/{query}",
        "display_order": 6
    },
    "tata_cliq": {
        "name": "Tata CLiQ",
        "icon": "https://www.tatacliq.com/favicon.ico",
        "search_url": "https://www.tatacliq.com/search/?searchCategory=all&text={query}",
        "display_order": 7
    },
    "paytm_mall": {
        "name": "Paytm Mall",
        "icon": "https://paytmmall.com/favicon.ico",
        "search_url": "https://paytmmall.com/shop/search?q={query}",
        "display_order": 8
    }
}

# E-commerce platforms for other countries
ECOMMERCE_PLATFORMS_GLOBAL = {
    "amazon": {
        "name": "Amazon",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
        "search_url": "https://www.amazon.com/s?k={query}",
        "display_order": 1
    },
    "ebay": {
        "name": "eBay",
        "icon": "https://www.ebay.com/favicon.ico",
        "search_url": "https://www.ebay.com/sch/i.html?_nkw={query}",
        "display_order": 2
    },
    "walmart": {
        "name": "Walmart",
        "icon": "https://www.walmart.com/favicon.ico",
        "search_url": "https://www.walmart.com/search?q={query}",
        "display_order": 3
    },
    "best_buy": {
        "name": "Best Buy",
        "icon": "https://www.bestbuy.com/favicon.ico",
        "search_url": "https://www.bestbuy.com/site/searchpage.jsp?st={query}",
        "display_order": 4
    },
    "newegg": {
        "name": "Newegg",
        "icon": "https://www.newegg.com/favicon.ico",
        "search_url": "https://www.newegg.com/p/pl?d={query}",
        "display_order": 5
    }
}

# Brand-specific official websites and icons
BRAND_INFO = {
    "apple": {
        "name": "Apple",
        "icon": "https://www.apple.com/favicon.ico",
        "website": {
            "IN": "https://www.apple.com/in/",
            "US": "https://www.apple.com/",
            "default": "https://www.apple.com/"
        }
    },
    "samsung": {
        "name": "Samsung",
        "icon": "https://www.samsung.com/etc.clientlibs/samsung/clientlibs/consumer/global/clientlib-common/resources/images/favicon.png",
        "website": {
            "IN": "https://www.samsung.com/in/",
            "US": "https://www.samsung.com/us/",
            "default": "https://www.samsung.com/"
        }
    },
    "oneplus": {
        "name": "OnePlus",
        "icon": "https://www.oneplus.in/favicon.ico",
        "website": {
            "IN": "https://www.oneplus.in/",
            "US": "https://www.oneplus.com/us/",
            "default": "https://www.oneplus.com/"
        }
    },
    "xiaomi": {
        "name": "Xiaomi",
        "icon": "https://www.mi.com/favicon.ico",
        "website": {
            "IN": "https://www.mi.com/in/",
            "US": "https://www.mi.com/us/",
            "default": "https://www.mi.com/"
        }
    },
    "realme": {
        "name": "Realme",
        "icon": "https://www.realme.com/favicon.ico",
        "website": {
            "IN": "https://www.realme.com/in/",
            "default": "https://www.realme.com/"
        }
    },
    "oppo": {
        "name": "OPPO",
        "icon": "https://www.oppo.com/favicon.ico",
        "website": {
            "IN": "https://www.oppo.com/in/",
            "default": "https://www.oppo.com/"
        }
    },
    "vivo": {
        "name": "Vivo",
        "icon": "https://www.vivo.com/favicon.ico",
        "website": {
            "IN": "https://www.vivo.com/in/",
            "default": "https://www.vivo.com/"
        }
    },
    "dell": {
        "name": "Dell",
        "icon": "https://www.dell.com/favicon.ico",
        "website": {
            "IN": "https://www.dell.com/en-in/",
            "US": "https://www.dell.com/en-us/",
            "default": "https://www.dell.com/"
        }
    },
    "hp": {
        "name": "HP",
        "icon": "https://www.hp.com/favicon.ico",
        "website": {
            "IN": "https://www.hp.com/in-en/",
            "US": "https://www.hp.com/us-en/",
            "default": "https://www.hp.com/"
        }
    },
    "lenovo": {
        "name": "Lenovo",
        "icon": "https://www.lenovo.com/favicon.ico",
        "website": {
            "IN": "https://www.lenovo.com/in/en/",
            "US": "https://www.lenovo.com/us/en/",
            "default": "https://www.lenovo.com/"
        }
    },
    "asus": {
        "name": "ASUS",
        "icon": "https://www.asus.com/favicon.ico",
        "website": {
            "IN": "https://www.asus.com/in/",
            "US": "https://www.asus.com/us/",
            "default": "https://www.asus.com/"
        }
    },
    "acer": {
        "name": "Acer",
        "icon": "https://www.acer.com/favicon.ico",
        "website": {
            "IN": "https://www.acer.com/in-en/",
            "US": "https://www.acer.com/us-en/",
            "default": "https://www.acer.com/"
        }
    },
    "msi": {
        "name": "MSI",
        "icon": "https://in.msi.com/favicon.ico",
        "website": {
            "IN": "https://in.msi.com/",
            "US": "https://us.msi.com/",
            "default": "https://www.msi.com/"
        }
    },
    "lg": {
        "name": "LG",
        "icon": "https://www.lg.com/favicon.ico",
        "website": {
            "IN": "https://www.lg.com/in/",
            "US": "https://www.lg.com/us/",
            "default": "https://www.lg.com/"
        }
    },
    "sony": {
        "name": "Sony",
        "icon": "https://www.sony.co.in/favicon.ico",
        "website": {
            "IN": "https://www.sony.co.in/",
            "US": "https://www.sony.com/",
            "default": "https://www.sony.com/"
        }
    },
    "microsoft": {
        "name": "Microsoft",
        "icon": "https://www.microsoft.com/favicon.ico",
        "website": {
            "IN": "https://www.microsoft.com/en-in/",
            "US": "https://www.microsoft.com/en-us/",
            "default": "https://www.microsoft.com/"
        }
    },
    "google": {
        "name": "Google",
        "icon": "https://www.google.com/favicon.ico",
        "website": {
            "IN": "https://store.google.com/in/",
            "US": "https://store.google.com/us/",
            "default": "https://store.google.com/"
        }
    },
    "motorola": {
        "name": "Motorola",
        "icon": "https://www.motorola.in/favicon.ico",
        "website": {
            "IN": "https://www.motorola.in/",
            "US": "https://www.motorola.com/us/",
            "default": "https://www.motorola.com/"
        }
    },
    "nothing": {
        "name": "Nothing",
        "icon": "https://intl.nothing.tech/favicon.ico",
        "website": {
            "IN": "https://in.nothing.tech/",
            "default": "https://intl.nothing.tech/"
        }
    }
}


class DevicePricingService:
    """Service for fetching device pricing information."""
    
    def __init__(self):
        """Initialize the device pricing service."""
        self.logger = logging.getLogger(__name__)
    
    def _get_brand_info(self, brand_name: str, country: str) -> Optional[Dict[str, str]]:
        """
        Get brand official website and icon.
        
        Args:
            brand_name: Brand name
            country: Country code
            
        Returns:
            Dictionary with website and icon, or None
        """
        brand_lower = brand_name.lower().strip()
        brand_data = BRAND_INFO.get(brand_lower)
        
        if not brand_data:
            return None
        
        # Get country-specific website or default
        website = brand_data["website"].get(country) or brand_data["website"].get("default")
        
        return {
            "name": brand_data["name"],
            "website": website,
            "icon": brand_data["icon"]
        }
    
    def _build_platform_links(
        self,
        search_query: str,
        country: str,
        brand_name: str
    ) -> List[PlatformLink]:
        """
        Build list of platform links with icons.
        
        Args:
            search_query: Search query string
            country: Country code
            brand_name: Brand name for official website
            
        Returns:
            List of PlatformLink objects
        """
        platform_links = []
        
        # Get e-commerce platforms based on country
        if country == "IN":
            platforms = ECOMMERCE_PLATFORMS_IN
        else:
            platforms = ECOMMERCE_PLATFORMS_GLOBAL
        
        # Add e-commerce platform links
        for platform_key, platform_data in platforms.items():
            search_url = platform_data["search_url"].format(query=search_query)
            platform_links.append(
                PlatformLink(
                    platformName=platform_data["name"],
                    link=search_url,
                    icon=platform_data["icon"],
                    displayOrder=platform_data["display_order"]
                )
            )
        
        # Add official brand website
        brand_info = self._get_brand_info(brand_name, country)
        if brand_info:
            platform_links.append(
                PlatformLink(
                    platformName=f"{brand_info['name']} Official",
                    link=brand_info["website"],
                    icon=brand_info["icon"],
                    displayOrder=999  # Show official link last
                )
            )
        
        # Sort by display order
        platform_links.sort(key=lambda x: x.display_order or 999)
        
        return platform_links
    
    async def get_device_pricing(
        self,
        brand_name: str,
        model_name: str,
        category_name: str,
        country: str
    ) -> Optional[DevicePricing]:
        """
        Get device pricing information from e-commerce platforms.
        
        This is a placeholder implementation. In production, you would:
        1. Use web scraping APIs (with proper rate limiting and caching)
        2. Use official e-commerce APIs if available
        3. Maintain a database of device prices
        4. Use price comparison APIs
        
        Args:
            brand_name: Device brand name
            model_name: Device model name
            category_name: Device category
            country: Country code for regional pricing
            
        Returns:
            DevicePricing object with pricing information, or None if not available
        """
        try:
            self.logger.info(
                f"Price lookup requested for {brand_name} {model_name}",
                extra={
                    "brand": brand_name,
                    "model": model_name,
                    "category": category_name,
                    "country": country
                }
            )
            
            # Generate search query
            search_query = f"{brand_name} {model_name}".replace(" ", "+")
            
            # Build platform links
            platform_links = self._build_platform_links(
                search_query=search_query,
                country=country,
                brand_name=brand_name
            )
            
            # Return pricing object with all platform links
            return DevicePricing(
                currentMarketPrice=None,  # Set to None until actual API integration
                currency=None,
                platformLinks=platform_links
            )
            
        except Exception as e:
            self.logger.error(
                f"Error fetching device pricing: {str(e)}",
                extra={
                    "brand": brand_name,
                    "model": model_name,
                    "error": str(e)
                }
            )
            return None


# Global service instance
device_pricing_service = DevicePricingService()
