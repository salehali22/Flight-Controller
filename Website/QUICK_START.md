# Quick Start Guide

## Opening the Website

1. **Double-click** `index.html` OR
2. **Right-click** → Open with → Web Browser

That's it! The website should open in your browser.

## Quick Customizations

### 1. Change Email Address
**File**: `index.html`  
**Line**: ~710  
**Find**: `project@example.com`  
**Replace**: Your actual email

### 2. Add Images to Gallery
**File**: `index.html`  
**Section**: Documentation Gallery (around line 450)

**Current placeholder:**
```html
<div class="gallery-placeholder">
    <span class="placeholder-icon">📸</span>
    <span class="placeholder-text">PCB Design Preview</span>
</div>
```

**Replace with:**
```html
<img src="assets/images/your-image.jpg" alt="Description">
```

### 3. Update Progress Status
**File**: `index.html`  
**Find**: Timeline items with `data-status="planned"`  
**Change to**:
- `data-status="in-progress"` - for current work
- `data-status="completed"` - for finished tasks

### 4. Update Progress Percentage
**File**: `index.html`  
**Find**: `<div class="progress-stat-value">0%</div>`  
**Replace**: `0%` with your actual percentage

### 5. Add Team Photos
**File**: `index.html`  
**Find**: `<div class="avatar-placeholder">AG</div>`  
**Replace with**:
```html
<img src="assets/images/akaki.jpg" alt="Akaki">
```

**Add CSS** to `css/style.css`:
```css
.team-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 50%;
}
```

## Image Recommendations

- **Gallery Images**: 1920x1080 or 16:9 ratio
- **Team Photos**: Square images (500x500px minimum)
- **PCB/Schematic Images**: High resolution, PNG format
- **Flight Test Videos**: MP4 format (can embed with `<video>` tag)

## File Locations

- **Images**: Put in `assets/images/`
- **Documents**: Link from project root or upload to a folder
- **PDFs**: Already in root (Project proposal.pdf)

## Common Tasks

### Update Project Stats
**File**: `index.html`  
**Find**: Hero stats section
```html
<div class="stat-value">24</div>
<div class="stat-label">Months Project</div>
```

### Add New Timeline Item
**File**: `index.html`  
**Copy** a timeline item and modify dates/content

### Change Colors
**File**: `css/style.css`  
**Line**: 9-25 (CSS Variables)
Change `--accent-primary`, `--bg-primary`, etc.

## Need Help?

- Check `README.md` for detailed documentation
- All styles are in `css/style.css`
- All scripts are in `js/script.js`
- HTML structure in `index.html`

## Deployment Options

**Easiest**: GitHub Pages
1. Create GitHub repo
2. Upload files
3. Settings → Pages → Enable

**Fastest**: Netlify
1. Go to netlify.com
2. Drag & drop folder
3. Done!
