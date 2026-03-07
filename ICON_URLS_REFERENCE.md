# Icon URLs Reference

## E-Commerce Platform Icons

### Flipkart
```json
{
  "flipkartLink": "https://www.flipkart.com/search?q=Apple+MacBook+Pro+16",
  "flipkartIcon": "https://static-assets-web.flixcart.com/fk-p-linchpin-web/fk-cp-zion/img/flipkart-plus_8d85f4.png"
}
```
- **Brand Color**: `#2874f0` (Blue)
- **Icon Type**: PNG logo
- **Recommended Size**: 24x24px or 32x32px

### Amazon
```json
{
  "amazonLink": "https://www.amazon.in/s?k=Apple+MacBook+Pro+16",
  "amazonIcon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"
}
```
- **Brand Color**: `#ff9900` (Orange)
- **Icon Type**: SVG logo
- **Recommended Size**: 24x24px or 32x32px

## Brand-Specific Icons

### Apple
```json
{
  "officialLink": "https://www.apple.com/in/",
  "officialIcon": "https://www.apple.com/favicon.ico"
}
```
- **Brand Color**: `#000000` (Black)

### Samsung
```json
{
  "officialLink": "https://www.samsung.com/in/",
  "officialIcon": "https://www.samsung.com/etc.clientlibs/samsung/clientlibs/consumer/global/clientlib-common/resources/images/favicon.png"
}
```
- **Brand Color**: `#1428a0` (Blue)

### OnePlus
```json
{
  "officialLink": "https://www.oneplus.in/",
  "officialIcon": "https://www.oneplus.in/favicon.ico"
}
```
- **Brand Color**: `#eb0028` (Red)

### Xiaomi
```json
{
  "officialLink": "https://www.mi.com/in/",
  "officialIcon": "https://www.mi.com/favicon.ico"
}
```
- **Brand Color**: `#ff6700` (Orange)

### Dell
```json
{
  "officialLink": "https://www.dell.com/en-in/",
  "officialIcon": "https://www.dell.com/favicon.ico"
}
```
- **Brand Color**: `#007db8` (Blue)

### HP
```json
{
  "officialLink": "https://www.hp.com/in-en/",
  "officialIcon": "https://www.hp.com/favicon.ico"
}
```
- **Brand Color**: `#0096d6` (Blue)

### Lenovo
```json
{
  "officialLink": "https://www.lenovo.com/in/en/",
  "officialIcon": "https://www.lenovo.com/favicon.ico"
}
```
- **Brand Color**: `#e2231a` (Red)

### Asus
```json
{
  "officialLink": "https://www.asus.com/in/",
  "officialIcon": "https://www.asus.com/favicon.ico"
}
```
- **Brand Color**: `#000000` (Black)

## Complete Response Example

```json
{
  "success": true,
  "data": {
    "brand": {
      "id": "apple-123",
      "name": "Apple"
    },
    "model": {
      "name": "MacBook Pro 16 (M4)"
    },
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
}
```

## Frontend Display Example

### HTML Structure
```html
<div class="pricing-section">
  <h3>Check Current Price</h3>
  <div class="platform-links">
    <!-- Flipkart -->
    <a href="[flipkartLink]" target="_blank" class="platform-btn flipkart">
      <img src="[flipkartIcon]" alt="Flipkart" />
      <span>Flipkart</span>
    </a>
    
    <!-- Amazon -->
    <a href="[amazonLink]" target="_blank" class="platform-btn amazon">
      <img src="[amazonIcon]" alt="Amazon" />
      <span>Amazon</span>
    </a>
    
    <!-- Official Website -->
    <a href="[officialLink]" target="_blank" class="platform-btn official">
      <img src="[officialIcon]" alt="Official Website" />
      <span>Official Website</span>
    </a>
  </div>
</div>
```

### CSS Styling
```css
.platform-links {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.platform-btn {
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

.platform-btn.flipkart {
  border-color: #2874f0;
}

.platform-btn.flipkart:hover {
  background: #2874f0;
  color: white;
}

.platform-btn.amazon {
  border-color: #ff9900;
}

.platform-btn.amazon:hover {
  background: #ff9900;
  color: white;
}

.platform-btn.official {
  border-color: #000;
}

.platform-btn.official:hover {
  background: #000;
  color: white;
}

.platform-btn img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
```

## Icon Fallback Strategy

If an icon fails to load, use text-only display:

```jsx
<img
  src={platform.icon}
  alt={platform.name}
  onError={(e) => {
    e.target.style.display = 'none';
    e.target.nextSibling.style.marginLeft = '0';
  }}
/>
<span>{platform.name}</span>
```

## Mobile Responsive Design

```css
@media (max-width: 768px) {
  .platform-links {
    flex-direction: column;
  }
  
  .platform-btn {
    width: 100%;
    justify-content: center;
  }
}
```

## Accessibility Considerations

1. **Alt Text**: Always provide descriptive alt text for icons
2. **ARIA Labels**: Add aria-label for screen readers
3. **Keyboard Navigation**: Ensure buttons are keyboard accessible
4. **Focus States**: Add visible focus indicators

```html
<a
  href="[link]"
  target="_blank"
  rel="noopener noreferrer"
  aria-label="Check price on Flipkart"
  class="platform-btn"
>
  <img src="[icon]" alt="Flipkart logo" />
  <span>Flipkart</span>
</a>
```

## Testing Checklist

- [ ] Icons load correctly
- [ ] Links open in new tab
- [ ] Hover states work
- [ ] Mobile responsive
- [ ] Keyboard accessible
- [ ] Screen reader compatible
- [ ] Fallback for missing icons
- [ ] Error handling for broken links
