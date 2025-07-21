// ----- Funções reusáveis -----

// Pegar CSRF token da meta tag
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Função genérica para enviar requisições AJAX
async function sendApiRequest(url, method, data) {
    const csrfToken = getCsrfToken();
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição API:', error);
        return { success: false, message: 'Erro de comunicação com o servidor.' };
    }
}

// Tamanho dinânimo de textarea
function adjustTextareaHeight(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

function resetTextarea(textarea) {
    textarea.value = '';
    textarea.style.height = 'auto';
}

// Marcar um elemento como ativo
function toggleActive(element) {
    if (element) {
        element.classList.toggle('active');
    }
}

// Formatar números
function formatNumber(num) {
    if (num >= 1000 && num < 1000000) {
        return (num / 1000).toFixed(1) + 'K';
    } else if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M'; // Não custa sonhar né
    }
    return num;
}

// Funções para Modais
function openModal(modalId, imageSrc = null) {
    const modal = document.getElementById(modalId);
    if (modalId === 'imageModal') {
        const fullImage = document.getElementById('fullImage');
        fullImage.src = imageSrc;
    }
    modal.classList.remove('hidden');
    modal.classList.add('is-visible');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('hidden');
    modal.classList.remove('is-visible');
    
    if (modalId === 'replyModal') {
        resetTextarea(document.getElementById('replyTextarea'));
        toggleReplyButton();
    }
}

// Notificações
function toggleNotification(id, message = "Carregando") {
    const container = document.getElementById('notificationContainer');
    if (!container) {
        const newContainer = document.createElement('div');
        newContainer.id = 'notification';
        document.body.appendChild(newContainer);
    }

    const existingNotification = document.getElementById(`Notif${id}`);
    if (existingNotification) {
        const fadeOut = existingNotification.animate([
            { opacity: 1 },
            { opacity: 0 }
        ], {
            duration: 300,
            easing: 'ease-out',
            fill: 'forwards'
        });

        fadeOut.onfinish = () => {
            existingNotification.remove();
        };
    } else {
        const newNotification = document.createElement('div');
        newNotification.id = `Notif${id}`;
        newNotification.innerHTML = `<p id="popupMessage">${message}${message == "Carregando" ? ' <i class="fa-solid fa-spinner fa-spin"></i>' : ''}</p>`;
        container.appendChild(newNotification);
    }
}

function toggleLoading(object) {
    const hasSpinner = object.querySelector('.loading-spinner');
    if (hasSpinner) {
        hasSpinner.remove();
    } else {
        const spinner = document.createElement('span');
        spinner.className = 'loading-spinner';
        spinner.innerHTML = ' <i class="fa-solid fa-spinner fa-spin"></i>';
        object.appendChild(spinner);
    }
}