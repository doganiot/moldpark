// ========================================
// MOLDPARK - MODERN JAVASCRIPT v4.0
// Enhanced User Experience & Performance
// ========================================

class MoldParkApp {
    constructor() {
        this.init();
    }

    init() {
        try {
            this.setupEventListeners();
            this.initializeComponents();
            this.setupAnimations();
            this.setupPerformanceOptimizations();
            
            // Initialize new enhanced features
            this.initDashboardInteractions();
            this.initEnhancedFormValidation();
            this.initKeyboardShortcuts();
            this.initAudioContext();
            this.initPerformanceMonitoring();
            
            console.log('✅ MoldPark uygulaması tüm özelliklerle başlatıldı');
        } catch (error) {
            console.error('MoldPark initialization error:', error);
        }
    }

    initializeComponents() {
        // Komponent başlatma işlemleri
        console.log('MoldPark components initialized');
    }

    setupEventListeners() {
        // Güvenli event listener kurulumu
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initBootstrapComponents();
                this.setupCustomFeatures();
                this.setupNavbarEffects();
                this.setupFormEnhancements();
                this.setupNotificationSystem();
            });
        } else {
            // DOM zaten yüklü
            this.initBootstrapComponents();
            this.setupCustomFeatures();
            this.setupNavbarEffects();
            this.setupFormEnhancements();
            this.setupNotificationSystem();
        }

        // Navbar scroll effect
        if (typeof window !== 'undefined') {
            window.addEventListener('scroll', this.throttle(this.handleNavbarScroll.bind(this), 16));
            
            // Resize handler
            window.addEventListener('resize', this.debounce(this.handleResize.bind(this), 250));
        }
    }

    setupNavbarEffects() {
        // Navbar efektleri
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            console.log('Navbar effects initialized');
        }
    }

    // ========================================
    // BOOTSTRAP COMPONENTS
    // ========================================
    
    initBootstrapComponents() {
        // Initialize tooltips with better performance
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
            new bootstrap.Tooltip(tooltipTriggerEl, {
                trigger: 'hover focus',
                delay: { show: 500, hide: 100 }
            })
        );

        // Initialize popovers
        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        const popoverList = [...popoverTriggerList].map(popoverTriggerEl => 
            new bootstrap.Popover(popoverTriggerEl, {
                trigger: 'click',
                placement: 'auto'
            })
        );

    }

    // ========================================
    // NAVBAR EFFECTS
    // ========================================
    
    handleNavbarScroll() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        const scrolled = window.scrollY > 20;
        navbar.classList.toggle('scrolled', scrolled);
    }

    // ========================================
    // FORM ENHANCEMENTS
    // ========================================
    
    setupFormEnhancements() {
        // Enhanced form validation
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this), false);
            
            // Real-time validation
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', this.validateField.bind(this));
                input.addEventListener('input', this.debounce(this.validateField.bind(this), 300));
            });
        });

        // File upload enhancements
        this.setupFileUploads();
        
        // Progress indicators
        this.setupProgressBars();
    }

    handleFormSubmit(event) {
        const form = event.target;
        
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            
            // Focus first invalid field
            const firstInvalid = form.querySelector(':invalid');
            if (firstInvalid) {
                firstInvalid.focus();
                this.showFieldError(firstInvalid, 'Lütfen bu alanı doğru şekilde doldurun.');
            }
        } else {
            // Show loading state
            this.showFormLoading(form);
        }
        
            form.classList.add('was-validated');
    }

    validateField(event) {
        const field = event.target;
        const isValid = field.checkValidity();
        
        this.toggleFieldValidation(field, isValid);
        
        if (!isValid) {
            this.showFieldError(field, field.validationMessage);
        } else {
            this.hideFieldError(field);
        }
    }

    toggleFieldValidation(field, isValid) {
        field.classList.toggle('is-valid', isValid);
        field.classList.toggle('is-invalid', !isValid);
    }

    showFieldError(field, message) {
        let errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            field.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    hideFieldError(field) {
        const errorDiv = field.parentNode.querySelector('.invalid-feedback');
        if (errorDiv) {
            errorDiv.remove();
        }
    }

    showFormLoading(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="loading-spinner me-2"></span>Gönderiliyor...';
            submitBtn.disabled = true;
            
            submitBtn.dataset.originalText = originalText;
        }
    }

    // ========================================
    // FILE UPLOAD ENHANCEMENTS
    // ========================================
    
    setupFileUploads() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', this.handleFileUpload.bind(this));
            this.createFileDropZone(input);
        });
    }

    handleFileUpload(event) {
        const input = event.target;
        const files = input.files;
        
        if (files.length === 0) return;
        
        const file = files[0];
        this.displayFileInfo(input, file);
        this.validateFile(input, file);
    }

    displayFileInfo(input, file) {
        const fileName = file.name;
        const fileSize = this.formatFileSize(file.size);
        const fileType = file.type;
        
        let infoDiv = input.parentNode.querySelector('.file-info');
                if (!infoDiv) {
                    infoDiv = document.createElement('div');
            infoDiv.className = 'file-info mt-2 p-3 bg-light border rounded';
                    input.parentNode.appendChild(infoDiv);
                }
                
                infoDiv.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="me-3">
                    <i class="fas fa-file-alt fa-2x text-primary"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-bold">${fileName}</div>
                    <small class="text-muted">${fileSize} • ${fileType}</small>
                </div>
                <div class="ms-3">
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.parentNode.parentNode.parentNode.remove(); this.parentNode.parentNode.parentNode.previousElementSibling.value = '';">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    }

    validateFile(input, file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
        
        let isValid = true;
        let errorMessage = '';
        
        if (file.size > maxSize) {
            isValid = false;
            errorMessage = 'Dosya boyutu 10MB\'dan büyük olamaz.';
        } else if (!allowedTypes.includes(file.type)) {
            isValid = false;
            errorMessage = 'Sadece JPG, PNG, GIF ve PDF dosyaları kabul edilir.';
        }
        
        this.toggleFieldValidation(input, isValid);
        
        if (!isValid) {
            this.showFieldError(input, errorMessage);
        } else {
            this.hideFieldError(input);
        }
    }

    createFileDropZone(input) {
        const dropZone = document.createElement('div');
        dropZone.className = 'file-drop-zone border-2 border-dashed rounded p-4 text-center';
        dropZone.innerHTML = `
            <i class="fas fa-cloud-upload-alt fa-3x text-muted mb-3"></i>
            <p class="mb-2">Dosyayı buraya sürükleyin veya tıklayın</p>
            <small class="text-muted">Maksimum 10MB • JPG, PNG, GIF, PDF</small>
        `;
        
        input.parentNode.insertBefore(dropZone, input);
        input.style.display = 'none';
        
        dropZone.addEventListener('click', () => input.click());
        dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        dropZone.addEventListener('drop', this.handleDrop.bind(this, input));
    }

    handleDragOver(event) {
        event.preventDefault();
        event.target.classList.add('border-primary', 'bg-light');
    }

    handleDrop(input, event) {
        event.preventDefault();
        const dropZone = event.target;
        dropZone.classList.remove('border-primary', 'bg-light');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            this.handleFileUpload({ target: input });
        }
    }

    // ========================================
    // PROGRESS BARS & ANIMATIONS
    // ========================================
    
    setupProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateProgressBar(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        progressBars.forEach(bar => observer.observe(bar));
    }

    animateProgressBar(bar) {
        const targetWidth = bar.getAttribute('aria-valuenow') + '%';
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.width = targetWidth;
        }, 100);
    }

    // ========================================
    // SMOOTH SCROLLING & ANIMATIONS
    // ========================================
    
    setupAnimations() {
        // Intersection Observer for animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in-up');
                }
            });
        }, observerOptions);
        
        // Observe elements for animation
        const animatedElements = document.querySelectorAll('.card, .feature-card, .alert');
        animatedElements.forEach(el => observer.observe(el));
        
        // Setup smooth scrolling
        this.initSmoothScrolling();
    }

    initSmoothScrolling() {
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        
        anchorLinks.forEach(link => {
            const href = link.getAttribute('href');
            
                if (href && href.length > 1 && href !== '#' && /^#[a-zA-Z][\w-]*$/.test(href)) {
                link.addEventListener('click', (e) => {
                        try {
                        const targetElement = document.getElementById(href.substring(1));
                            if (targetElement) {
                                e.preventDefault();
                                targetElement.scrollIntoView({
                                    behavior: 'smooth',
                                    block: 'start'
                                });
                            }
                    } catch (error) {
                        console.error('Scroll error:', error);
                        }
                    });
                }
            });
    }

    // ========================================
    // NOTIFICATION SYSTEM
    // ========================================
    
    setupNotificationSystem() {
        // Mark notification as read
        const notificationLinks = document.querySelectorAll('.notification-item');
        notificationLinks.forEach(link => {
            link.addEventListener('click', this.handleNotificationClick.bind(this));
        });
        
        // Mark all as read
        const markAllBtn = document.getElementById('mark-all-read');
        if (markAllBtn) {
            markAllBtn.addEventListener('click', this.markAllNotificationsRead.bind(this));
        }
    }

    handleNotificationClick(event) {
        const link = event.target.closest('.notification-item');
        const notificationId = link.dataset.notificationId;
        
        if (notificationId) {
            this.markNotificationRead(notificationId);
        }
    }

    markNotificationRead(notificationId) {
        fetch(`/center/notifications/${notificationId}/read/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateNotificationBadge(data.unread_count);
            }
        })
        .catch(error => console.error('Notification error:', error));
    }

    markAllNotificationsRead() {
        fetch('/center/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.updateNotificationBadge(0);
                location.reload();
            }
        })
        .catch(error => console.error('Mark all error:', error));
    }

    updateNotificationBadge(count) {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline-flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    // ========================================
    // CUSTOM FEATURES
    // ========================================
    
    setupCustomFeatures() {
        // Loading buttons
        this.setupLoadingButtons();
        
        // Counter animations
        this.setupCounterAnimations();
        
        // Search functionality
        this.setupSearchFilters();
        
        // Theme toggle (if needed)
        this.setupThemeToggle();
    }

    setupLoadingButtons() {
        const loadingButtons = document.querySelectorAll('.btn-loading');
        loadingButtons.forEach(button => {
            button.addEventListener('click', () => {
                const originalText = button.innerHTML;
                button.innerHTML = '<span class="loading-spinner me-2"></span>Yükleniyor...';
                button.disabled = true;
                
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }, 3000);
            });
        });
    }

    setupCounterAnimations() {
        const counters = document.querySelectorAll('.stat-counter');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(counter => observer.observe(counter));
    }

    animateCounter(element) {
        const target = parseInt(element.textContent);
        const duration = 2000;
        const step = target / (duration / 16);
        let current = 0;
        
        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }

    setupSearchFilters() {
        const searchInputs = document.querySelectorAll('[data-search-target]');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        });
    }

    handleSearch(event) {
        const input = event.target;
        const searchTerm = input.value.toLowerCase();
        const targetSelector = input.dataset.searchTarget;
        const targets = document.querySelectorAll(targetSelector);
        
        targets.forEach(target => {
            const text = target.textContent.toLowerCase();
            const shouldShow = text.includes(searchTerm);
            target.style.display = shouldShow ? '' : 'none';
        });
    }

    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', this.toggleTheme.bind(this));
            
            // Load saved theme
            const savedTheme = localStorage.getItem('moldpark-theme');
            if (savedTheme) {
                document.body.classList.toggle('dark-theme', savedTheme === 'dark');
            }
        }
    }

    toggleTheme() {
        const isDark = document.body.classList.toggle('dark-theme');
        localStorage.setItem('moldpark-theme', isDark ? 'dark' : 'light');
    }

    // ========================================
    // PERFORMANCE OPTIMIZATIONS
    // ========================================
    
    setupPerformanceOptimizations() {
        // Lazy loading for images
        this.setupLazyLoading();
        
        // Preload critical resources
        this.preloadCriticalResources();
        
        // Service worker registration (if available)
        this.registerServiceWorker();
    }

    setupLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for older browsers
            images.forEach(img => {
                img.src = img.dataset.src;
            });
        }
    }

    preloadCriticalResources() {
        const criticalResources = [
            '/static/css/custom.css',
            '/static/js/custom.js'
        ];
        
        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = resource.endsWith('.css') ? 'style' : 'script';
            link.href = resource;
            document.head.appendChild(link);
        });
    }

    registerServiceWorker() {
        // Service Worker GEÇİCİ OLARAK DEVRE DIŞI
        // Network hatalarını önlemek için development sırasında kapatıldı
        if ('serviceWorker' in navigator) {
            // Mevcut service worker'ları kaldır
            navigator.serviceWorker.getRegistrations().then(registrations => {
                registrations.forEach(registration => {
                    registration.unregister();
                    console.log('✅ Service Worker kaldırıldı (development mode)');
                });
            });
        }
        
        // Service Worker kaydı devre dışı (production'da açılacak)
        /*
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
                .then(registration => {
                    console.log('SW registered:', registration);
                })
                .catch(error => {
                    console.log('SW registration failed:', error);
                });
        }
        */
    }

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================
    
    getCsrfToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
            
        return cookieValue || '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function executedFunction(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    handleResize() {
        // Handle responsive changes
        const isMobile = window.innerWidth < 768;
        document.body.classList.toggle('mobile-view', isMobile);
        
        // Trigger custom resize event
        document.dispatchEvent(new CustomEvent('moldpark:resize', {
            detail: { isMobile, width: window.innerWidth }
        }));
    }

    // Dashboard Card Interactions
    initDashboardInteractions() {
        const dashboardCards = document.querySelectorAll('.dashboard-card, .quick-action-card, .status-card');
        
        dashboardCards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                this.playHoverSound();
                card.style.setProperty('--hover-scale', '1.02');
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.removeProperty('--hover-scale');
            });
            
            // Add ripple effect on click
            card.addEventListener('click', (e) => {
                this.createRippleEffect(e, card);
            });
        });
    }
    
    // Create Ripple Effect
    createRippleEffect(event, element) {
        const ripple = document.createElement('div');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: radial-gradient(circle, rgba(79, 70, 229, 0.3) 0%, transparent 70%);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
            z-index: 1;
        `;
        
        // Add ripple animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(2);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
        
        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
            if (element.querySelectorAll('.ripple').length === 0) {
                document.head.removeChild(style);
            }
        }, 600);
    }
    
    // Notification System
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification-popup ${type}`;
        notification.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="notification-icon me-3">
                    <i class="fas fa-${this.getNotificationIcon(type)} fa-lg"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="notification-message">${message}</div>
                    <div class="notification-progress">
                        <div class="progress" style="height: 2px;">
                            <div class="progress-bar bg-${type}" role="progressbar" style="width: 100%"></div>
                        </div>
                    </div>
                </div>
                <button class="btn-close btn-close-sm ms-2" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Auto hide
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, duration);
        
        // Progress bar animation
        const progressBar = notification.querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.transition = `width ${duration}ms linear`;
            setTimeout(() => progressBar.style.width = '0%', 100);
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    // Loading Overlay
    showLoading(message = 'Yükleniyor...') {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="text-center">
                <div class="loading-spinner-enhanced mb-3"></div>
                <div class="loading-message fw-semibold text-gray-700">${message}</div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        setTimeout(() => overlay.classList.add('show'), 50);
        
        return {
            hide: () => {
                overlay.classList.remove('show');
                setTimeout(() => overlay.remove(), 300);
            },
            updateMessage: (newMessage) => {
                const messageEl = overlay.querySelector('.loading-message');
                if (messageEl) messageEl.textContent = newMessage;
            }
        };
    }
    
    // Enhanced Form Validation
    initEnhancedFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            
            inputs.forEach(input => {
                // Real-time validation
                input.addEventListener('blur', () => this.validateField(input));
                input.addEventListener('input', () => {
                    if (input.classList.contains('is-invalid')) {
                        this.validateField(input);
                    }
                });
                
                // Enhanced focus effects
                input.addEventListener('focus', () => {
                    input.parentElement.classList.add('field-focused');
                });
                
                input.addEventListener('blur', () => {
                    input.parentElement.classList.remove('field-focused');
                });
            });
            
            // Form submission with loading
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !form.querySelector('.is-invalid')) {
                    this.setButtonLoading(submitBtn);
                }
            });
        });
    }
    
    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';
        
        // Required validation
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = 'Bu alan zorunludur';
        }
        
        // Email validation
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                message = 'Geçerli bir email adresi giriniz';
            }
        }
        
        // Phone validation
        if (field.type === 'tel' && value) {
            const phoneRegex = /^[\+]?[0-9\s\-\(\)]{10,}$/;
            if (!phoneRegex.test(value)) {
                isValid = false;
                message = 'Geçerli bir telefon numarası giriniz';
            }
        }
        
        // Update field state
        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            this.removeFieldError(field);
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            this.showFieldError(field, message);
        }
        
        return isValid;
    }
    
    showFieldError(field, message) {
        this.removeFieldError(field);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback d-block';
        errorDiv.textContent = message;
        
        field.parentElement.appendChild(errorDiv);
    }
    
    removeFieldError(field) {
        const existingError = field.parentElement.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }
    }
    
    setButtonLoading(button, loadingText = 'Yükleniyor...') {
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            ${loadingText}
        `;
        
        // Store original text for restoration
        button.dataset.originalText = originalText;
    }
    
    restoreButton(button) {
        if (button.dataset.originalText) {
            button.innerHTML = button.dataset.originalText;
            button.disabled = false;
            delete button.dataset.originalText;
        }
    }
    
    // Sound Effects (optional)
    playHoverSound() {
        // Only play if user has interacted with the page
        if (this.audioContext && this.audioContext.state === 'running') {
            try {
                const oscillator = this.audioContext.createOscillator();
                const gainNode = this.audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(this.audioContext.destination);
                
                oscillator.frequency.setValueAtTime(800, this.audioContext.currentTime);
                gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.1);
                
                oscillator.start(this.audioContext.currentTime);
                oscillator.stop(this.audioContext.currentTime + 0.1);
            } catch (e) {
                // Ignore audio errors
            }
        }
    }
    
    initAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume context on user interaction
            document.addEventListener('click', () => {
                if (this.audioContext.state === 'suspended') {
                    this.audioContext.resume();
                }
            }, { once: true });
        } catch (e) {
            // Audio not supported
            console.log('Web Audio API not supported');
        }
    }
    
    // Advanced Performance Monitoring
    initPerformanceMonitoring() {
        // Monitor page load performance
        window.addEventListener('load', () => {
            setTimeout(() => {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    const loadTime = perfData.loadEventEnd - perfData.loadEventStart;
                    console.log(`Sayfa yükleme süresi: ${loadTime}ms`);
                    
                    // Show warning if load time is too high
                    if (loadTime > 3000) {
                        this.showNotification(
                            'Sayfa yükleme süresi yavaş. İnternet bağlantınızı kontrol edin.',
                            'warning',
                            3000
                        );
                    }
                }
            }, 1000);
        });
        
        // Monitor memory usage (if available)
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const usedPercent = (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100;
                
                if (usedPercent > 80) {
                    console.warn('Yüksek bellek kullanımı tespit edildi');
                }
            }, 30000);
        }
    }
    
    // Keyboard Shortcuts
    initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K for search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('input[type="search"], input[name="search"]');
                if (searchInput) {
                    searchInput.focus();
                    this.showNotification('Arama alanı aktif edildi', 'info', 2000);
                }
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    const modal = bootstrap.Modal.getInstance(openModal);
                    if (modal) modal.hide();
                }
            }
        });
    }
}

// ========================================
// INITIALIZE APPLICATION
// ========================================

// Güvenli uygulama başlatma
function initMoldParkApp() {
    try {
        if (typeof window !== 'undefined' && !window.moldparkApp) {
            window.moldparkApp = new MoldParkApp();
            console.log('MoldPark App successfully initialized');
        }
    } catch (error) {
        console.error('Failed to initialize MoldPark App:', error);
    }
}

// Initialize app when DOM is ready
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMoldParkApp);
    } else {
        initMoldParkApp();
    }
}

// Export for modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MoldParkApp;
} 