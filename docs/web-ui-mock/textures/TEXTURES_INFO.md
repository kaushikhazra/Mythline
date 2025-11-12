# Texture Assets for WoW UI

This folder contains texture images for authentic WoW UI styling.

## Required Textures

### 1. stone-texture.png
- **Size:** 512x512px
- **Description:** Dark gray stone with subtle cracks and weathering
- **Usage:** Background for main frames and panels
- **Seamless:** Yes (must tile perfectly)
- **Example sources:**
  - Use a photo editing tool to create from stone images
  - Free texture sites like textures.com or freepik
  - Create procedurally in Photoshop/GIMP

### 2. wood-grain.png
- **Size:** 512x256px
- **Description:** Brown wood with visible horizontal grain
- **Usage:** Background for panels and session lists
- **Seamless:** Yes (horizontal tiling)
- **Color:** Medium-dark brown (#6B4423 to #4A2511)

### 3. parchment.png
- **Size:** 1024x1024px
- **Description:** Aged paper texture with subtle stains and wrinkles
- **Usage:** Background for content areas, quest text, narration
- **Seamless:** Yes
- **Color:** Warm beige/tan (#E8DAB2 to #D2BE96)
- **Notes:** Should be subtle to maintain text readability

### 4. metal-corner.png
- **Size:** 64x64px
- **Description:** Ornate golden corner flourish
- **Usage:** Decorative corners on frames
- **Transparent:** Yes (PNG with alpha)
- **Color:** Gold (#FFD700) with shadows
- **Style:** Medieval/fantasy ornamental design

### 5. leather-texture.png
- **Size:** 512x512px
- **Description:** Brown leather with wrinkles and grain
- **Usage:** Background for file explorer (bag interface)
- **Seamless:** Yes
- **Color:** Dark brown leather (#5C4033 to #3E2723)

## Temporary CSS Fallbacks

If textures are not yet available, the CSS uses:
- **Gradient backgrounds** that simulate texture depth
- **Multiple box-shadows** for 3D beveled effects
- **Border patterns** with pseudo-elements for ornamental look

The UI will look good with or without texture images, but textures add significant authenticity.

## How to Add Textures

1. Create or download the texture images matching the specifications above
2. Save them in this folder (`docs/web-ui-mock/textures/`)
3. Refresh the mockup pages - textures will load automatically
4. If textures don't appear, check browser console for 404 errors

## Creating Textures

### Option 1: Free Online Tools
- **Photopea** (https://www.photopea.com) - Free Photoshop alternative
- Add noise, apply filters, adjust colors
- Export as optimized PNG

### Option 2: AI Generation
- Use AI image generators (DALL-E, Midjourney, Stable Diffusion)
- Prompt: "seamless tileable [texture type] texture, game UI, fantasy style"
- Make seamless using offset filter

### Option 3: Free Texture Sites
- textures.com (some free textures)
- freepik.com (free with attribution)
- pexels.com (free photos to convert)

### Option 4: Procedural in CSS (Advanced)
- Use CSS gradients and patterns to simulate textures
- Performance-friendly
- Less authentic but adequate

## Notes

- All textures should be optimized for web (< 100KB each)
- Use PNG for transparency support (corners)
- Use JPG for opaque textures if smaller file size needed
- Textures blend with CSS using background-blend-mode
