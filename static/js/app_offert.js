// Smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing app...');
    
    // Handle smooth scrolling for navigation links
    const navLinks = document.querySelectorAll('.nav__link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href.startsWith('#')) {
                e.preventDefault();
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Handle "Rozpocznij za darmo" button
    const startTrialBtn = document.getElementById('startTrialBtn');
    console.log('Start trial button found:', startTrialBtn);
    
    if (startTrialBtn) {
        startTrialBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Start trial button clicked');
            alert('Świetnie! Za chwilę zostaniesz przekierowany do rejestracji i rozpoczniesz 30-dniowy okres próbny za darmo.\n\nPo zarejestrowaniu otrzymasz dostęp do pełnego systemu zarządzania kalendarzem i rezerwacjami.');
            
            // In a real application, this would redirect to registration page
            // window.location.href = '/register';
        });
    } else {
        console.error('Start trial button not found!');
    }

    // Handle "Dowiedz się więcej" button
    const learnMoreBtn = document.getElementById('learnMoreBtn');
    console.log('Learn more button found:', learnMoreBtn);
    
    if (learnMoreBtn) {
        learnMoreBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Learn more button clicked');
            // Scroll to benefits section
            const benefitsSection = document.getElementById('korzyści');
            if (benefitsSection) {
                benefitsSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    } else {
        console.error('Learn more button not found!');
    }

    // Handle pricing plan button - use more specific selector
    const pricingButtons = document.querySelectorAll('.pricing__card .btn');
    console.log('Pricing buttons found:', pricingButtons.length);
    
    pricingButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Pricing button clicked');
            alert('Doskonały wybór! Za chwilę zostaniesz przekierowany do rejestracji.\n\nPamiętaj: pierwsze 30 dni są całkowicie za darmo, bez żadnych zobowiązań.');
            
            // In a real application, this would redirect to registration page
            // window.location.href = '/register';
        });
    });

    // Also handle any button with specific text content as fallback
    const allButtons = document.querySelectorAll('button, .btn');
    allButtons.forEach(button => {
        const buttonText = button.textContent.trim();
        
        if (buttonText === 'Rozpocznij za darmo' && !button.hasAttribute('data-handled')) {
            button.setAttribute('data-handled', 'true');
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Fallback: Start trial button clicked');
                alert('Świetnie! Za chwilę zostaniesz przekierowany do rejestracji i rozpoczniesz 30-dniowy okres próbny za darmo.\n\nPo zarejestrowaniu otrzymasz dostęp do pełnego systemu zarządzania kalendarzem i rezerwacjami.');
            });
        }
        
        if (buttonText === 'Wybierz plan' && !button.hasAttribute('data-handled')) {
            button.setAttribute('data-handled', 'true');
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Fallback: Choose plan button clicked');
                alert('Doskonały wybór! Za chwilę zostaniesz przekierowany do rejestracji.\n\nPamiętaj: pierwsze 30 dni są całkowicie za darmo, bez żadnych zobowiązań.');
            });
        }
        
        if (buttonText === 'Dowiedz się więcej' && !button.hasAttribute('data-handled')) {
            button.setAttribute('data-handled', 'true');
            button.addEventListener('click', function(e) {
                e.preventDefault();
                console.log('Fallback: Learn more button clicked');
                const benefitsSection = document.getElementById('korzyści');
                if (benefitsSection) {
                    benefitsSection.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        }
    });

    // Add animation on scroll for benefit cards
    const observeCards = () => {
        const cards = document.querySelectorAll('.benefit-card');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        cards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
    };

    // Initialize animations if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        observeCards();
    } else {
        // Fallback for older browsers - just show all cards
        const cards = document.querySelectorAll('.benefit-card');
        cards.forEach(card => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        });
    }

    // Add hover effect to pricing card
    const pricingCard = document.querySelector('.pricing__card');
    if (pricingCard) {
        pricingCard.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.02)';
            this.style.transition = 'transform 0.3s ease';
        });
        
        pricingCard.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    }

    // Add simple analytics tracking simulation
    const trackEvent = (eventName, elementId) => {
        console.log(`Event tracked: ${eventName} on ${elementId}`);
        // In a real application, this would send data to analytics service
        // gtag('event', eventName, { element_id: elementId });
    };

    // Track button clicks
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('btn') || e.target.tagName === 'BUTTON') {
            const buttonText = e.target.textContent.trim();
            trackEvent('button_click', buttonText);
        }
    });

    // Track section views
    const sections = document.querySelectorAll('section[id]');
    if ('IntersectionObserver' in window && sections.length > 0) {
        const sectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    trackEvent('section_view', entry.target.id);
                }
            });
        }, {
            threshold: 0.5
        });

        sections.forEach(section => {
            sectionObserver.observe(section);
        });
    }

    // Simple form validation helper (for future use)
    const validateEmail = (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    // Expose utility functions globally if needed
    window.umowzdalnieUtils = {
        validateEmail,
        trackEvent
    };

    console.log('App initialization complete');
});