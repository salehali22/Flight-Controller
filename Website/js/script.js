// ===================================
// Flight Controller Website JavaScript
// Interactive Features & Navigation
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Navigation Scroll Effect
    // ===================================
    
    const navbar = document.getElementById('navbar');
    let lastScroll = 0;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset;
        
        // Add scrolled class for styling
        if (currentScroll > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        
        lastScroll = currentScroll;
    });
    
    // ===================================
    // Smooth Scrolling for Navigation Links
    // ===================================
    
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Only handle anchor links
            if (href.startsWith('#')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    const offsetTop = targetElement.offsetTop - 80; // Account for fixed navbar
                    
                    window.scrollTo({
                        top: offsetTop,
                        behavior: 'smooth'
                    });
                    
                    // Update active link
                    navLinks.forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                }
            }
        });
    });
    
    // ===================================
    // Active Navigation Link on Scroll
    // ===================================
    
    const sections = document.querySelectorAll('.section, .hero');
    
    function updateActiveNavLink() {
        const scrollPosition = window.pageYOffset + 100;
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.offsetHeight;
            const sectionId = section.getAttribute('id');
            
            if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === `#${sectionId}`) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }
    
    window.addEventListener('scroll', updateActiveNavLink);
    
    // ===================================
    // Mobile Navigation Toggle
    // ===================================
    
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            this.classList.toggle('active');
        });
    }
    
    // ===================================
    // Documentation Tabs
    // ===================================
    
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            this.classList.add('active');
            const targetContent = document.getElementById(`${targetTab}-tab`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });
    
    // ===================================
    // Component Diagram Interactions
    // ===================================
    
    const diagramItems = document.querySelectorAll('.diagram-item');
    
    diagramItems.forEach(item => {
        item.addEventListener('click', function() {
            const component = this.getAttribute('data-component');
            console.log('Component clicked:', component);
            
            // Add pulse animation
            this.style.animation = 'pulse 0.5s ease';
            setTimeout(() => {
                this.style.animation = '';
            }, 500);
            
            // Highlight the info panel
            const infoPanel = this.querySelector('.diagram-info-panel');
            if (infoPanel) {
                infoPanel.style.animation = 'pulse 0.3s ease';
                setTimeout(() => {
                    infoPanel.style.animation = '';
                }, 300);
            }
        });
        
        // Ensure info panel stays visible on hover
        item.addEventListener('mouseenter', function() {
            const infoPanel = this.querySelector('.diagram-info-panel');
            if (infoPanel) {
                infoPanel.style.zIndex = '1000';
            }
        });
    });
    
    // ===================================
    // Timeline Item Interactions
    // ===================================
    
    const timelineItems = document.querySelectorAll('.timeline-item');
    
    timelineItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            const marker = this.querySelector('.timeline-marker');
            marker.style.transform = 'scale(1.3)';
        });
        
        item.addEventListener('mouseleave', function() {
            const marker = this.querySelector('.timeline-marker');
            marker.style.transform = 'scale(1)';
        });
    });
    
    // ===================================
    // Contact Form Handling
    // ===================================
    
    const contactForm = document.getElementById('contact-form');
    
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const formData = new FormData(this);
            const data = {
                name: formData.get('name'),
                email: formData.get('email'),
                subject: formData.get('subject'),
                message: formData.get('message')
            };
            
            // Basic validation
            if (!data.name || !data.email || !data.message) {
                alert('Please fill in all required fields.');
                return;
            }
            
            // Email validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(data.email)) {
                alert('Please enter a valid email address.');
                return;
            }
            
            // For now, just log the data
            // In production, you would send this to a backend API
            // or use a service like Formspree, EmailJS, etc.
            console.log('Form submitted:', data);
            alert('Thank you for your message! In production, this would be sent via email service.');
            
            // Reset form
            this.reset();
            
            // You can integrate with:
            // - Formspree: https://formspree.io/
            // - EmailJS: https://www.emailjs.com/
            // - Your own backend API
        });
    }
    
    // ===================================
    // Scroll Animations
    // ===================================
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for scroll animations
    const animatedElements = document.querySelectorAll('.overview-card, .specs-category, .team-card, .timeline-item, .feature-item');
    
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
    
    // ===================================
    // Progress Stats Animation
    // ===================================
    
    function animateCounter(element, target, duration = 2000) {
        let start = 0;
        const increment = target / (duration / 16);
        
        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                element.textContent = target + (element.textContent.includes('%') ? '%' : '');
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(start) + (element.textContent.includes('%') ? '%' : '');
            }
        }, 16);
    }
    
    // Animate progress stats when they come into view
    const progressStats = document.querySelectorAll('.progress-stat-value');
    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const value = entry.target.textContent;
                const numericValue = parseInt(value);
                if (!isNaN(numericValue)) {
                    animateCounter(entry.target, numericValue);
                    statsObserver.unobserve(entry.target);
                }
            }
        });
    }, observerOptions);
    
    progressStats.forEach(stat => {
        statsObserver.observe(stat);
    });
    
    // ===================================
    // Gallery Item Click (for lightbox - basic implementation)
    // ===================================
    
    const galleryItems = document.querySelectorAll('.gallery-item');
    
    galleryItems.forEach(item => {
        item.addEventListener('click', function() {
            // For now, just log
            // You can implement a lightbox/modal here
            console.log('Gallery item clicked');
            
            // Example lightbox implementation:
            // const img = this.querySelector('img');
            // if (img) {
            //     showLightbox(img.src, img.alt);
            // }
        });
    });
    
    // ===================================
    // Feature Item Hover Effects
    // ===================================
    
    const featureItems = document.querySelectorAll('.feature-item');
    
    featureItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.style.borderLeftWidth = '4px';
        });
        
        item.addEventListener('mouseleave', function() {
            this.style.borderLeftWidth = '3px';
        });
    });
    
    // ===================================
    // Card Hover Effects Enhancement
    // ===================================
    
    const cards = document.querySelectorAll('.overview-card, .specs-category, .team-card, .download-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            // Add subtle glow effect
            this.style.transition = 'all 0.3s ease';
        });
    });
    
    // ===================================
    // Scroll to Top (Optional - can add button)
    // ===================================
    
    // You can add a scroll-to-top button if needed:
    // 
    // function createScrollToTop() {
    //     const button = document.createElement('button');
    //     button.innerHTML = '↑';
    //     button.className = 'scroll-to-top';
    //     button.style.cssText = `
    //         position: fixed;
    //         bottom: 30px;
    //         right: 30px;
    //         width: 50px;
    //         height: 50px;
    //         border-radius: 50%;
    //         background: var(--accent-primary);
    //         color: white;
    //         border: none;
    //         cursor: pointer;
    //         font-size: 24px;
    //         z-index: 999;
    //         opacity: 0;
    //         transition: opacity 0.3s ease;
    //     `;
    //     
    //     button.addEventListener('click', () => {
    //         window.scrollTo({ top: 0, behavior: 'smooth' });
    //     });
    //     
    //     window.addEventListener('scroll', () => {
    //         if (window.pageYOffset > 300) {
    //             button.style.opacity = '1';
    //         } else {
    //             button.style.opacity = '0';
    //         }
    //     });
    //     
    //     document.body.appendChild(button);
    // }
    // 
    // createScrollToTop();
    
    // ===================================
    // Console Message
    // ===================================
    
    console.log('%cCustom Flight Controller Website', 'font-size: 20px; font-weight: bold; color: #6366f1;');
    console.log('%cBuilt with modern web technologies', 'font-size: 12px; color: #9ca3af;');
    
});

// ===================================
// Utility Functions
// ===================================

// Debounce function for scroll events (optional optimization)
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for scroll events (optional optimization)
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
