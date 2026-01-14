// ===================================
// Downloads Page JavaScript
// Category Filtering & Interactions
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ===================================
    // Category Filtering
    // ===================================
    
    const categoryButtons = document.querySelectorAll('.category-btn');
    const downloadItems = document.querySelectorAll('.download-item');
    
    categoryButtons.forEach(button => {
        button.addEventListener('click', function() {
            const category = this.getAttribute('data-category');
            
            // Update active button
            categoryButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Filter download items
            downloadItems.forEach(item => {
                const itemCategory = item.getAttribute('data-category');
                
                if (category === 'all' || itemCategory === category) {
                    item.classList.remove('hidden');
                    // Add fade-in animation
                    item.style.opacity = '0';
                    item.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                        item.style.opacity = '1';
                        item.style.transform = 'translateY(0)';
                    }, 10);
                } else {
                    item.classList.add('hidden');
                }
            });
        });
    });
    
    // ===================================
    // Download Button Interactions
    // ===================================
    
    const downloadButtons = document.querySelectorAll('.download-btn-primary:not(.disabled)');
    
    downloadButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Add click animation
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
            
            // Track download (optional - for analytics)
            const downloadItem = this.closest('.download-item');
            if (downloadItem) {
                const fileName = downloadItem.querySelector('h3').textContent;
                console.log('Download initiated:', fileName);
            }
        });
    });
    
    // ===================================
    // Scroll Animations for Download Items
    // ===================================
    
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Initialize items with hidden state
    downloadItems.forEach(item => {
        item.style.opacity = '0';
        item.style.transform = 'translateY(30px)';
        item.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(item);
    });
    
    // ===================================
    // Stats Counter Animation
    // ===================================
    
    function animateCounter(element, target, duration = 2000) {
        let start = 0;
        const increment = target / (duration / 16);
        
        const timer = setInterval(() => {
            start += increment;
            if (start >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(start);
            }
        }, 16);
    }
    
    const statValues = document.querySelectorAll('.stat-value');
    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const value = parseInt(entry.target.textContent);
                if (!isNaN(value)) {
                    animateCounter(entry.target, value);
                    statsObserver.unobserve(entry.target);
                }
            }
        });
    }, observerOptions);
    
    statValues.forEach(stat => {
        statsObserver.observe(stat);
    });
    
    // ===================================
    // Hover Effects Enhancement
    // ===================================
    
    downloadItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            const iconWrapper = this.querySelector('.download-icon-wrapper');
            if (iconWrapper) {
                iconWrapper.style.transform = 'scale(1.1) rotate(5deg)';
                iconWrapper.style.transition = 'transform 0.3s ease';
            }
        });
        
        item.addEventListener('mouseleave', function() {
            const iconWrapper = this.querySelector('.download-icon-wrapper');
            if (iconWrapper) {
                iconWrapper.style.transform = 'scale(1) rotate(0deg)';
            }
        });
    });
    
    // ===================================
    // Navigation Scroll Effect
    // ===================================
    
    const navbar = document.getElementById('navbar');
    
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
    
    // ===================================
    // Console Message
    // ===================================
    
    console.log('%cDownloads Page Loaded', 'font-size: 16px; font-weight: bold; color: #6366f1;');
    
});
