# E-Commerce Platforms Reference

## Overview
The material analysis API now returns links to ALL major e-commerce platforms and official brand websites, each with their logo/icon for dynamic frontend display.

## Response Structure

### New Format (Array of Platform Links)
```json
{
  "devicePricing": {
    "currentMarketPrice": 249990.00,
    "currency": "INR",
    "platformLinks": [
      {
        "platformName": "Flipkart",
        "link": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
        "icon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
        "displayOrder": 1
      },
      {
        "platformName": "Amazon",
        "link": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
        "displayOrder": 2
      },
      // ... more platforms
      {
        "platformName": "Apple Official",
        "link": "https://www.apple.com/in/",
        "icon": "https://www.apple.com/favicon.ico",
        "displayOrder": 999
      }
    ]
  }
}
```

## Supported E-Commerce Platforms

### India (country: "IN")

| Platform | Display Order | Icon URL |
|----------|--------------|----------|
| **Flipkart** | 1 | `https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png` |
| **Amazon** | 2 | `https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg` |
| **Snapdeal** | 3 | `https://www.snapdeal.com/favicon.ico` |
| **Croma** | 4 | `https://www.croma.com/favicon.ico` |
| **Reliance Digital** | 5 | `https://www.reliancedigital.in/favicon.ico` |
| **Vijay Sales** | 6 | `https://www.vijaysales.com/favicon.ico` |
| **Tata CLiQ** | 7 | `https://www.tatacliq.com/favicon.ico` |
| **Paytm Mall** | 8 | `https://paytmmall.com/favicon.ico` |

### Global (Other Countries)

| Platform | Display Order | Icon URL |
|----------|--------------|----------|
| **Amazon** | 1 | `https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg` |
| **eBay** | 2 | `https://www.ebay.com/favicon.ico` |
| **Walmart** | 3 | `https://www.walmart.com/favicon.ico` |
| **Best Buy** | 4 | `https://www.bestbuy.com/favicon.ico` |
| **Newegg** | 5 | `https://www.newegg.com/favicon.ico` |

## Supported Brand Official Websites

All brands include country-specific websites and icons:

| Brand | Icon URL | India Website | US Website |
|-------|----------|---------------|------------|
| **Apple** | `https://www.apple.com/favicon.ico` | `https://www.apple.com/in/` | `https://www.apple.com/` |
| **Samsung** | `https://www.samsung.com/.../favicon.png` | `https://www.samsung.com/in/` | `https://www.samsung.com/us/` |
| **OnePlus** | `https://www.oneplus.in/favicon.ico` | `https://www.oneplus.in/` | `https://www.oneplus.com/us/` |
| **Xiaomi** | `https://www.mi.com/favicon.ico` | `https://www.mi.com/in/` | `https://www.mi.com/us/` |
| **Realme** | `https://www.realme.com/favicon.ico` | `https://www.realme.com/in/` | - |
| **OPPO** | `https://www.oppo.com/favicon.ico` | `https://www.oppo.com/in/` | - |
| **Vivo** | `https://www.vivo.com/favicon.ico` | `https://www.vivo.com/in/` | - |
| **Dell** | `https://www.dell.com/favicon.ico` | `https://www.dell.com/en-in/` | `https://www.dell.com/en-us/` |
| **HP** | `https://www.hp.com/favicon.ico` | `https://www.hp.com/in-en/` | `https://www.hp.com/us-en/` |
| **Lenovo** | `https://www.lenovo.com/favicon.ico` | `https://www.lenovo.com/in/en/` | `https://www.lenovo.com/us/en/` |
| **ASUS** | `https://www.asus.com/favicon.ico` | `https://www.asus.com/in/` | `https://www.asus.com/us/` |
| **Acer** | `https://www.acer.com/favicon.ico` | `https://www.acer.com/in-en/` | `https://www.acer.com/us-en/` |
| **MSI** | `https://in.msi.com/favicon.ico` | `https://in.msi.com/` | `https://us.msi.com/` |
| **LG** | `https://www.lg.com/favicon.ico` | `https://www.lg.com/in/` | `https://www.lg.com/us/` |
| **Sony** | `https://www.sony.co.in/favicon.ico` | `https://www.sony.co.in/` | `https://www.sony.com/` |
| **Microsoft** | `https://www.microsoft.com/favicon.ico` | `https://www.microsoft.com/en-in/` | `https://www.microsoft.com/en-us/` |
| **Google** | `https://www.google.com/favicon.ico` | `https://store.google.com/in/` | `https://store.google.com/us/` |
| **Motorola** | `https://www.motorola.in/favicon.ico` | `https://www.motorola.in/` | `https://www.motorola.com/us/` |
| **Nothing** | `https://intl.nothing.tech/favicon.ico` | `https://in.nothing.tech/` | - |

## Frontend Implementation

### React/Next.js Example

```jsx
function PlatformLinks({ devicePricing }) {
  if (!devicePricing?.platformLinks?.length) return null;

  return (
    <div className="platform-links">
      <h3>Check Current Price</h3>
      <div className="platform-grid">
        {devicePricing.platformLinks.map((platform) => (
          <a
            key={platform.platformName}
            href={platform.link}
            target="_blank"
            rel="noopener noreferrer"
            className="platform-card"
          >
            {platform.icon && (
              <img
                src={platform.icon}
                alt={`${platform.platformName} logo`}
                className="platform-icon"
                loading="lazy"
              />
            )}
            <span className="platform-name">{platform.platformName}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
```

### CSS Grid Layout

```css
.platform-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.platform-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  text-decoration: none;
  color: #333;
  transition: all 0.2s;
}

.platform-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
  border-color: #2196f3;
}

.platform-icon {
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.platform-name {
  font-size: 14px;
  font-weight: 500;
  text-align: center;
}

@media (max-width: 768px) {
  .platform-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
```

### Vue.js Example

```vue
<template>
  <div v-if="platformLinks.length" class="platform-links">
    <h3>Check Current Price</h3>
    <div class="platform-grid">
      <a
        v-for="platform in platformLinks"
        :key="platform.platformName"
        :href="platform.link"
        target="_blank"
        rel="noopener noreferrer"
        class="platform-card"
      >
        <img
          v-if="platform.icon"
          :src="platform.icon"
          :alt="`${platform.platformName} logo`"
          class="platform-icon"
          loading="lazy"
        />
        <span class="platform-name">{{ platform.platformName }}</span>
      </a>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    devicePricing: Object
  },
  computed: {
    platformLinks() {
      return this.devicePricing?.platformLinks || [];
    }
  }
}
</script>
```

## Display Order Logic

Platforms are automatically sorted by `displayOrder`:
- Lower numbers appear first (1, 2, 3...)
- Official brand website always appears last (displayOrder: 999)
- Frontend can re-sort if needed

## Example API Response

```json
{
  "success": true,
  "data": {
    "brand": {"name": "Apple"},
    "model": {"name": "MacBook Pro 16 (M4)"},
    "country": "IN",
    "devicePricing": {
      "currentMarketPrice": null,
      "currency": null,
      "platformLinks": [
        {
          "platformName": "Flipkart",
          "link": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
          "displayOrder": 1
        },
        {
          "platformName": "Amazon",
          "link": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
          "displayOrder": 2
        },
        {
          "platformName": "Snapdeal",
          "link": "https://www.snapdeal.com/search?keyword=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.snapdeal.com/favicon.ico",
          "displayOrder": 3
        },
        {
          "platformName": "Croma",
          "link": "https://www.croma.com/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.croma.com/favicon.ico",
          "displayOrder": 4
        },
        {
          "platformName": "Reliance Digital",
          "link": "https://www.reliancedigital.in/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.reliancedigital.in/favicon.ico",
          "displayOrder": 5
        },
        {
          "platformName": "Vijay Sales",
          "link": "https://www.vijaysales.com/search/Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.vijaysales.com/favicon.ico",
          "displayOrder": 6
        },
        {
          "platformName": "Tata CLiQ",
          "link": "https://www.tatacliq.com/search/?searchCategory=all&text=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://www.tatacliq.com/favicon.ico",
          "displayOrder": 7
        },
        {
          "platformName": "Paytm Mall",
          "link": "https://paytmmall.com/shop/search?q=Apple+MacBook+Pro+16+(M4)",
          "icon": "https://paytmmall.com/favicon.ico",
          "displayOrder": 8
        },
        {
          "platformName": "Apple Official",
          "link": "https://www.apple.com/in/",
          "icon": "https://www.apple.com/favicon.ico",
          "displayOrder": 999
        }
      ]
    }
  }
}
```

## Benefits

1. **Scalable**: Easy to add new platforms without changing API structure
2. **Flexible**: Frontend can filter, sort, or customize display
3. **Complete**: Includes all major e-commerce + official brand website
4. **Dynamic**: Icons load from official sources
5. **Country-aware**: Different platforms for different countries

## Adding New Platforms

To add a new platform, update `device_pricing.py`:

```python
ECOMMERCE_PLATFORMS_IN = {
    # ... existing platforms
    "new_platform": {
        "name": "New Platform",
        "icon": "https://www.newplatform.com/favicon.ico",
        "search_url": "https://www.newplatform.com/search?q={query}",
        "display_order": 9
    }
}
```

## Adding New Brands

To add a new brand, update `BRAND_INFO` in `device_pricing.py`:

```python
BRAND_INFO = {
    # ... existing brands
    "newbrand": {
        "name": "NewBrand",
        "icon": "https://www.newbrand.com/favicon.ico",
        "website": {
            "IN": "https://www.newbrand.com/in/",
            "US": "https://www.newbrand.com/us/",
            "default": "https://www.newbrand.com/"
        }
    }
}
```
