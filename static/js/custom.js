// MoldPark Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // Güvenli JSON parse fonksiyonu
    function safeJsonParse(response) {
        try {
            // Önce response'un JSON olup olmadığını kontrol et
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Response is not JSON');
            }
            return response.json();
        } catch (error) {
            console.error('JSON parse error:', error);
            throw new Error('JSON parse failed: ' + error.message);
        }
    }

    // Güvenli fetch fonksiyonu
    function safeFetch(url, options = {}) {
        return fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                // Content-Type kontrolü
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json();
                } else {
                    // JSON değilse text olarak al
                    return response.text().then(text => {
                        // Eğer HTML ise hata fırlat
                        if (text.includes('<!DOCTYPE') || text.includes('<html')) {
                            throw new Error('Unexpected HTML response instead of JSON');
                        }
                        return { success: false, message: 'Invalid response format' };
                    });
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                return { success: false, message: error.message };
            });
    }

    // Tooltip'leri etkinleştir
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Popover'ları etkinleştir
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation enhancement
    var forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // File upload preview
    var fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var file = e.target.files[0];
            if (file) {
                var fileName = file.name;
                var fileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';
                
                // Create or update file info display
                var infoDiv = input.parentNode.querySelector('.file-info');
                if (!infoDiv) {
                    infoDiv = document.createElement('div');
                    infoDiv.className = 'file-info mt-2';
                    input.parentNode.appendChild(infoDiv);
                }
                
                infoDiv.innerHTML = `
                    <small class="text-muted">
                        <i class="fas fa-file me-1"></i>
                        ${fileName} (${fileSize})
                    </small>
                `;
            }
        });
    });

    // Progress bar animation
    var progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(function(bar) {
        var width = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
        bar.style.width = '0%';
        setTimeout(function() {
            bar.style.width = width;
        }, 100);
    });

    // Smooth scroll for anchor links - Güvenli versiyon
    function initSmoothScrolling() {
        try {
            var anchorLinks = document.querySelectorAll('a[href^="#"]');
            
            anchorLinks.forEach(function(link) {
                var href = link.getAttribute('href');
                
                // Sadece geçerli ID selector'ları için işlem yap
                if (href && href.length > 1 && href !== '#' && /^#[a-zA-Z][\w-]*$/.test(href)) {
                    link.addEventListener('click', function(e) {
                        try {
                            var targetElement = document.getElementById(href.substring(1));
                            if (targetElement) {
                                e.preventDefault();
                                targetElement.scrollIntoView({
                                    behavior: 'smooth',
                                    block: 'start'
                                });
                            }
                        } catch (scrollError) {
                            console.error('Scroll error for:', href, scrollError);
                        }
                    });
                }
            });
        } catch (error) {
            console.error('Smooth scrolling initialization error:', error);
        }
    }
    
    // Güvenli başlatma
    initSmoothScrolling();

    // Loading state for buttons
    var loadingButtons = document.querySelectorAll('.btn-loading');
    loadingButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            var originalText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Yükleniyor...';
            this.disabled = true;
            
            // Re-enable after 3 seconds (adjust as needed)
            setTimeout(function() {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
        });
    });

    // CSRF Token alma fonksiyonu
    function getCsrfToken() {
        var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            return csrfToken.value;
        }
        // Cookie'den al
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue || '';
    }

    // Bildirim sistemi
    function updateNotificationBadge(count) {
        var badge = document.querySelector('.notification-badge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    // Tüm bildirimleri okundu işaretle
    var markAllReadBtn = document.getElementById('mark-all-read');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            safeFetch(this.href, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(data => {
                if (data.success) {
                    updateNotificationBadge(0);
                    // Dropdown'u kapat
                    var dropdown = bootstrap.Dropdown.getInstance(document.getElementById('navbarDropdown'));
                    if (dropdown) dropdown.hide();
                    // Sayfayı yenile
                    location.reload();
                } else {
                    console.error('Operation failed:', data.message);
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    // Tekli bildirim okundu işaretle
    document.querySelectorAll('.notification-item').forEach(function(item) {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            var notificationId = this.getAttribute('data-notification-id');
            
            safeFetch(this.href, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(data => {
                if (data.success) {
                    // Badge sayısını azalt
                    var currentBadge = document.querySelector('.notification-badge');
                    if (currentBadge) {
                        var currentCount = parseInt(currentBadge.textContent) || 0;
                        updateNotificationBadge(Math.max(0, currentCount - 1));
                    }
                    // Bu bildirimi listeden kaldır
                    this.closest('li').remove();
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm-delete') || 'Bu işlemi gerçekleştirmek istediğinizden emin misiniz?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Auto-save form data to localStorage
    var autoSaveForms = document.querySelectorAll('.auto-save');
    autoSaveForms.forEach(function(form) {
        var formId = form.id || 'auto-save-form';
        
        // Load saved data
        var savedData = localStorage.getItem(formId);
        if (savedData) {
            try {
                var data = JSON.parse(savedData);
                Object.keys(data).forEach(function(key) {
                    var input = form.querySelector(`[name="${key}"]`);
                    if (input && input.type !== 'file') {
                        input.value = data[key];
                    }
                });
            } catch (e) {
                console.log('Error loading saved form data:', e);
            }
        }
        
        // Save data on input
        form.addEventListener('input', function() {
            var formData = new FormData(form);
            var data = {};
            for (var [key, value] of formData.entries()) {
                if (form.querySelector(`[name="${key}"]`).type !== 'file') {
                    data[key] = value;
                }
            }
            localStorage.setItem(formId, JSON.stringify(data));
        });
        
        // Clear saved data on successful submit
        form.addEventListener('submit', function() {
            localStorage.removeItem(formId);
        });
    });

    // Table sorting
    var sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(function(header) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            var table = this.closest('table');
            var tbody = table.querySelector('tbody');
            var rows = Array.from(tbody.querySelectorAll('tr'));
            var index = Array.from(this.parentNode.children).indexOf(this);
            var isAscending = this.classList.contains('sort-asc');
            
            // Remove existing sort classes
            sortableHeaders.forEach(function(h) {
                h.classList.remove('sort-asc', 'sort-desc');
            });
            
            // Add new sort class
            this.classList.add(isAscending ? 'sort-desc' : 'sort-asc');
            
            // Sort rows
            rows.sort(function(a, b) {
                var aText = a.children[index].textContent.trim();
                var bText = b.children[index].textContent.trim();
                
                // Try to parse as numbers
                var aNum = parseFloat(aText);
                var bNum = parseFloat(bText);
                
                if (!isNaN(aNum) && !isNaN(bNum)) {
                    return isAscending ? bNum - aNum : aNum - bNum;
                } else {
                    return isAscending ? bText.localeCompare(aText) : aText.localeCompare(bText);
                }
            });
            
            // Reorder rows
            rows.forEach(function(row) {
                tbody.appendChild(row);
            });
        });
    });

    // Sayaç animasyonu
    function animateCounters() {
        const counters = document.querySelectorAll('.stat-counter');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const counter = entry.target;
                    const text = counter.textContent;
                    const number = text.match(/\d+/);
                    if (number) {
                        const finalNumber = parseInt(number[0]);
                        const icon = counter.querySelector('i');
                        const iconClass = icon ? icon.className : '';
                        
                        let currentNumber = 0;
                        const increment = finalNumber / 50;
                        const timer = setInterval(() => {
                            currentNumber += increment;
                            if (currentNumber >= finalNumber) {
                                currentNumber = finalNumber;
                                clearInterval(timer);
                            }
                            counter.innerHTML = icon ? 
                                `<i class="${iconClass}"></i>${Math.floor(currentNumber)}${text.includes('+') ? '+' : ''}${text.includes('.') ? '.8' : ''}` :
                                `${Math.floor(currentNumber)}${text.includes('+') ? '+' : ''}${text.includes('.') ? '.8' : ''}`;
                        }, 40);
                    }
                    observer.unobserve(counter);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(counter => observer.observe(counter));
    }

    // Kalıp kartları hover efekti
    document.querySelectorAll('.mold-type-card').forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Sayaç animasyonunu başlat
    if (document.querySelector('.stat-counter')) {
        animateCounters();
    }

    console.log('MoldPark JavaScript initialized successfully!');
});

// Utility functions
window.MoldPark = {
    showToast: function(message, type = 'info') {
        var toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        var toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        var bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },
    
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        var k = 1024;
        var sizes = ['Bytes', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    formatDate: function(date) {
        return new Intl.DateTimeFormat('tr-TR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
}; 