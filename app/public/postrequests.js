// Abre a interface de respostas e armazena o ID do comentário a ser respondido
function openRepliesModal(parentCommentId) {
    const replyModal = document.getElementById('replyModal');
    replyModal.dataset.parentCommentId = parentCommentId; 

    openModal('replyModal');
}

// Compartilhamento
function copyPostUrl() {
    const dummy = document.createElement('textarea');
    const postUrl = window.location.href;
    document.body.appendChild(dummy);
    dummy.value = postUrl;
    dummy.select();
    document.execCommand('copy');
    document.body.removeChild(dummy);
    alert('URL do post copiada para a área de transferência!');
    document.getElementById('shareContextMenu').classList.add('hidden'); // Fecha o menu após copiar
}

// --- Funções de Comentário ---

function toggleCommentButton() {
    const textarea = document.getElementById('commentTextarea');
    const button = document.getElementById('commentButton');
    if (textarea.value.trim().length > 0) {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }
}

function toggleReplyButton() {
    const textarea = document.getElementById('replyTextarea');
    const button = document.getElementById('replyButton');
    if (textarea.value.trim().length > 0) {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }
}

// Atualiza visualmentet uma reação, removendo a oposta e incrementando a atual
function visualReactionUpdate(selfType, oppositeType) { 
    const oppositeCount = document.getElementById(oppositeType + "Count");
    const selfCount = document.getElementById(selfType + "Count");

    const opposite = document.getElementById(oppositeType + "Button");
    if (opposite.classList.contains('active')) { // Se a reação oposta estiver ativa....
        oppositeCount.textContent = Number(oppositeCount.textContent) - 1; // Na hora de converter os valores de 1000 pra 1k isso não vai funcionar mais, então talvez seja necessário criar um data-quanitity pra saber o valor numérico
        opposite.classList.remove('active'); // Caso o botão de deslike esteja ativado :P
    }
    selfCount.textContent = Number(selfCount.textContent) + 1;
}

// ---- Requisições ----
// Helpers e auxiliares
// Helper para curtida de comentários
async function handleCommentReaction(commentId, reactionType) {
    const data = { reaction_type: reactionType };
    const result = await sendApiRequest(`/api/comments/${commentId}/react`, 'POST', data);

    if (result.success) {
        await updateCommentCounts(commentId);
    } else {
        alert('Erro: ' + result.message);
    }
}

// Função para atualizar contagens e estado dos botões de post
async function updatePostCounts(postId) {
    const response = await fetch(`/api/posts/${postId}/counts`);
    const data = await response.json();
    if (data.success) {
        document.getElementById('likeCount').textContent = data.likes;
        document.getElementById('dislikeCount').textContent = data.dislikes;

        const likeButton = document.getElementById('likeButton');
        const dislikeButton = document.getElementById('dislikeButton');

        // Remove as classes ativas antes de adicionar, para garantir o estado correto
        likeButton.classList.remove('active');
        dislikeButton.classList.remove('active');

        if (data.user_reaction === 'like_post') {
            likeButton.classList.add('active');
        } else if (data.user_reaction === 'dislike_post') {
            dislikeButton.classList.add('active');
        }
    }
}

// Função para atualizar contagens e estado dos comentários
async function updateCommentCounts(commentId) {
    const response = await fetch(`/api/comments/${commentId}/counts`);
    const data = await response.json();
    if (data.success) {
        const commentItem = document.querySelector(`.comment-item[data-comment-id="${commentId}"]`);
        if (commentItem) {
            commentItem.querySelector('.comment-like-count').textContent = data.likes;
            commentItem.querySelector('.comment-dislike-count').textContent = data.dislikes;
            
            const likeButton = commentItem.querySelector('.comment-like-button');
            const dislikeButton = commentItem.querySelector('.comment-dislike-button');

            if (dislikeButton && likeButton) {
                likeButton.classList.remove('active');
                dislikeButton.classList.remove('active');

                if (data.user_reaction === 'like_comment') {
                    likeButton.classList.add('active');
                } else if (data.user_reaction === 'dislike_comment') {
                    dislikeButton.classList.add('active');
                }
            }
        }
    }
}

// Função auxiliar para renderizar um único comentário e suas respostas
function renderComment(comment_content) {
    const commentLikeActiveClass = comment_content.user_reaction === 'like_comment' ? 'active' : '';
    const commentDislikeActiveClass = comment_content.user_reaction === 'dislike_comment' ? 'active' : '';

    let html = `
        <div class="comment-item flex gap-4 mb-6" data-comment-id="${comment_content.comment.id}">
            <div class="comment-profile-pic">
                <i class="fa-solid fa-user"></i>
            </div>
            <div class="flex-grow">
                <div id="interaction${comment_content.comment.id}box">
                    <p class="font-semibold text-gray-800 mb-1">${comment_content.comment.username}</p>
                    <p class="text-gray-700 mb-2">${comment_content.comment.value}</p>
                    <div class="flex items-center gap-4 text-sm text-gray-500">
                        <button class="interaction-button comment-like-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${commentLikeActiveClass}" id="interaction${comment_content.comment.id}likeButton">
                            <i class="fa-solid fa-thumbs-up"></i> <span class="comment-like-count" id="interaction${comment_content.comment.id}likeCount">${comment_content.likes}</span>
                        </button>
                        <button class="interaction-button comment-dislike-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${commentDislikeActiveClass}" id="interaction${comment_content.comment.id}dislikeButton">
                            <i class="fa-solid fa-thumbs-down"></i> <span class="comment-dislike-count" id="interaction${comment_content.comment.id}dislikeCount">${comment_content.dislikes}</span>
                        </button>
                        <button class="interaction-button comment-reply-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500" onclick="openRepliesModal('${comment_content.comment.id}')">
                            <i class="fa-solid fa-reply"></i>
                        </button>
                        <button class="interaction-button comment-save-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500">
                            <i class="fa-solid fa-bookmark"></i>
                        </button>
                    </div>
                </div>
    `;
    if (comment_content.most_liked_reply) {
        const replyLikeActiveClass = comment_content.reply_user_reaction === 'like_comment' ? 'active' : '';
        const replyDislikeActiveClass = comment_content.reply_user_reaction === 'dislike_comment' ? 'active' : '';

        html += `
            <div class="comment-item flex gap-4 mt-4 comment-reply" data-comment-id="${comment_content.most_liked_reply.reply.id}">
                <div class="comment-profile-pic">
                    <i class="fa-solid fa-user"></i>
                </div>
                <div class="flex-grow">
                    <p class="font-semibold text-gray-800 mb-1">${comment_content.most_liked_reply.reply.username}</p>
                    <p class="text-gray-700 mb-2">${comment_content.most_liked_reply.reply.value}</p>
                    <div class="flex items-center gap-4 text-sm text-gray-500">
                        <button class="interaction-button comment-like-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${replyLikeActiveClass}" id="interaction${comment_content.most_liked_reply.reply.id}likeButton">
                            <i class="fa-solid fa-thumbs-up"></i> <span class="comment-like-count" id="interaction${comment_content.most_liked_reply.reply.id}likeCount">${comment_content.most_liked_reply.likes}</span>
                        </button>
                        <button class="interaction-button comment-dislike-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${replyDislikeActiveClass}" id="interaction${comment_content.most_liked_reply.reply.id}dislikeButton">
                            <i class="fa-solid fa-thumbs-down"></i> <span class="comment-dislike-count" id="interaction${comment_content.most_liked_reply.reply.id}dislikeCount">${comment_content.most_liked_reply.dislikes}</span>
                        </button>
                        <button class="interaction-button comment-reply-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500" onclick="openRepliesModal('${comment_content.most_liked_reply.reply.id}')">
                            <i class="fa-solid fa-reply"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    if (comment_content.total_replies > 1) {
        html += `
            <button class="interaction-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500" onclick="openCommentModal('${comment_content.comment.id}')">
                Ver mais ${comment_content.total_replies - 1} respostas
            </button>`
    }
    html += `</div></div>`;
    return html;
}

// Função auxiliar para renderizar uma resposta a um comentário
function renderReply(reply_content) {
    const replyLikeActiveClass = reply_content.user_reaction === 'like_comment' ? 'active' : '';
    const replyDislikeActiveClass = reply_content.user_reaction === 'dislike_comment' ? 'active' : '';

    let html = `
        <div class="comment-item flex gap-4 mt-4 comment-reply" data-comment-id="${reply_content.reply.id}">
            <div class="comment-profile-pic">
                <i class="fa-solid fa-user"></i>
            </div>
            <div class="flex-grow">
                <p class="font-semibold text-gray-800 mb-1">${reply_content.reply.username}</p>
                <p class="text-gray-700 mb-2">${reply_content.reply.value}</p>
                <div class="flex items-center gap-4 text-sm text-gray-500">
                    <button class="interaction-button comment-like-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${replyLikeActiveClass}" id="interaction${reply_content.reply.id}likeButton">
                        <i class="fa-solid fa-thumbs-up"></i> <span class="comment-like-count" id="interaction${reply_content.reply.id}likeCount">${reply_content.likes}</span>
                    </button>
                    <button class="interaction-button comment-dislike-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500 ${replyDislikeActiveClass}" id="interaction${reply_content.reply.id}dislikeButton">
                        <i class="fa-solid fa-thumbs-down"></i> <span class="comment-dislike-count" id="interaction${reply_content.reply.id}dislikeCount">${reply_content.dislikes}</span>
                    </button>
                    <button class="interaction-button comment-reply-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500" onclick="openRepliesModal('${reply_content.reply.id}')">
                        <i class="fa-solid fa-reply"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    return html;
}

async function openCommentModal(commentId) {
    const commentModalContent = document.getElementById('commentModalContent');
    commentModalContent.innerHTML = 'Carregando...'; // Mensagem de carregamento

    openModal('commentModal');

    try {
        const request = await fetch(`/api/posts/${postId}/comment/${commentId}/replies`);
        const result = await request.json();

        if (result.success) {
            commentModalContent.innerHTML = '';
            
            // Busca o comentário original
            const originalComment = document.getElementById(`interaction${commentId}box`);
            if (originalComment) {
                commentModalContent.appendChild(originalComment.cloneNode(true)); // Clona o comentário original

            }

            // Adiciona as respostas ao modal
            result.replies.forEach(reply => {
                commentModalContent.innerHTML += renderReply(reply); // Use uma função separada para renderizar respostas
            });
            attachCommentEventListeners(); // Anexa os event listeners
        } else {
            commentModalContent.innerHTML = 'Erro ao carregar respostas.';
        }
    } catch (error) {
        console.log(error);
        commentModalContent.innerHTML = 'Erro de conexão.';
    }
}

function attachCommentEventListeners() {
    document.getElementById('commentModalContent').addEventListener('click', function(event) {
        const clickedButton = event.target.closest('.comment-like-button, .comment-dislike-button, .comment-reply-button');

        if (clickedButton) {
            const commentItem = clickedButton.closest('.comment-item');
            const commentId = commentItem ? commentItem.dataset.commentId : null;

            if (clickedButton.classList.contains('comment-reply-button')) {
                openRepliesModal(commentId);
            } else {
                if (clickedButton.classList.contains('comment-like-button')) {
                    handleCommentReaction(commentId, 'like_comment');
                } else if (clickedButton.classList.contains('comment-dislike-button')) {
                    handleCommentReaction(commentId, 'dislike_comment');
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    // Fecha modais ao clicar fora
    document.addEventListener('click', function(event) {
        // Fechar modal de imagem
        const imageModal = document.getElementById('imageModal');
        if (imageModal && imageModal.classList.contains('is-visible') && !imageModal.querySelector('.modal-content').contains(event.target) && event.target.id === 'imageModal') {
            closeModal('imageModal');
        }
        
        // Fechar modal de resposta
        const replyModal = document.getElementById('replyModal');
        if (replyModal && replyModal.classList.contains('is-visible') && !replyModal.querySelector('.reply-modal-content').contains(event.target) && event.target.id === 'replyModal') {
            closeModal('replyModal');
        }

        // Fechar o menu de compartilhamento se clicar fora de ambos os elementos
        const shareContextMenu = document.getElementById('shareContextMenu');
        const shareButton = document.getElementById('shareButton');
        if (shareContextMenu && !shareContextMenu.classList.contains('hidden') && !shareContextMenu.contains(event.target) && event.target !== shareButton) {
            shareContextMenu.classList.add('hidden');
        }
    });

    // Fecha modais ao pressionar a tecla ESC
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeModal('imageModal');
            closeModal('replyModal');
        }
    });

    // --- Funções de Interatividade dos Botões Principais (Like, Dislike, Salvar) ---

    document.getElementById('saveButton').addEventListener('click', function() {
        toggleActive(this);
        console.log('Botão Salvar do Post clicado!');
        // Lógica de backend aqui
    });

    // --- Compartilhamento ---
    document.getElementById('shareButton').addEventListener('click', function(event) {
        event.stopPropagation(); // Evita que o clique se propague para o document e feche o menu imediatamente
        const contextMenu = document.getElementById('shareContextMenu');
        contextMenu.classList.toggle('hidden');
    });

    // Evento de clique para os botões de resposta dos comentários
    document.getElementById('commentsSection').addEventListener('click', function(event) {
        const clickedButton = event.target.closest('.comment-like-button, .comment-dislike-button, .comment-save-button, .comment-reply-button');

        if (clickedButton) {
            const commentItem = clickedButton.closest('.comment-item');
            const commentId = commentItem ? commentItem.dataset.commentId : null; // Eu acho esse forma de if else muito funny

            if (clickedButton.classList.contains('comment-reply-button')) {
                openRepliesModal(commentId); // Resposta de comentário
            } else {
                toggleActive(clickedButton);

                if (clickedButton.classList.contains('comment-like-button')) {
                    visualReactionUpdate(`interaction${commentId}like`, `interaction${commentId}dislike`); // Like
                    handleCommentReaction(commentId, 'like_comment');
                } else if (clickedButton.classList.contains('comment-dislike-button')) {
                    visualReactionUpdate(`interaction${commentId}dislike`, `interaction${commentId}like`); // Deslike
                    handleCommentReaction(commentId, 'dislike_comment');
                } else if (clickedButton.classList.contains('comment-save-button')) {
                    // Lógica para salvar comentário
                    alert(`Botão Salvar Comentário ${commentId} clicado! (Lógica backend a ser implementada)`);
                }
            }
        }
    });

    document.getElementById('commentTextarea').addEventListener('input', toggleCommentButton);
    document.getElementById('replyTextarea').addEventListener('input', toggleReplyButton);

    // Dar like em um post
    document.getElementById('likeButton').addEventListener('click', async function() {
        toggleActive(this); 
        visualReactionUpdate('like', 'dislike');

        const data = { reaction_type: 'like_post' };
        const result = await sendApiRequest(`/api/posts/${postId}/react`, 'POST', data);
        if (result.success) {
            updatePostCounts(postId);
        } else {
            alert('Erro durante a reação, nenhuma alteração foi feita: ' + result.message);
        }
    });

    // Dar deslike em um post
    document.getElementById('dislikeButton').addEventListener('click', async function() {

        toggleActive(this); 
        visualReactionUpdate('dislike', 'like');
        
        const data = { reaction_type: 'dislike_post' };
        const result = await sendApiRequest(`/api/posts/${postId}/react`, 'POST', data);
        if (result.success) {
            updatePostCounts(postId);
        } else {
            alert('Erro durante a reação, nenhuma alteração foi feita: ' + result.message);
        }
    });

    // Publicar um comentário no post
    document.getElementById('commentButton').addEventListener('click', async function() {
        if (this.classList.contains('active')) {
            const commentText = document.getElementById('commentTextarea').value.trim();

            resetTextarea(document.getElementById('commentTextarea'));
            toggleCommentButton();
            toggleLoading(this);
            
            const data = { comment_text: commentText };
            const result = await sendApiRequest(`/api/posts/${postId}/comment`, 'POST', data);
            if (result.success) {
                const commentSection = document.getElementById("commentsSection");
                commentSection.innerHTML = renderComment(result.comment_content) + commentSection.innerHTML; // Adiciona o novo comentário no início da seção... Bem feito nas coxa, eu sei.
            } else {
                alert('Erro: ' + result.message);
            }
            toggleLoading(this);
        }
    });

    // Publicar uma resposta a um comentário
    document.getElementById('replyButton').addEventListener('click', async function() {
        if (this.classList.contains('active')) {
            const replyText = document.getElementById('replyTextarea').value.trim();
            const parentCommentId = document.getElementById('replyModal').dataset.parentCommentId; 
            
            if (!parentCommentId) {
                alert("Erro: ID do comentário pai não encontrado.");
                return;
            }

            let notifId = Date.now();
            toggleNotification(notifId);
            closeModal('replyModal');

            const data = { reply_text: replyText };
            const result = await sendApiRequest(`/api/comments/${parentCommentId}/reply`, 'POST', data);
            if (result.success) {
                const parentCommentBox = document.getElementById(`interaction${parentCommentId}box`);
                const replyHTML = renderReply(result.reply_content);
                parentCommentBox.insertAdjacentHTML('afterend', replyHTML);
            } else {
                alert('Erro: ' + result.message);
            }
            toggleNotification(notifId);
        }
    });

    // Carregar mais comentários
    const loadMoreButton = document.getElementById('loadMoreComments');
    if (loadMoreButton) {
        loadMoreButton.addEventListener('click', async function() {
            let notifId = Date.now();
            toggleNotification(notifId);

            try {
                const request = await fetch(`/api/posts/${postId}/comments?offset=${rendered_comments}&limit=10`);
                const result = await request.json();

                if (result.success) {
                    const commentsSection = document.getElementById('commentsSection');
                    result.comments.forEach(comment => {
                        commentsSection.innerHTML += renderComment(comment); // Adiciona cada comentário
                    });

                    rendered_comments += 5; // Incrementa o número de comentários a serem carregados
                    // Verifica se todos os comentários foram carregados
                    if (total_comments <= rendered_comments) {
                        this.style.display = 'none'; // Esconde o botão se não houver mais comentários
                    }
                } else {
                    alert('Erro ao carregar mais comentários: ' + result.message);
                }
            } catch (error) {
                commentModalContent.innerHTML = 'Erro de conexão.';
            }
            toggleNotification(notifId);
        });
    }

    document.querySelectorAll('textarea').forEach(textarea => {
        resetTextarea(textarea);
    });
    
    toggleCommentButton();
    toggleReplyButton();
});