from flask import render_template, redirect, url_for, flash, session
from app.extensions import login_required, db_manager, s3, current_app
from app.api.routes import get_post_with_details
from botocore.exceptions import ClientError
import app.data_sanitizer as sanitizer
from app.database import Post
from app.posts import bp
from PIL import Image
import uuid
import os
import io

@bp.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = sanitizer.PostForm()
    if form.validate_on_submit():
        uploaded_files_info = []
        
        for file in form.images.data:
            if file and file.filename: # Verificar se um arquivo foi realmente enviado para este campo
                try:
                    file_extension = os.path.splitext(file.filename)[1]
                    unique_filename = str(uuid.uuid4()) + file_extension
                    img = Image.open(file)

                    # Cria um buffer em memória para salvar a imagem limpa
                    img_byte_arr = io.BytesIO()

                    # Salva a imagem no buffer sem metadados EXIF.
                    if file_extension == '.jpeg' or file_extension == '.jpg':
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
                    print(f"Erro S3: {e}")
                except Exception as e:
                    flash(f'Erro inesperado ao processar {file.filename}: {e}', 'danger')
                    print(f"Erro geral: {e}")
        
        with db_manager.get_db() as db:
            image_urls_json = json.dumps(uploaded_files_info) if uploaded_files_info else None

            try:
                new_post = Post(
                    user_id=session['id'],
                    title=form.titulo.data.strip(),
                    content=form.conteudo.data.strip(),
                    tag=form.tags.data,
                    optional_tags=form.optionaltags.data,
                    image_urls=image_urls_json
                )
                db.add(new_post)
                db.commit()
                db.refresh(new_post) # Recarrega o objeto para ter o ID gerado pelo DB
                flash('Post criado com sucesso!', 'success')
                return redirect(url_for('posts.view_post', post_id=new_post.id))
            except Exception as e:
                db.rollback()
                flash('Erro ao criar post. Tente novamente.', 'danger')
    
    return render_template('post.html', form=form, allowed_categories=sanitizer.ALLOWED_CATEGORIES)

@bp.route('/post/<int:post_id>', methods=['GET'])
@login_required
def view_post(post_id):
    post = get_post_with_details(post_id)
    if not post:
        flash('Post não encontrado.', 'error') # Considerar usar abort()
        return redirect(url_for('main.index'))
    
    return render_template('post_details.html',
                           post=post['post'],
                           comments=post['comments_with_details'], 
                           post_likes=post['post_likes'],
                           post_dislikes=post['post_dislikes'],
                           user_post_reaction=post['user_post_reaction'],
                           next_offset=post['next_offset'],
                           total_comments=post['total_comments'])
