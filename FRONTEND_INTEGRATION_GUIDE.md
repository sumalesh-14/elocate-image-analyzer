# Frontend Integration Guide - Device Pricing with Icons

## Overview
The material analysis API now returns e-commerce links with their corresponding logo/icon URLs, making it easy for the frontend to display them dynamically.

## Response Structure

### Device Pricing Object
```json
{
  "devicePricing": {
    "currentMarketPrice": 249990.00,
    "currency": "INR",
    "flipkartLink": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
    "flipkartIcon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
    "amazonLink": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
    "amazonIcon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "officialLink": "https://www.apple.com/in/",
    "officialIcon": "https://www.apple.com/favicon.ico"
  }
}
```

## Frontend Implementation Examples

### React/Next.js Example

```jsx
import Image from 'next/image';

function DevicePricingLinks({ devicePricing }) {
  if (!devicePricing) return null;

  const platforms = [
    {
      name: 'Flipkart',
      link: devicePricing.flipkartLink,
      icon: devicePricing.flipkartIcon,
      color: '#2874f0'
    },
    {
      name: 'Amazon',
      link: devicePricing.amazonLink,
      icon: devicePricing.amazonIcon,
      color: '#ff9900'
    },
    {
      name: 'Official Website',
      link: devicePricing.officialLink,
      icon: devicePricing.officialIcon,
      color: '#000000'
    }
  ].filter(platform => platform.link); // Only show available platforms

  return (
    <div className="pricing-links">
      <h3>Check Current Price</h3>
      <div className="platform-buttons">
        {platforms.map((platform) => (
          <a
            key={platform.name}
            href={platform.link}
            target="_blank"
            rel="noopener noreferrer"
            className="platform-button"
            style={{ borderColor: platform.color }}
          >
            {platform.icon && (
              <img
                src={platform.icon}
                alt={`${platform.name} logo`}
                width={24}
                height={24}
                className="platform-icon"
              />
            )}
            <span>{platform.name}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
```

### CSS Styling Example

```css
.pricing-links {
  margin: 20px 0;
}

.platform-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.platform-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 2px solid;
  border-radius: 8px;
  background: white;
  text-decoration: none;
  color: #333;
  font-weight: 500;
  transition: all 0.2s;
}

.platform-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.platform-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
```

### Vue.js Example

```vue
<template>
  <div v-if="devicePricing" class="pricing-links">
    <h3>Check Current Price</h3>
    <div class="platform-buttons">
      <a
        v-for="platform in availablePlatforms"
        :key="platform.name"
        :href="platform.link"
        target="_blank"
        rel="noopener noreferrer"
        class="platform-button"
      >
        <img
          v-if="platform.icon"
          :src="platform.icon"
          :alt="`${platform.name} logo`"
          class="platform-icon"
        />
        <span>{{ platform.name }}</span>
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
    availablePlatforms() {
      if (!this.devicePricing) return [];
      
      return [
        {
          name: 'Flipkart',
          link: this.devicePricing.flipkartLink,
          icon: this.devicePricing.flipkartIcon
        },
        {
          name: 'Amazon',
          link: this.devicePricing.amazonLink,
          icon: this.devicePricing.amazonIcon
        },
        {
          name: 'Official Website',
          link: this.devicePricing.officialLink,
          icon: this.devicePricing.officialIcon
        }
      ].filter(platform => platform.link);
    }
  }
}
</script>
```

### Angular Example

```typescript
// component.ts
import { Component, Input } from '@angular/core';

interface Platform {
  name: string;
  link: string;
  icon: string;
  color: string;
}

@Component({
  selector: 'app-device-pricing',
  templateUrl: './device-pricing.component.html',
  styleUrls: ['./device-pricing.component.css']
})
export class DevicePricingComponent {
  @Input() devicePricing: any;

  get availablePlatforms(): Platform[] {
    if (!this.devicePricing) return [];

    return [
      {
        name: 'Flipkart',
        link: this.devicePricing.flipkartLink,
        icon: this.devicePricing.flipkartIcon,
        color: '#2874f0'
      },
      {
        name: 'Amazon',
        link: this.devicePricing.amazonLink,
        icon: this.devicePricing.amazonIcon,
        color: '#ff9900'
      },
      {
        name: 'Official Website',
        link: this.devicePricing.officialLink,
        icon: this.devicePricing.officialIcon,
        color: '#000000'
      }
    ].filter(platform => platform.link);
  }
}
```

```html
<!-- component.html -->
<div *ngIf="devicePricing" class="pricing-links">
  <h3>Check Current Price</h3>
  <div class="platform-buttons">
    <a
      *ngFor="let platform of availablePlatforms"
      [href]="platform.link"
      target="_blank"
      rel="noopener noreferrer"
      class="platform-button"
      [style.border-color]="platform.color"
    >
      <img
        *ngIf="platform.icon"
        [src]="platform.icon"
        [alt]="platform.name + ' logo'"
        class="platform-icon"
      />
      <span>{{ platform.name }}</span>
    </a>
  </div>
</div>
```

## Supported Brands & Icons

The API automatically provides brand-specific icons for:

| Brand | Icon URL | Official Website |
|-------|----------|------------------|
| Apple | `https://www.apple.com/favicon.ico` | `https://www.apple.com/in/` |
| Samsung | `https://www.samsung.com/.../favicon.png` | `https://www.samsung.com/in/` |
| OnePlus | `https://www.oneplus.in/favicon.ico` | `https://www.oneplus.in/` |
| Xiaomi | `https://www.mi.com/favicon.ico` | `https://www.mi.com/in/` |
| Dell | `https://www.dell.com/favicon.ico` | `https://www.dell.com/en-in/` |
| HP | `https://www.hp.com/favicon.ico` | `https://www.hp.com/in-en/` |
| Lenovo | `https://www.lenovo.com/favicon.ico` | `https://www.lenovo.com/in/en/` |
| Asus | `https://www.asus.com/favicon.ico` | `https://www.asus.com/in/` |

And more... (see `device_pricing.py` for full list)

## Platform Icons

### Flipkart
- Icon: `https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png`
- Brand Color: `#2874f0`

### Amazon
- Icon: `https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg`
- Brand Color: `#ff9900`

## Handling Missing Data

### When devicePricing is null
```jsx
{devicePricing ? (
  <DevicePricingLinks devicePricing={devicePricing} />
) : (
  <p>Price information not available</p>
)}
```

### When specific platform is unavailable
```jsx
const platforms = [
  // ... platform definitions
].filter(platform => platform.link); // Automatically filters out null/undefined links
```

### When icon is missing
```jsx
{platform.icon ? (
  <img src={platform.icon} alt={`${platform.name} logo`} />
) : (
  <span className="platform-name-only">{platform.name}</span>
)}
```

## Best Practices

### 1. Image Loading
Use lazy loading for icons:
```jsx
<img
  src={platform.icon}
  alt={`${platform.name} logo`}
  loading="lazy"
/>
```

### 2. Error Handling
Handle image load errors:
```jsx
<img
  src={platform.icon}
  alt={`${platform.name} logo`}
  onError={(e) => {
    e.target.style.display = 'none';
  }}
/>
```

### 3. Accessibility
Always include proper alt text and ARIA labels:
```jsx
<a
  href={platform.link}
  target="_blank"
  rel="noopener noreferrer"
  aria-label={`Check price on ${platform.name}`}
>
  <img src={platform.icon} alt={`${platform.name} logo`} />
  <span>{platform.name}</span>
</a>
```

### 4. Mobile Responsiveness
```css
@media (max-width: 768px) {
  .platform-buttons {
    flex-direction: column;
  }
  
  .platform-button {
    width: 100%;
    justify-content: center;
  }
}
```

## Complete Example Response

```json
{
  "success": true,
  "data": {
    "brand": {"id": "mock", "name": "Apple"},
    "model": {"name": "MacBook Pro 16 (M4)"},
    "devicePricing": {
      "currentMarketPrice": 249990.00,
      "currency": "INR",
      "flipkartLink": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16+(M4)",
      "flipkartIcon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png",
      "amazonLink": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16+(M4)",
      "amazonIcon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
      "officialLink": "https://www.apple.com/in/",
      "officialIcon": "https://www.apple.com/favicon.ico"
    },
    "recyclingEstimate": {
      "totalMaterialValue": 19797.00,
      "suggestedRecyclingPrice": 10888.35,
      "suggestedBuybackPrice": 137494.50,
      "currency": "INR"
    }
  }
}
```

## Notes

1. All icon URLs are from official sources or public CDNs
2. Icons are automatically included based on the brand name
3. Links are country-specific (e.g., amazon.in for India, amazon.com for others)
4. Flipkart links are only provided for India (country: "IN")
5. All external links should open in a new tab with `target="_blank"` and `rel="noopener noreferrer"`
