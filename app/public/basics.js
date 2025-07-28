// ----- Funções reusáveis -----

// Pegar CSRF token da meta tag
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

function getUserId() {
	return document.querySelector('meta[name="validated"]').getAttribute('content');
}

function checkAuthenticationStatus() {
	return getUserId() === "None" ? false: true;
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

// Popup de login
// Cria e exibe um popup de login no documento.
function showLoginPopup(onLoginSuccess, originalClickEvent = null, extraArgs = undefined) {
    // Verifica se o modal já existe para evitar duplicação
    if (document.getElementById('__loginModal')) {
        const existingModal = document.getElementById('__loginModal');
        existingModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        return; // Sai da função se o modal já está na DOM
    }

    const popupHtml = `
        <div id="__loginModal" class="fixed inset-0 flex items-center justify-center z-10000 modal-overlay">
            <div class="bg-white p-8 rounded-lg shadow-xl w-96 modal-content relative">
                <h2 class="text-3xl font-semibold text-gray-800 mb-6 text-center">Login</h2>

                <form id="__loginForm">
                    <div class="mb-5">
                        <label for="login" class="block text-gray-700 text-sm font-medium mb-2">Login</label>
                        <input type="text" id="__login" name="login" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Seu nome de usuário ou e-mail" required>
                    </div>

                    <div class="mb-6 relative">
                        <label for="password" class="block text-gray-700 text-sm font-medium mb-2">Senha</label>
                        <input type="password" id="__password" name="password" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 pr-10" placeholder="Sua senha" required>
                        <span class="absolute inset-y-0 right-0 pr-3 flex items-center cursor-pointer mt-7" id="__togglePassword">
                            <i class="fas fa-eye text-gray-500" id="__eyeIcon"></i>
                        </span>
                    </div>

                    <button type="submit" class="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition duration-300 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50">Entrar</button>
                </form>

                <p class="text-center text-gray-600 text-sm mt-6">
                    Não tem uma conta? <a href="/registrar" id="__registerLink" class="text-blue-600 hover:underline font-medium">Registre-se.</a>
                </p>

                <button id="__closeModal" class="absolute top-4 right-4 text-gray-500 hover:text-gray-700 text-2xl focus:outline-none">
                    &times;
                </button>
            </div>
        </div>
    `;

    // Adiciona o HTML do popup ao body
    document.body.insertAdjacentHTML('beforeend', popupHtml);

    // Seleciona os elementos recém-adicionados
    const loginModal = document.getElementById('__loginModal');
    const closeModalBtn = document.getElementById('__closeModal');
    const togglePassword = document.getElementById('__togglePassword');
    const passwordInput = document.getElementById('__password');
    const eyeIcon = document.getElementById('__eyeIcon');
    const loginForm = document.getElementById('__loginForm');
    const registerLink = document.getElementById('__registerLink');

    // Funções auxiliares para abrir e fechar
    const openModal = () => {
        loginModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    };

    const closeModal = () => {
        loginModal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    };

    // Event Listeners
    closeModalBtn.addEventListener('click', closeModal);

    loginModal.addEventListener('click', (e) => {
        if (e.target === loginModal) {
            closeModal();
        }
    });

    togglePassword.addEventListener('click', () => {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        eyeIcon.classList.toggle('fa-eye');
        eyeIcon.classList.toggle('fa-eye-slash');
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault(); // Previne o envio padrão do formulário
        const login = document.getElementById('__login').value;
        const password = document.getElementById('__password').value;

		// Limpar mensagens de erro anteriores, se houver
		const oldErrorMessages = loginForm.querySelectorAll('.error-message');
        oldErrorMessages.forEach(msg => msg.remove());
        loginForm.querySelectorAll('input').forEach(input => input.classList.remove('border-red-500'));

        const result = await sendApiRequest('/login_ajax', 'POST', {login: login, password: password});
		if (result.success) {
				closeModal();
				if (extraArgs) {
					onLoginSuccess(extraArgs);
				} else {
					onLoginSuccess(originalClickEvent);
				}
            } else {
				if (result.errors) {
					for (const fieldName in result.errors) {
						const messages = result.errors[fieldName];
						const inputElement = document.getElementById(`__${fieldName}`);
						if (inputElement) {
							inputElement.classList.add('border-red-500');
							messages.forEach(msg => {
								const errorMessage = document.createElement('p');
								errorMessage.className = 'text-red-500 text-xs mt-1 error-message';
								errorMessage.textContent = msg;
								inputElement.parentNode.appendChild(errorMessage);
							});
						}
					}
				} else {
					console.log('Erro: ' + result.message);
					const errorMessageDiv = document.createElement('div');
					errorMessageDiv.className = 'text-red-500 text-sm mt-3 text-center error-message';
					errorMessageDiv.textContent = result.message || 'Erro desconhecido.';
					loginForm.appendChild(errorMessageDiv);
				}
            }
    });

    registerLink.addEventListener('click', (e) => {
        e.preventDefault();
        closeModal();
		window.location.href = '/registrar';
    });

    // Abre o modal logo após ser renderizado
    openModal();
}

// Inicializa a funcionalidade do popup de login para botões que exigem autenticação.
function initializeAuthButtons(_button, isAuthenticatedCheck, popupSuccessCallback, extraArgs = null) {
    _button.addEventListener('click', (event) => {
		event.preventDefault(); // Previne a ação padrão do botão, se houver

		if (!isAuthenticatedCheck()) {
			showLoginPopup(popupSuccessCallback, event, extraArgs);
		} else {
			popupSuccessCallback(event, extraArgs);
		}
    });
}

// Dropdown
const reusableDropdown = document.getElementById('reusableDropdown');
const dropdownContent = document.getElementById('dropdownContent');
let currentActiveButton = null; // Para rastrear qual botão abriu o dropdown

function showReusableDropdown(buttonElement, options, dataAttributes = {}) {	
	hideReusableDropdown(); // Esconder dropdown existente se estiver visível

	currentActiveButton = buttonElement; // Armazena o botão ativo

	dropdownContent.innerHTML = ''; // Limpa conteúdo anterior

	options.forEach(option => {
		const item = document.createElement('a');
		item.href = '#';
		item.className = 'block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 whitespace-nowrap';
		item.textContent = option.text;
		
		initializeAuthButtons(
			item,
			checkAuthenticationStatus,
			option.action,
			dataAttributes
		);
		dropdownContent.appendChild(item);
	});
	
	const rect = buttonElement.getBoundingClientRect();
	reusableDropdown.style.top = `${rect.bottom + window.scrollY + 5}px`;
	reusableDropdown.style.left = `${rect.left + window.scrollX}px`;

	// Ajustar para garantir que o dropdown não saia da tela à direita
	const dropdownWidth = reusableDropdown.offsetWidth;
	if (rect.left + dropdownWidth > window.innerWidth) {
		reusableDropdown.style.left = `${rect.right + window.scrollX - dropdownWidth}px`;
	}
	reusableDropdown.classList.remove('hidden');
}

function hideReusableDropdown() {
	reusableDropdown.classList.add('hidden');
	currentActiveButton = null;
}

// Fechar o dropdown ao clicar fora dele
document.addEventListener('click', (event) => {
	if (reusableDropdown && !reusableDropdown.contains(event.target) && event.target !== currentActiveButton && !currentActiveButton?.contains(event.target)) {
		hideReusableDropdown();
	}
});

// Fechar o dropdown ao rolar a página
window.addEventListener('scroll', hideReusableDropdown);
window.addEventListener('resize', hideReusableDropdown);

async function deletePost(_, data) {
	if (confirm(`Tem certeza que deseja deletar o post de ID: ${data.target_id}?`)) {
		try {
			const response = await sendApiRequest(`/api/post/${data.target_id}/delete`, 'POST', {});

			if (response.success) {
				location.reload();
			} else {
				alert('Falha ao deletar: ' + (response.message || 'Erro desconhecido.'));
				console.error('Falha ao deletar:', response.errors || response.message);
			}
		} catch (error) {
			console.error('Erro ao deletar post:', error);
			alert('Erro ao deletar post.');
		}
	}
}

async function deleteInteraction(_, data) {
	if (confirm(`Tem certeza que deseja deletar a interação de ID: ${data.target_id}?`)) {
		try {
			const response = await sendApiRequest(`/api/interaction/${data.target_id}/delete`, 'POST', {});

			if (response.success) {
				location.reload();
			} else {
				alert('Falha ao deletar: ' + (response.message || 'Erro desconhecido.'));
				console.error('Falha ao deletar:', response.errors || response.message);
			}
		} catch (error) {
			console.error('Erro ao deletar interação:', error);
			alert('Erro ao deletar interação.');
		}
	}
}

function reportItem(_, data) {
    showReportPopup(data);
}

function followUser(_, data) {
	console.log(`Seguir Usuário ID: ${data.userId} (Username: ${data.username})`);
	alert(`Seguindo ${data.username}!`);
	// Lógica para enviar requisição de seguir
}

function blockUser(_, data) {
	if (confirm(`Tem certeza que deseja bloquear o Usuário ID: ${data.userId} (Username: ${data.username})?`)) {
		console.log(`Bloquear Usuário ID: ${data.userId} (Username: ${data.username})`);
		alert(`Bloqueando ${data.username}!`);
		// Lógica para enviar requisição de bloqueio
	}
}

function sendMessage(_, data) {
	console.log(`Enviar mensagem para Usuário ID: ${data.userId} (Username: ${data.username})`);
	alert(`Abrindo chat com ${data.username}.`);
	// Lógica para abrir chat
}

function optionButton(event) {
	const parentElement = event.currentTarget.closest('.comment-item, .post-container, .profile-card'); // Encontra o pai mais próximo que identifica o item
	let options = [];
	let data = {};

	if (parentElement.classList.contains('post-container')) { // Para posts
		const postId = parentElement.dataset.postid;
		const ownerId = parentElement.dataset.postUserid;

		data = { target_id: postId, type: 'post', perpetrator_id: ownerId };
		
		if (getUserId() === ownerId) {
			options = [
				{ text: 'Deletar Post', action: deletePost }
			];
		} else {
			options = [
				{ text: 'Denunciar', action: reportItem }
			];
		}

	} else if (parentElement.classList.contains('profile-card')) { // Para usuários
		const userId = parentElement.dataset.userId;

		data = { target_id: userId, type: 'usuario', perpetrator_id: userId };

		options = [
			{ text: 'Denunciar', action: reportItem }//,
			//{ text: 'Seguir', action: followUser },
			//{ text: 'Bloquear', action: blockUser },
			//{ text: 'Enviar Mensagem', action: sendMessage }
		];
	} else if (parentElement.classList.contains('comment-item')) { // Para comentários e respostas (interações)
		const interactionId = parentElement.dataset.commentId;
		const ownerId = parentElement.dataset.commentUserid;

		data = { target_id: interactionId, type: 'interacao', perpetrator_id: ownerId };

		if (getUserId() === ownerId) {
		 	options = [
		 		{ text: 'Deletar Comentário', action: deleteInteraction }
		 	];
		} else {
			options = [
				{ text: 'Denunciar', action: reportItem }
			];
		}
	}
	
	showReusableDropdown(event.currentTarget, options, data);
}

function attachOptionBtnListener(button) {
	button.addEventListener('click', (event) => {
		optionButton(event);
	});
}

document.addEventListener('DOMContentLoaded', () => {
	document.querySelectorAll('.options-button').forEach(button => {
		attachOptionBtnListener(button);
	});
});

// Popup de denúncia
const reportModal = document.getElementById('reportModal');
const closeReportModalBtn = document.getElementById('closeReportModal');
const reportForm = document.getElementById('reportForm');
const reportModalTitle = document.getElementById('reportModalTitle');

const reportStep1 = document.getElementById('reportStep1');
const nextReportStepBtn = document.getElementById('nextReportStep');
const reportCategoryRadios = document.querySelectorAll('input[name="reportCategory"]');

const reportStep2 = document.getElementById('reportStep2');
const backToReportStep1Btn = document.getElementById('backToReportStep1');
const reportDescriptionInput = document.getElementById('reportDescription');
const charCountSpan = document.getElementById('reportCharCount');
const submitReportBtn = document.getElementById('submitReport');

const reportSuccess = document.getElementById('reportSuccess');
const closeReportSuccessBtn = document.getElementById('closeReportSuccess');

let currentReportTargetData = {}; // Para armazenar o id do que está sendo denunciado

// Reseta o popup de denúncias para o estado inicial (primeira etapa).
function resetReportPopup() {
    reportModalTitle.textContent = "Denunciar";
    reportStep1.classList.remove('hidden');
    reportStep2.classList.add('hidden');
    reportSuccess.classList.add('hidden');

    // Limpa a seleção de rádio
    reportCategoryRadios.forEach(radio => radio.checked = false);

    // Limpa a descrição
    reportDescriptionInput.value = '';
    charCountSpan.textContent = '0';
}

// Exibe o popup de denúncias e inicializa a primeira etapa.
function showReportPopup(targetData) {
    currentReportTargetData = targetData; // Armazena os dados do item/usuário
    resetReportPopup(); // Reseta o popup para a primeira etapa
    reportModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

// Esconde o popup de denúncias.
function hideReportPopup() {
    reportModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
    resetReportPopup(); // Reseta ao fechar para que na próxima vez comece do zero
}

// Event Listeners Globais para o Popup de Denúncia
closeReportModalBtn.addEventListener('click', hideReportPopup);
reportModal.addEventListener('click', (e) => {
	if (e.target === reportModal) {
		hideReportPopup();
	}
});

nextReportStepBtn.addEventListener('click', () => {
    let selectedCategory = null;
    reportCategoryRadios.forEach(radio => {
        if (radio.checked) {
            selectedCategory = radio.value;
        }
    });

    if (selectedCategory) {
        reportStep1.classList.add('hidden');
        reportStep2.classList.remove('hidden');
        reportModalTitle.textContent = "Detalhes da Denúncia"; // Atualiza o título
    } else {
        alert('Por favor, selecione uma categoria para a denúncia.');
    }
});

backToReportStep1Btn.addEventListener('click', () => {
    reportStep2.classList.add('hidden');
    reportStep1.classList.remove('hidden');
    reportModalTitle.textContent = "Denunciar"; // Volta o título
});

reportDescriptionInput.addEventListener('input', () => {
    charCountSpan.textContent = reportDescriptionInput.value.length;
});

reportForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    let selectedCategory = null;
    reportCategoryRadios.forEach(radio => {
        if (radio.checked) {
            selectedCategory = radio.value;
        }
    });

    const description = reportDescriptionInput.value;

    // Constrói os dados da denúncia
    const reportData = {
        category: selectedCategory,
        description: description,
		type: currentReportTargetData['type'],
		target_id: currentReportTargetData['target_id'],
		perpetrator_id: currentReportTargetData['perpetrator_id']
    };

    try {
        const response = await sendApiRequest('/api/report', 'POST', reportData);

        if (response.success) {
            reportStep2.classList.add('hidden');
            reportSuccess.classList.remove('hidden');
            reportModalTitle.textContent = "Sucesso!";
        } else {
            alert('Falha ao enviar denúncia: ' + (response.message || 'Erro desconhecido.'));
            console.error('Erro ao enviar denúncia:', response.errors || response.message);
        }
    } catch (error) {
        console.error('Erro na requisição da denúncia:', error);
        alert('Erro de comunicação com o servidor ao enviar denúncia.');
    }
});
closeReportSuccessBtn.addEventListener('click', hideReportPopup);