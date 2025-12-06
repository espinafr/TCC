from flask import render_template, redirect, url_for, flash, session, current_app, jsonify, request
import logging
from app.extensions import login_required, db_manager, s3
from app.api.routes import get_post_with_details, get_user_icon
from botocore.exceptions import ClientError
from app.data_sanitizer import PostForm, ALLOWED_CATEGORIES
from app.database import Post
from app.posts import bp
from PIL import Image
from werkzeug.datastructures import FileStorage
import json, uuid, os, io

@bp.route('/escrever', methods=['GET', 'POST'])
@login_required
def postedeluz():
    form = PostForm()
    return render_template('post.html', form=form, allowed_categories=ALLOWED_CATEGORIES)

@bp.route('/mandarpost', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        uploaded_files_info = []
        
        for file in form.inputFiles.data:
            if isinstance(file, FileStorage) and file.filename: # Verificar se um arquivo foi realmente enviado para este campo
                try:
                    file_extension = os.path.splitext(file.filename)[1]
                    unique_filename = str(uuid.uuid4()) + file_extension
                    img = Image.open(file)

                    # Cria um buffer em memória para salvar a imagem limpa
                    img_byte_arr = io.BytesIO()

                    # Salva a imagem no buffer sem metadados EXIF.
                    if file_extension in ['.jpeg', '.jpg']:
                        img.save(img_byte_arr, format='JPEG', optimize=True)
                    elif file_extension == '.png':
                        img.save(img_byte_arr, format='PNG', optimize=True)
                    else:
                        # Para outros formatos
                        img.save(img_byte_arr, format=img.format, optimize=True)

                    img_byte_arr.seek(0) # Volta o ponteiro pro início do buffer

                    s3.client.upload_fileobj(
                        img_byte_arr, # Buffer com a imagem limpa
                        current_app.config['S3_BUCKET_NAME'],
                        f'public/{unique_filename}',
                        ExtraArgs={
                            'ContentType': file.content_type
                        }
                    )

                    file_url = f"https://{current_app.config['S3_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/public/{unique_filename}"
                    uploaded_files_info.append(file_url)
                except ClientError as e:
                    flash(f'Erro ao fazer upload para o S3 para {file.filename}: {e}', 'danger')
                    logging.getLogger(__name__).error(f"Erro S3: {e}")
                except Exception as e:
                    flash(f'Erro inesperado ao processar {file.filename}: {e}', 'danger')
                    logging.getLogger(__name__).error(f"Erro geral: {e}")
        
        with db_manager.get_db() as db:
            image_urls_json = json.dumps(uploaded_files_info) if uploaded_files_info else None

            try:
                new_post = Post(
                    user_id=session['id'],
                    title=form.tituloInput.data.strip(),
                    content=form.contentTextarea.data.strip(),
                    tag=form.tags.data,
                    optional_tags=form.hiddenOptionalTags.data,
                    image_urls=image_urls_json
                )
                db.add(new_post)
                db.commit()
                db.refresh(new_post) # Recarrega o objeto para ter o ID gerado pelo DB
                flash('Post criado com sucesso!', 'success')
                return jsonify({'success': True, 'message': new_post.id}), 201
            except Exception as e:
                db.rollback()
                return jsonify({'success': False, 'message': 'Erro ao criar post. Tente novamente.'}), 400
    else:
        logging.getLogger(__name__).warning(f"Erro de validação no create_post: {form.errors}")
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'}), 400

@bp.route('/post/<int:post_id>', methods=['GET'])
def view_post(post_id):
    post = get_post_with_details(post_id)
    if not post:
        flash('Post não encontrado.', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('post_details.html',
                           post=post['post'],
                           comments=post['comments_with_details'], 
                           post_likes=post['post_likes'],
                           post_dislikes=post['post_dislikes'],
                           user_post_reaction=post['user_post_reaction'],
                           next_offset=post['next_offset'],
                           total_comments=post['total_comments'],
                           is_saved=db_manager.is_post_saved(session.get('id', 0), post_id) if session.get('id') else False,
                           user_icon=get_user_icon(session.get('id')))

