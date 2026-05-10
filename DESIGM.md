---
name: Serene Commerce
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#4d4447'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f1f1f1'
  outline: '#7f7478'
  outline-variant: '#d0c3c7'
  surface-tint: '#6b5a60'
  primary: '#6b5a60'
  on-primary: '#ffffff'
  primary-container: '#fce4ec'
  on-primary-container: '#76646b'
  inverse-primary: '#d7c1c8'
  secondary: '#526069'
  on-secondary: '#ffffff'
  secondary-container: '#d3e2ed'
  on-secondary-container: '#56656e'
  tertiary: '#556158'
  on-tertiary: '#ffffff'
  tertiary-container: '#e0ede1'
  on-tertiary-container: '#606c62'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#f4dce4'
  primary-fixed-dim: '#d7c1c8'
  on-primary-fixed: '#25181e'
  on-primary-fixed-variant: '#524249'
  secondary-fixed: '#d6e5ef'
  secondary-fixed-dim: '#bac9d3'
  on-secondary-fixed: '#0f1d25'
  on-secondary-fixed-variant: '#3b4951'
  tertiary-fixed: '#d9e6da'
  tertiary-fixed-dim: '#bdcabe'
  on-tertiary-fixed: '#131e17'
  on-tertiary-fixed-variant: '#3e4a41'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  display:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Outfit
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Outfit
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Outfit
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  label-caps:
    fontFamily: Outfit
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  container-margin: 20px
  gutter: 16px
---

## Brand & Style

This design system is anchored in a **Soft Minimalism** aesthetic, specifically tailored for a premium, high-end e-commerce experience. The brand personality is gentle, sophisticated, and intentional. It aims to evoke a sense of calm and clarity, reducing the "decision fatigue" often associated with digital shopping.

The visual direction prioritizes clarity through high-quality product photography and ample white space. By utilizing a "Quiet UI" approach, the interface recedes into the background, allowing the products to become the primary focal point. The emotional response is one of effortless luxury and approachability, achieved through soft-edged geometry and a soothing pastel palette.

## Colors

The palette is built on a foundation of "Airy Neutrals" and "Whimsical Pastels." 
- **Primary (Soft Pink):** Used for primary calls to action, brand highlights, and active states. It adds a touch of warmth and human connection.
- **Secondary (Pastel Blue):** Utilized for informational elements, secondary categories, and calming backgrounds.
- **Tertiary (Mint Green):** Reserved for "Success" states, promotional badges, or sustainability indicators.
- **Neutral:** A range of off-whites and very light greys are used for backgrounds and surfaces to ensure the layout remains "airy" without the harshness of pure #FFFFFF.
- **Text:** High-contrast dark charcoal is used for readability, while a muted slate grey is reserved for secondary information.

## Typography

This design system utilizes **Outfit** for its geometric yet friendly characteristics. The wide apertures and consistent stroke weights align perfectly with the minimalist ethos.

- **Headlines:** Set with tight tracking and medium-to-bold weights to create a clear visual hierarchy.
- **Body Text:** Generous line heights (1.6) are applied to ensure maximum legibility and to contribute to the "airy" feel of the interface.
- **Labels:** Small-scale labels use slightly increased letter spacing and uppercase styling to provide contrast against body text without requiring heavy weights.

## Layout & Spacing

The layout follows a **Fluid Mobile Grid** philosophy. We employ a 4-column structure for mobile views with a standard 20px outer margin to provide content with breathing room.

- **Rhythm:** A 4px baseline grid governs all vertical spacing. 
- **Padding:** Internal card padding is strictly set to 16px (md) or 24px (lg) to prevent elements from feeling cramped.
- **Photography:** Product images should always span either the full width of the container or exactly 2 columns to maintain a clean, rhythmic alignment.

## Elevation & Depth

Depth is achieved through **Ambient Shadows** rather than physical borders. The goal is to make elements appear as though they are floating softly above the surface.

- **Shadow Character:** Use highly diffused shadows with a large blur radius (20px+) and low opacity (5-8%). The shadow color should be slightly tinted with the primary or secondary pastel hues rather than pure black to maintain the "soft" feel.
- **Tonal Layering:** Different "levels" of white and pastel are used to distinguish between the background and foreground containers. For example, a card may be pure white (#FFFFFF) sitting on a soft neutral (#F9F9F9) background.
- **Interaction:** On press or hover, shadows should subtly contract or deepen to provide tactile feedback without breaking the minimalist aesthetic.

## Shapes

The shape language is defined by **Generous Radii**. All interactive elements and containers use a minimum of 16px corner radius to evoke a sense of safety and friendliness.

- **Buttons & Inputs:** Use the `rounded-xl` (1.5rem / 24px) setting to create a friendly, organic feel.
- **Product Cards:** Utilize a standard `rounded-lg` (1rem / 16px) for a balanced, structured appearance.
- **Images:** Product photography should always mirror the container's corner radius to ensure a cohesive visual unit.

## Components

- **Buttons:** Primary buttons use the Soft Pink background with dark text. Secondary buttons should be Ghost-style with a subtle Pastel Blue border or a light blue tinted fill. Avoid heavy solid blacks.
- **Cards:** Product cards are borderless, utilizing the ambient shadow and 16px rounded corners. Imagery should be top-aligned with no internal margin between the image and the top/side edges of the card.
- **Inputs:** Text fields feature a light pastel background instead of a white fill, with 24px rounded corners. Focus states are indicated by a 1px solid primary-colored border.
- **Chips:** Used for sizing and categories, chips should use a "Pill" shape (fully rounded ends) with a light secondary color fill and no border.
- **Lists:** List items are separated by generous white space rather than lines. If a divider is necessary, it should be a 1px line in the lightest possible neutral shade, with horizontal margins.
- **Product Focus:** An "Image Carousel" component is central, featuring pagination dots that utilize the pastel palette to indicate the active state.