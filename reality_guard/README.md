# Reality Guard - INDB Landing Page

**Live Demo**: Modern sales landing page showcasing the Inhale-Exhale-Axiom protocol with interactive Psalm 23 deduplication demo.

## Overview

Reality Guard is a production-ready landing page for INDB (Intelligent Neural Database) that demonstrates the core concept of data deduplication through a beautiful, interactive visualization.

## Features

### 🎨 Modern Design (2026)
- **Tailwind CSS** - Utility-first styling
- **Glassmorphism** - Frosted glass effects
- **Gradient animations** - Smooth color transitions
- **Responsive layout** - Mobile-first design

### ✨ Interactive Demo
- **Live particle system** - Real-time canvas rendering
- **Spawn animations** - Particles fly in from screen edges
- **Pulsing INDB core** - Animated central hub
- **Twinkling stars** - Dynamic background
- **Hover tooltips** - Show verse text on mouseover
- **Real-time stats** - Total/Unique/Saved percentage

### 📖 Real Data
- **Psalm 23 verses** - Actual biblical text
- **Deduplication logic** - Remove duplicate verses
- **Canonical output** - Display deduplicated result

## File Structure

```
backend/reality_guard/
├── index.html      # Main landing page (320 lines)
├── demo.js         # Interactive demo logic (297 lines)
└── psalms.js       # Verse data (optional, not used)
```

## Setup

### 1. Start Backend
```bash
cd backend
./start.sh
```

### 2. Start Frontend Server
```bash
cd backend/reality_guard
python3 -m http.server 9000
```

### 3. Open Browser
Navigate to: `http://localhost:9000`

## How to Use

### Demo Workflow

1. **INHALE** - Click "Add Duplicates" to spawn 50 duplicate verses
   - Particles fly in from screen edges
   - Red color indicates duplicates
   
2. **EXHALE** - Click "Remove Duplicates" to run deduplication
   - Particles pull toward INDB core
   - Duplicates fade out
   - Unique verses turn green
   
3. **AXIOM** - Click "Show Canonical Text" to view result
   - Overlay displays deduplicated verses
   - Numbered list with green accents

### Interactive Features

- **Hover particles** - See verse text in floating tooltip
- **Watch stats** - Real-time Total/Unique/Saved counter
- **Pulsing core** - INDB heart beats with data
- **Twinkling stars** - Living cosmic background

## Technical Details

### Canvas Rendering
- **Resolution**: Matches container dimensions
- **Animation**: 60 FPS requestAnimationFrame loop
- **Particles**: Custom class with spawn/update/draw methods

### Particle Behavior

#### Spawn Phase
```javascript
// Particles spawn from random edge
edge = random(top, right, bottom, left)
// Fly to target position around center
velocity = (target - position) * 0.05
// Fade in from alpha 0 → 1
```

#### Normal Phase
```javascript
// Brownian motion
velocity += random(-0.05, 0.05)
velocity *= 0.98 // Damping

// Boundary forces
if near_edge: velocity += push_force
```

#### Exhale Phase
```javascript
// Pull toward center
dx = centerX - x
dy = centerY - y
velocity += (dx, dy) * 0.003
```

### INDB Core Animation
```javascript
pulse = sin(time / 300) * 0.3 + 0.7  // 0.4 to 1.0
radius = 35 + sin(time / 500) * 3     // 32 to 38px
```

### Background Stars
```javascript
twinkle = sin(time / 500 + index * 0.5) * 0.3 + 0.7
alpha = twinkle * 0.3
```

## Color Palette

| Element | Color | Hex |
|---------|-------|-----|
| Axiom (Truth) | Green | `#00ff94` |
| Inhale (Input) | Cyan | `#00ccff` |
| Exhale (Noise) | Pink | `#ff0055` |
| Background | Black | `#000000` |
| Glass | White 5% | `rgba(255,255,255,0.05)` |

## Browser Compatibility

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Performance

- **Canvas**: Hardware accelerated
- **Particles**: Up to 200 simultaneous
- **FPS**: Stable 60fps on modern hardware
- **Memory**: ~50MB typical usage

## Customization

### Change Verses
Edit `VERSES` array in `demo.js`:
```javascript
const VERSES = [
    "Your custom text here",
    "Another verse",
    // ...
];
```

### Adjust Spawn Count
Modify `inhale()` function:
```javascript
inhale() {
    for (let i = 0; i < 100; i++) { // Change 50 to 100
        // ...
    }
}
```

### Change Colors
Update Tailwind config in `index.html`:
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                'axiom': '#YOUR_COLOR',
                'inhale': '#YOUR_COLOR',
                'exhale': '#YOUR_COLOR',
            }
        }
    }
}
```

## Version History

- **v1.0.7** (2026-01-11) - Spawn animations, pulsing core, twinkling stars
- **v1.0.6** - Particle spawn from edges
- **v1.0.5** - Removed close button, added animations
- **v1.0.4** - Axiom overlay instead of alert
- **v1.0.3** - Fixed hover detection
- **v1.0.2** - Fixed HUD positioning
- **v1.0.1** - Added floating HUD
- **v1.0.0** - Initial release

## Credits

- **Concept**: Inhale-Exhale-Axiom protocol
- **Data**: Psalm 23 (King James Version)
- **Framework**: Tailwind CSS
- **Font**: Inter (Google Fonts)

## License

Part of the INDB project.
