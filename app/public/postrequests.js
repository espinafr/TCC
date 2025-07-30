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
    } else if (modalId === 'postModal') {
        const postModalContent = document.querySelector('.post-modal-content');
        postModalContent.innerHTML = ''; 
    }
}

// Abre a interface de respostas e armazena o ID do comentário a ser respondido
function openRepliesModal(parentCommentId, customId = "") {
    const replyModal = document.getElementById('replyModal');
    replyModal.dataset.parentCommentId = parentCommentId; 
    replyModal.dataset.parentCommentIdSufix = customId;

    openModal('replyModal');
}

// Compartilhamento
function copyPostUrl(postId) {
    const postUrl = window.location.origin + '/post/' + postId;
    const dummy = document.createElement('textarea');
    document.body.appendChild(dummy);
    dummy.value = postUrl;
    dummy.select();
    document.execCommand('copy');
    document.body.removeChild(dummy);
    alert('URL do post copiada para a área de transferência!');
}

// --- Funções de Comentário ---

function toggleCommentButton() {
    const textarea = document.getElementById('commentTextarea');
    const button = document.getElementById('commentButton');
    if (textarea.value.trim().length > 0) {
        button.classList.add('active', 'cursor-pointer');
    } else {
        button.classList.remove('active', 'cursor-pointer');
    }
}

function toggleReplyButton() {
    const textarea = document.getElementById('replyTextarea');
    const button = document.getElementById('replyButton');
    if (textarea.value.trim().length > 0) {
        button.classList.add('active', 'cursor-pointer');
    } else {
        button.classList.remove('active', 'cursor-pointer');
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

async function handlePostReaction(postId, reactionType) {
    const data = { reaction_type: reactionType };
    const result = await sendApiRequest(`/api/posts/${postId}/react`, 'POST', data);
    if (!result.success) {
        alert('Erro durante a reação, nenhuma alteração foi feita: ' + result.message);
    }
}

async function handleCommentReaction(commentId, reactionType) {
    const data = { reaction_type: reactionType };
    const result = await sendApiRequest(`/api/comments/${commentId}/react`, 'POST', data);

    if (!result.success) {
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
function renderComment(comment_content, postid) {
    const commentLikeActiveClass = comment_content.user_reaction === 'like_comment' ? 'active' : '';
    const commentDislikeActiveClass = comment_content.user_reaction === 'dislike_comment' ? 'active' : '';

    let html = `
        <div class="comment-item flex gap-4 mb-6" data-comment-id="${comment_content.comment.id}" data-comment-userid="${comment_content.comment.userid}">
            <div class="comment-profile-pic">
                ${ comment_content.comment.usericon ? '<img src='+comment_content.comment.usericon+' alt="Foto de perfil>" class="object-cover w-9 h-9 rounded-full">' : '<i class="fa-solid fa-user"></i>'}
            </div>
            <div class="flex-grow">
                <div id="interaction${comment_content.comment.id}box">
					<div class="flex justify-between">
                        <a class="font-semibold text-gray-800 mb-1 hover:underline" target="_blank" href="/usuario/${comment_content.comment.userid}">${comment_content.comment.username}</a>
						<button class="options-button self-start text-gray-500 pl-5 hover:text-blue-700 focus:outline-none"><i class="fas fa-ellipsis-v text-gl"></i></button>
					</div>
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
            <div class="comment-item flex gap-4 mt-4 comment-reply" data-comment-id="${comment_content.most_liked_reply.reply.id}" data-comment-userid="${comment_content.most_liked_reply.reply.userid}">
                <div class="comment-profile-pic">
                    ${ comment_content.most_liked_reply.reply.usericon ? '<img src='+comment_content.most_liked_reply.reply.usericon+' alt="Foto de perfil>" class="object-cover w-9 h-9 rounded-full">' : '<i class="fa-solid fa-user"></i>'}
                </div>
                <div class="flex-grow">
					<div class="flex justify-between">
						<a class="font-semibold text-gray-800 mb-1 hover:underline" target="_blank" href="/usuario/${comment_content.most_liked_reply.reply.userid}">${comment_content.most_liked_reply.reply.username}</a>
						<button class="options-button self-start text-gray-500 pl-5 hover:text-blue-700 focus:outline-none"><i class="fas fa-ellipsis-v text-gl"></i></button>
					</div>
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
            <button class="interaction-button px-2 py-1 bg-transparent hover:bg-blue-100 hover:text-blue-500" onclick="openCommentModal('${comment_content.comment.id}', '${postid}')">
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
        <div class="comment-item flex gap-4 mt-4 comment-reply" data-comment-id="${reply_content.reply.id}" data-comment-userid="${reply_content.reply.userid}">
            <div class="comment-profile-pic">
                ${ reply_content.reply.usericon ? '<img src='+reply_content.reply.usericon+' alt="Foto de perfil>" class="object-cover w-9 h-9 rounded-full">' : '<i class="fa-solid fa-user"></i>'}
            </div>
            <div class="flex-grow">
				<div class="flex justify-between">
                    <a class="font-semibold text-gray-800 mb-1 hover:underline" target="_blank" href="/usuario/${reply_content.reply.userid}">${reply_content.reply.username}</a>
					<button class="options-button self-start text-gray-500 pl-5 hover:text-blue-700 focus:outline-none"><i class="fas fa-ellipsis-v text-gl"></i></button>
				</div>
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

function renderPost(post_package) {
    // post: {
    //   id, title, content, tag, optional_tags, image_urls, created_at, author_user, user_post_reaction, likes, dislikes, comments, total_comments
    // }

    let optionalTagsHtml = '';
    if (post_package.post.optional_tags) {
        post_package.post.optional_tags.split(',').forEach(tag => {
            if (tag.trim()) {
                optionalTagsHtml += `<span class="bg-gray-300 text-gray-800 text-xs font-semibold px-3 py-1 rounded-full">${tag.trim().toUpperCase()}</span>`;
            }
        });
    }

    let imagesHtml = '';
    if (post_package.post.image_urls && post_package.post.image_urls.length > 0) {
        post_package.post.image_urls.forEach(image_url => {
            imagesHtml += `
                <div class="bg-gray-200 rounded-lg overflow-hidden flex items-center justify-center h-48 md:h-64 cursor-pointer hover:opacity-90 transition-opacity" onclick="openModal('imageModal', '${image_url}')">
                    <img src="${image_url}" alt="Imagem do Post" class="object-cover w-full h-full">
                </div>
            `;
        });
    }

    let commentsHtml = '';
    if (post_package.comments && post_package.comments.length > 0) {
        post_package.comments.forEach(comment_content => {
            commentsHtml += renderComment(comment_content, post_package.post.id); // Usa sua função já existente
        });
    }

    return `
    <div class="timeline-post post-container bg-white rounded-lg shadow-xl p-6 md:p-8 w-full max-w-3xl" data-postid="${post_package.post.id}" data-post-userid="${post_package.post.userid}">
        <div class="flex justify-right items-start mb-4">
            <h1 class="text-2xl md:text-3xl font-extrabold text-gray-900 flex-grow flex-shrink min-w-0 pr-4 break-words line-clamp-3">${post_package.post.title}</h1>
			<div class="flex items-center space-x-4">
				<span class="text-gray-500 text-sm md:text-base">
					${post_package.post.created_at}
				</span>
				<button class="options-button self-start text-gray-500 hover:text-blue-700 focus:outline-none">
					<i class="fas fa-ellipsis-v text-lg"></i>
				</button>
			</div>
        </div>
        <div class="flex flex-wrap gap-2 mb-6">
            <span class="bg-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full">${post_package.post.tag.toUpperCase()}</span>
            ${optionalTagsHtml}
        </div>
        <div class="post-content text-gray-700 leading-relaxed text-base md:text-lg mb-8">${post_package.post.content}</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            ${imagesHtml}
        </div>
        <div class="my-2 text-gray-600 text-sm">
            Postado por: <a href="/usuario/{{ post.author_user.user_id }}" class="font-semibold text-blue-500 hover:underline">${post_package.post.username || post_package.post.userat}</a>
        </div>
        <div class="flex items-center gap-4 border-t border-gray-200 pt-4 mb-8">
            <button class="interaction-button cursor-pointer ${post_package.user_post_reaction === 'like_post' ? 'active' : ''}" id="likeButton">
                <i class="fa-solid fa-thumbs-up"></i>
                <span id="likeCount">${post_package.likes}</span>
            </button>
            <button class="interaction-button cursor-pointer ${post_package.user_post_reaction === 'dislike_post' ? 'active' : ''}" id="dislikeButton">
                <i class="fa-solid fa-thumbs-down"></i>
                <span id="dislikeCount">${post_package.dislikes}</span>
            </button>
            <div class="relative shareContainer">
                <button class="interaction-button cursor-pointer shareButton" id="shareButton">
                    <i class="fa-solid fa-share-alt"></i>
                    <span>Compartilhar</span>
                </button>
                <div id="shareContextMenu" class="share-context-menu hidden">
                    <button onclick="copyPostUrl('${post_package.post.id}')" class="cursor-pointer">
                        <i class="fa-solid fa-copy"></i>
                        Copiar URL do Post
                    </button>
                </div>
            </div>
            <button class="interaction-button cursor-pointer" id="saveButton">
                <i class="fa-solid fa-bookmark"></i>
                <span>Salvar</span>
            </button>
        </div>
        <div class="comment-input-container mb-8">
            <div class="comment-profile-pic">
                ${ post_package.usericon ? '<img src='+post_package.usericon+' alt="Foto de perfil>" class="object-cover w-9 h-9 rounded-full">' : '<i class="fa-solid fa-user"></i>'}
            </div>
            <textarea id="commentTextarea" class="comment-textarea border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Escreva um comentário!" oninput="adjustTextareaHeight(this); toggleCommentButton();"></textarea>
            <button id="commentButton" class="comment-button">Comentar</button>
        </div>
        <div class="border-t border-blue-200 mb-8"></div>
        <div id="commentsSection">
            ${commentsHtml}
        </div>
        <div class="mt-8 text-center">
            ${post_package.total_comments - (post_package.comments ? post_package.comments.length : 0) > 0 ? `
            <button id="loadMoreComments" class="inline-block bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-full transition duration-300 ease-in-out">
                Carregar mais comentários
            </button>` : ''}
            <a href="/" class="inline-block cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-full transition duration-300 ease-in-out">
                Voltar para a página inicial
            </a>
        </div>
    </div>
    `;
}

let shareMenuOpen = false;
function attachShareEvent(btn) {
    btn.addEventListener('click', function(event) {
        event.stopPropagation(); // Evita que o clique se propague para o document e feche o menu imediatamente
        const postId = btn.closest('.post-container').dataset.postid;

        const contextMenu = document.getElementById(`shareContextMenu${postId}`);
        shareMenuOpen = true; // Sei que por causa do toggle ali em baixo, isso vai continuar marcando positivo mesmo se fechado, mas fazer assim é mais fácil do que fazer uma verificação... (por causa da função que fecha o menu)
        contextMenu.classList.toggle('hidden');
    });
}

function attachLikeEvent(btn) {
	initializeAuthButtons(
		btn,
		checkAuthenticationStatus,
		async () => {
			const postId = btn.closest('.post-container').dataset.postid;

			toggleActive(btn); 
			visualReactionUpdate(`like${postId}`, `dislike${postId}`);

			await handlePostReaction(postId, 'like_post');
		}
	);
}

function attachDislikeEvent(btn) {
	initializeAuthButtons(
		btn,
		checkAuthenticationStatus,
		async () => {
			const postId = btn.closest('.post-container').dataset.postid;

			toggleActive(btn); 
			visualReactionUpdate(`dislike${postId}`, `like${postId}`);

			await handlePostReaction(postId, 'dislike_post');
		}
	);
}

function attachCommentEventListeners() {
	initializeAuthButtons(
		document.getElementById('commentModalContent'),
		checkAuthenticationStatus,
		(event) => {
			const clickedButton = event.target.closest('.comment-like-button, .comment-dislike-button, .comment-reply-button');

			if (clickedButton) {
				const commentItem = clickedButton.closest('.comment-item');
				const commentId = commentItem ? commentItem.dataset.commentId : null;

				if (clickedButton.classList.contains('comment-reply-button')) {
					openRepliesModal(commentId, "modal");
				} else {
					if (clickedButton.classList.contains('comment-like-button')) {
						toggleActive(clickedButton);
						visualReactionUpdate(`interaction${commentId}like`, `interaction${commentId}dislike`);
						handleCommentReaction(commentId, 'like_comment');
					} else if (clickedButton.classList.contains('comment-dislike-button')) {
						toggleActive(clickedButton);
						visualReactionUpdate(`interaction${commentId}dislike`, `interaction${commentId}like`);
						handleCommentReaction(commentId, 'dislike_comment');
					}
				}
			}
		}
	);
}

function attachPostEventListeners(postId, total_comments, rendered_comments) {
    // Evento de clique para os botões de resposta dos comentários
	initializeAuthButtons(
		document.getElementById('commentsSection'),
		checkAuthenticationStatus,
		(event) => {
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
		}
	);

    document.getElementById('commentTextarea').addEventListener('input', toggleCommentButton);
    document.getElementById('replyTextarea').addEventListener('input', toggleReplyButton);

    // Publicar um comentário no post
    const commentButton = document.getElementById('commentButton');
	initializeAuthButtons(
		commentButton,
		checkAuthenticationStatus,
		async () => {
			if (commentButton.classList.contains('active')) {
				const commentText = document.getElementById('commentTextarea').value.trim();

				resetTextarea(document.getElementById('commentTextarea'));
				toggleCommentButton();
				toggleLoading(commentButton);
				
				const data = { comment_text: commentText };
				const result = await sendApiRequest(`/api/posts/${postId}/comment`, 'POST', data);
				if (result.success) {
					const commentSection = document.getElementById("commentsSection");
					commentSection.innerHTML = renderComment(result.comment_content, postId) + commentSection.innerHTML; // Adiciona o novo comentário no início da seção... Bem mal feito, eu sei.
				} else {
					alert('Erro: ' + result.message);
				}
				toggleLoading(commentButton);
			}
        }
	);

    // Publicar uma resposta a um comentário
    const replyButton = document.getElementById('replyButton');
	initializeAuthButtons(
		replyButton,
		checkAuthenticationStatus,
		async () => {
			if (replyButton.classList.contains('active')) {
				const replyText = document.getElementById('replyTextarea').value.trim();
				const parentCommentId = document.getElementById('replyModal').dataset.parentCommentId;
				const parentCommentIdSufix = document.getElementById('replyModal').dataset.parentCommentIdSufix;
				
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
					const parentCommentBox = document.getElementById(`interaction${parentCommentId}${parentCommentIdSufix}box`);
					const replyHTML = renderReply(result.reply_content);
					parentCommentBox.insertAdjacentHTML('afterend', replyHTML);
					parentCommentBox.parentNode.querySelector(`[data-comment-id="${result.reply_content.reply.id}"]`).onclick = optionButton;
				} else {
					alert('Erro: ' + result.message);
				}
				toggleNotification(notifId);
			}
		}
	);
    
    // Compartilhar
    document.getElementById('shareButton').addEventListener('click', () => {
        event.stopPropagation(); // Evita que o clique se propague para o document e feche o menu imediatamente
        const contextMenu = document.getElementById('shareContextMenu');
        shareMenuOpen = true;
        contextMenu.classList.toggle('hidden');
    });

    // Like
	const likeButton = document.getElementById('likeButton');
	initializeAuthButtons(
		likeButton,
		checkAuthenticationStatus,
		async () => {
			toggleActive(likeButton); 
			visualReactionUpdate(`like`, `dislike`);

			await handlePostReaction(postId, 'like_post');
		}
	);

    // Deslike
	const dislikeButton = document.getElementById('dislikeButton');
	initializeAuthButtons(
		dislikeButton,
		checkAuthenticationStatus,
		async () => {
			toggleActive(dislikeButton); 
			visualReactionUpdate(`dislike`, `like`);

			await handlePostReaction(postId, 'dislike_post');
		}
	);

	const postModal = document.getElementById('postModal')
	if (postModal) {
		postModal.querySelectorAll('.options-button').forEach(button => {
			attachOptionBtnListener(button);
		});
	}

    // Carregar mais comentários
    const loadMoreButton = document.getElementById('loadMoreComments');
    if (loadMoreButton) {
		initializeAuthButtons(
			dislikeButton,
			checkAuthenticationStatus,
			async function() {
				let notifId = Date.now();
				toggleNotification(notifId);

				try {
					const request = await fetch(`/api/posts/${postId}/comments?offset=${rendered_comments}&limit=10`);
					const result = await request.json();

					if (result.success) {
						const commentsSection = document.getElementById('commentsSection');
						result.comments.forEach(comment => {
							commentsSection.innerHTML += renderComment(comment, postId); // Adiciona cada comentário
						});

						rendered_comments += 5; // Incrementa o número de comentários a serem carregados
						// Verifica se todos os comentários foram carregados
						if (total_comments <= rendered_comments) {
							loadMoreButton.style.display = 'none'; // Esconde o botão se não houver mais comentários
						}
					} else {
						alert('Erro ao carregar mais comentários: ' + result.message);
					}
				} catch (error) {
					commentModalContent.innerHTML = 'Erro de conexão.';
				}
				toggleNotification(notifId);
			}
		);
	}
}

async function openCommentModal(commentId, postId) {
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
				const cloneComment = originalComment.cloneNode(true);
				cloneComment.setAttribute("id", `interaction${commentId}modalbox`);
				cloneComment.classList.add('comment-item');
				cloneComment.dataset.commentId = commentId;
				cloneComment.querySelector('.options-button').remove()
                commentModalContent.appendChild(cloneComment);
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

// Fecha modais ao pressionar a tecla ESC
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeModal('imageModal');
        closeModal('replyModal');
        closeModal('postModal');
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    // Fecha modais ao clicar fora
    document.addEventListener('click', function(event) {
        // Fechar modal de imagem
        const imageModal = document.getElementById('imageModal');
        if (imageModal && imageModal.classList.contains('is-visible') && !imageModal.querySelector('.image-modal-content').contains(event.target) && event.target.id === 'imageModal') {
            closeModal('imageModal');
        }
        
        // Fechar modal de resposta
        const replyModal = document.getElementById('replyModal');
        if (replyModal && replyModal.classList.contains('is-visible') && !replyModal.querySelector('.reply-modal-content').contains(event.target) && event.target.id === 'replyModal') {
            closeModal('replyModal');
        }
		
		// Fechar modal de comentários extras
		const commentModal = document.getElementById('commentModal');
        if (commentModal && commentModal.classList.contains('is-visible') && !commentModal.querySelector('.reply-modal-content').contains(event.target) && event.target.id === 'commentModal') {
            closeModal('commentModal');
        }
		
        // Fechar modal do post
        const postModal = document.getElementById('postModal');
        if (postModal && postModal.classList.contains('is-visible') && !postModal.querySelector('.post-modal-content').contains(event.target) && event.target.id === 'postModal') {
            closeModal('postModal');
        }

        // Fechar o menu de compartilhamento se clicar fora de ambos os elementos
        if (!event.target.closest('.shareContainer') && shareMenuOpen == true) {
            document.querySelectorAll('.share-context-menu').forEach(shareContextMenu => {
                shareContextMenu.classList.add('hidden')
            })
            shareMenuOpen = false;
        }
    });

    // --- Funções de Interatividade dos Botões Principais (Like, Dislike, Salvar) ---

    document.querySelectorAll('[id^="saveButton-"]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            toggleActive(btn);
            console.log('Botão Salvar do Post clicado!');
            // Lógica de backend aqui
        });
    });

    // --- Compartilhamento ---
    document.querySelectorAll('.shareButton').forEach(attachShareEvent);

    // Dar like em um post
    document.querySelectorAll('.like-button').forEach(attachLikeEvent);

    // Dar deslike em um post
    document.querySelectorAll('.dislike-button').forEach(attachDislikeEvent);

    // Abrir um post
    document.querySelectorAll('.timeline-post').forEach(function(post) {
        post.addEventListener('click', async function(event) {
            if (event.target.closest('.interactions-container, .interaction-button, .share-context-menu, .image-container, .options-button, .author-link')) {
                return; 
            }
            const postId = post.dataset.postid;
            const notifId = Date.now();
            toggleNotification(notifId);
            
            try {
                // Requisição para obter os dados do post
                const response = await fetch(`/api/posts/${postId}`);
                const data = await response.json();
                if (data.success) {
                    const postModal = document.getElementById('postModal');
                    const modalContent = postModal.querySelector('.post-modal-content')
                    
                    modalContent.innerHTML = renderPost(data);
                    openModal('postModal');
                    attachPostEventListeners(postId, data.total_comments, data.next_offset); // Passa o ID do post e o número total de comentários
                }
            } catch(error) {
                console.error('Erro ao carregar o post:', error);
            }
            toggleNotification(notifId);
        });
    });

    document.querySelectorAll('textarea').forEach(textarea => {
        resetTextarea(textarea);
    });
});