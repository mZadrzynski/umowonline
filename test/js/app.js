document.addEventListener('DOMContentLoaded', function() {
    // Smooth scrolling for anchor links
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Handle CTA button clicks
    const ctaButtons = document.querySelectorAll('.btn--primary');
    ctaButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Add loading state
            const originalText = this.textContent;
            this.textContent = 'Przekierowywanie...';
            this.disabled = true;
            
            // Simulate redirect to signup process
            setTimeout(() => {
                // In a real application, this would redirect to the actual signup page
                alert('🎉 Świetnie! Za chwilę przekierujemy Cię na stronę rejestracji, gdzie założysz swój darmowy kalendarz na 30 dni.\n\nPamiętaj: Pierwsze 30 dni to 0 PLN, potem tylko 20 PLN/miesiąc. Możesz zrezygnować w każdej chwili!');
                
                // Reset button
                this.textContent = originalText;
                this.disabled = false;
            }, 1500);
        });
    });

    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe sections for scroll animations
    const sections = document.querySelectorAll('.features, .pricing, .benefits, .cta');
    sections.forEach(section => {
        observer.observe(section);
    });

    // Add scroll-triggered counter animation for pricing
    const priceElement = document.querySelector('.currency');
    if (priceElement) {
        const observePricing = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(priceElement, 20, 1000);
                    observePricing.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });
        
        observePricing.observe(document.querySelector('.pricing-card'));
    }

    // Counter animation function
    function animateCounter(element, target, duration) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }

    // Add sticky header background on scroll
    const header = document.querySelector('.header');
    let lastScrollTop = 0;

    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add/remove background based on scroll position
        if (scrollTop > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        // Hide/show header on scroll direction (optional enhancement)
        if (scrollTop > lastScrollTop && scrollTop > 200) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }
        lastScrollTop = scrollTop;
    });

    // Add parallax effect to hero section
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallaxSpeed = 0.5;
            hero.style.transform = `translateY(${scrolled * parallaxSpeed}px)`;
        });
    }

    // Form validation and handling (if forms are added later)
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    // Add hover effects for feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Add typing effect to hero title (optional enhancement)
    const heroTitle = document.querySelector('.hero-text h1');
    if (heroTitle) {
        const text = heroTitle.textContent;
        heroTitle.textContent = '';
        let i = 0;
        
        // Only run typing effect on desktop
        if (window.innerWidth > 768) {
            const typeTimer = setInterval(() => {
                if (i < text.length) {
                    heroTitle.textContent += text.charAt(i);
                    i++;
                } else {
                    clearInterval(typeTimer);
                }
            }, 50);
        } else {
            // On mobile, just show the text immediately
            heroTitle.textContent = text;
        }
    }

    // Track user interactions for analytics (placeholder)
    function trackEvent(eventName, eventData = {}) {
        console.log('Analytics Event:', eventName, eventData);
        // In production, this would integrate with Google Analytics or other tracking service
    }

    // Track CTA clicks
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn--primary')) {
            trackEvent('cta_click', {
                button_text: e.target.textContent,
                section: e.target.closest('section')?.className || 'unknown'
            });
        }
    });

    // Track scroll depth
    let maxScrollPercent = 0;
    window.addEventListener('scroll', () => {
        const scrollPercent = Math.round(
            (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100
        );
        
        if (scrollPercent > maxScrollPercent) {
            maxScrollPercent = scrollPercent;
            
            // Track milestones
            if (maxScrollPercent >= 25 && maxScrollPercent < 50) {
                trackEvent('scroll_depth', { percent: 25 });
            } else if (maxScrollPercent >= 50 && maxScrollPercent < 75) {
                trackEvent('scroll_depth', { percent: 50 });
            } else if (maxScrollPercent >= 75 && maxScrollPercent < 100) {
                trackEvent('scroll_depth', { percent: 75 });
            } else if (maxScrollPercent >= 100) {
                trackEvent('scroll_depth', { percent: 100 });
            }
        }
    });

    // Add loading states and micro-interactions
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('click', function() {
            this.classList.add('btn-loading');
            setTimeout(() => {
                this.classList.remove('btn-loading');
            }, 1500);
        });
    });

    // Initialize tooltips or help texts (if needed)
    const helpElements = document.querySelectorAll('[data-help]');
    helpElements.forEach(element => {
        element.addEventListener('mouseenter', function() {
            // Show tooltip functionality could be added here
        });
    });
});

// Add CSS for dynamic classes via JavaScript
const dynamicStyles = `
    .header {
        transition: all 0.3s ease;
    }
    
    .header.scrolled {
        background-color: rgba(var(--color-surface), 0.95);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-md);
    }
    
    .animate-in {
        animation: slideInUp 0.8s ease-out;
    }
    
    .btn-loading {
        opacity: 0.7;
        pointer-events: none;
    }
    
    .btn-loading::after {
        content: '';
        width: 16px;
        height: 16px;
        margin-left: 8px;
        border: 2px solid transparent;
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        display: inline-block;
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
    
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
`;

// Inject dynamic styles
const styleSheet = document.createElement('style');
styleSheet.textContent = dynamicStyles;
document.head.appendChild(styleSheet);