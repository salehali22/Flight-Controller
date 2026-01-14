# Custom Flight Controller Website

A modern, dark-themed, technical website for showcasing the Custom Flight Controller Development project for UAV Applications.

## Features

- **Modern Dark Theme**: Professional dark technical theme with gradient accents
- **Fully Responsive**: Desktop-optimized (mobile support can be added later)
- **Interactive Elements**: Smooth scrolling, animated sections, interactive component diagram
- **Comprehensive Sections**:
  - Hero/Landing section with project stats
  - Project overview and features
  - Detailed technical specifications
  - Interactive timeline/progress tracker
  - Team member profiles
  - Documentation gallery with tabs
  - Contact form
- **Easy Content Management**: Simple structure for adding images and updating content

## Project Structure

```
FC site/
├── index.html          # Main HTML file
├── css/
│   └── style.css      # All styles (dark theme)
├── js/
│   └── script.js      # Interactive features
├── assets/
│   └── images/        # Place images here
├── Project proposal.pdf
├── Project proposal.txt
└── Project_Analysis.md
```

## Getting Started

### 1. View the Website

Simply open `index.html` in any modern web browser. No server or build process required!

```bash
# Just double-click index.html or open in browser
```

### 2. Adding Images to Gallery

Replace the placeholder gallery items with actual images:

**In `index.html`, find the gallery section (around line 450):**

```html
<div class="gallery-item">
    <div class="gallery-placeholder">
        <span class="placeholder-icon">📸</span>
        <span class="placeholder-text">PCB Design Preview</span>
    </div>
    <div class="gallery-overlay">
        <span>PCB Layout</span>
    </div>
</div>
```

**Replace with:**

```html
<div class="gallery-item">
    <img src="assets/images/pcb-design.jpg" alt="PCB Design Preview">
    <div class="gallery-overlay">
        <span>PCB Layout</span>
    </div>
</div>
```

**Add this CSS if needed (already included in style.css):**

```css
.gallery-item img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
```

### 3. Updating Team Member Photos

Replace avatar placeholders with actual photos:

**Find team cards and replace:**

```html
<div class="team-avatar">
    <div class="avatar-placeholder">AG</div>
</div>
```

**With:**

```html
<div class="team-avatar">
    <img src="assets/images/akaki.jpg" alt="Akaki Gvelesiani">
</div>
```

**Add CSS:**

```css
.team-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 50%;
}
```

### 4. Updating Contact Information

**Find the contact section and update:**

```html
<p><a href="mailto:project@example.com">project@example.com</a></p>
```

Replace with your actual email address.

### 5. Updating Project Progress

**To mark timeline items as completed or in-progress:**

In `index.html`, find timeline items and update the `data-status` attribute:

```html
<!-- Planned (default) -->
<div class="timeline-item" data-status="planned">

<!-- In Progress -->
<div class="timeline-item" data-status="in-progress">

<!-- Completed -->
<div class="timeline-item" data-status="completed">
```

### 6. Enabling Contact Form

The contact form currently logs to console. To enable email functionality:

**Option 1: Use Formspree (Easiest)**
1. Sign up at https://formspree.io/
2. Get your form endpoint
3. In `index.html`, update the form:

```html
<form class="contact-form" action="https://formspree.io/f/YOUR_FORM_ID" method="POST">
```

**Option 2: Use EmailJS**
1. Sign up at https://www.emailjs.com/
2. Follow their integration guide
3. Add EmailJS script and configure

**Option 3: Backend Integration**
- Integrate with your own backend API
- Update the form submission handler in `js/script.js`

## Customization

### Colors

All colors are defined in CSS variables at the top of `css/style.css`:

```css
:root {
    --bg-primary: #0a0e1a;
    --accent-primary: #6366f1;
    --accent-secondary: #8b5cf6;
    /* ... more colors ... */
}
```

Change these values to customize the color scheme.

### Fonts

The site uses:
- **Inter** for body text
- **JetBrains Mono** for technical/monospace text

Both are loaded from Google Fonts. Change in the `<head>` section of `index.html`.

### Typography

Font sizes and spacing can be adjusted in the CSS variables section.

## Deployment

### Option 1: GitHub Pages (Free)

1. Create a GitHub repository
2. Upload all files
3. Go to Settings > Pages
4. Select branch and folder
5. Your site will be live at `username.github.io/repository-name`

### Option 2: Netlify (Free)

1. Sign up at https://netlify.com/
2. Drag and drop your project folder
3. Site is live instantly

### Option 3: Vercel (Free)

1. Sign up at https://vercel.com/
2. Import your project
3. Deploy with one click

### Option 4: University Hosting

Upload files to your university web server via FTP/SFTP.

## Browser Support

- Chrome (Recommended)
- Firefox
- Edge
- Safari

## Future Enhancements

- Add blog/updates section
- Implement image lightbox for gallery
- Add scroll-to-top button
- Mobile responsive improvements
- Add video embedding for flight tests
- Integrate with GitHub API for code repository
- Add 3D model viewer for PCB
- Add real-time progress tracking

## Notes

- **Images**: Currently using placeholder divs. Replace with actual images in `assets/images/`
- **Contact Form**: Requires backend integration or service like Formspree
- **Progress Timeline**: Update `data-status` attributes as project progresses
- **Mobile**: Desktop-focused for now, can be enhanced later

## License

This project is part of the Custom Flight Controller Development for UAV Applications senior project at Ilia State University.

## Support

For questions or issues, contact the development team.

---

**Last Updated**: January 2025
**Project Timeline**: October 2025 - June 2026
