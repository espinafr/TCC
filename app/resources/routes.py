from flask import render_template, request, current_app, flash, session, redirect, url_for, jsonify
from app.resources import bp
from app.extensions import db_manager, s3, power_required, login_required
from app.data_sanitizer import ResourceForm, ALLOWED_CATEGORIES
from app.api.routes import get_user_icon
from botocore.exceptions import ClientError
from werkzeug.datastructures import FileStorage
from PIL import Image
import os, uuid, io, json, logging

from urllib.parse import unquote


def upload_file_to_s3(file: FileStorage, folder: str):
    """Faz upload de um arquivo pra S3 e retorna a URL, e em caso de erro None"""
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = str(uuid.uuid4()) + file_extension

        if file_extension in ['.jpg', '.jpeg', '.png', '.webp', '.jfif']:
            img = Image.open(file)
            try:
                img = img.convert('RGB')
            except Exception:
                pass
            img_byte_arr = io.BytesIO()
            if file_extension in ['.jpeg', '.jpg']:
                img.save(img_byte_arr, format='JPEG', optimize=True)
            elif file_extension == '.png':
                img.save(img_byte_arr, format='PNG', optimize=True)
            else:
                img.save(img_byte_arr, format=img.format, optimize=True)
            img_byte_arr.seek(0)
            object_body = img_byte_arr
        else:
            file.stream.seek(0)
            object_body = file.stream

        s3.client.upload_fileobj(
            object_body,
            current_app.config['S3_BUCKET_NAME'],
            f'public/resources/{folder}/{unique_filename}',
            ExtraArgs={'ContentType': file.content_type}
        )

        return f"https://{current_app.config['S3_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/public/resources/{folder}/{unique_filename}"
    except ClientError as e:
        logging.getLogger(__name__).error(f"S3 upload error: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Upload error: {e}")
    return None


def delete_from_s3(url: str):
    """Deletar um objeto do S3 a partir da URL"""
    if not url:
        return
    try:
        object_key = url.split(f"{current_app.config['S3_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/")[-1]
        decoded_key = unquote(object_key)
        s3.client.delete_object(Bucket=current_app.config['S3_BUCKET_NAME'], Key=decoded_key)
        logging.getLogger(__name__).info(f"Deleted S3 object {decoded_key}")
    except ClientError as e:
        logging.getLogger(__name__).error(f"Erro ao deletar objeto do S3: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Erro inesperado ao deletar do S3: {e}")


@bp.route('/', methods=['GET'])
def list_resources():
    resources = db_manager.get_all_resources(offset=0, limit=100)
    formatted = []
    for r in resources:
        formatted.append({
            'id': r.id,
            'title': r.title,
            'category': r.category,
            'tags': r.tags,
            'created_at': r.created_at.strftime('%d/%m/%Y'),
            'author': r.author_user.display_name or r.author_user.user.username,
            'banner_url': r.banner_url,
            'youtube_url': r.youtube_url,
            'first_attachment': r.attachment_urls[0] if r.attachment_urls else None
        })

    can_create = False
    if session.get('id'):
        user = db_manager.get_user('id', session.get('id'))
        if user and getattr(user, 'power', 0) >= 1:
            can_create = True

    return render_template('resources.html', resources=formatted, can_create=can_create)


@bp.route('/escrever', methods=['GET', 'POST'])
@power_required(1)
def create_resource():
    form = ResourceForm()
    if request.method == 'GET':
        return render_template('resource_create.html', form=form, allowed_categories=ALLOWED_CATEGORIES)

    if form.validate_on_submit():
        uploaded_banner = None
        attachments_urls = []

        banner = form.bannerImage.data
        if banner and getattr(banner, 'filename', None):
            uploaded_banner = upload_file_to_s3(banner, 'banners')

        for file in form.attachments.data:
            if isinstance(file, FileStorage) and file.filename:
                url = upload_file_to_s3(file, 'attachments')
                if url:
                    attachments_urls.append(url)

        youtube_url = None
        if getattr(form, 'youtubeUrl', None) and form.youtubeUrl.data:
            youtube_url = form.youtubeUrl.data.strip()

        success, result = db_manager.create_resource(
            user_id=session.get('id'),
            title=form.tituloInput.data.strip(),
            category=form.category.data,
            tags=form.tags.data,
            banner_url=uploaded_banner,
                content=form.contentTextarea.data.strip(),
                attachment_urls=attachments_urls,
                youtube_url=youtube_url
        )

        if success:
            flash('Recurso criado com sucesso!', 'success')
            return jsonify({'success': True, 'message': result}), 201
        else:
            logging.getLogger(__name__).error(f'Erro ao salvar recurso: {result}')
            return jsonify({'success': False, 'message': 'Erro ao criar recurso. Tente novamente.'}), 400
    else:
        logging.getLogger(__name__).warning(f"Erro de validação no create_resource: {form.errors}")
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'}), 400


@bp.route('/<int:resource_id>', methods=['GET'])
def view_resource(resource_id):
    resource = db_manager.get_resource_by_id(resource_id)
    if not resource:
        flash('Recurso não encontrado.', 'error')
        return redirect(url_for('main.index'))

    # Determine permission to delete (author or moderator power)
    can_delete = False
    if session.get('id'):
        user = db_manager.get_user('id', session.get('id'))
        if user and getattr(user, 'power', 0) >= 1:
            can_delete = True
        if resource.user_id == session.get('id'):
            can_delete = True

    # Render template
    return render_template('resource_details.html', resource=resource, user_icon=get_user_icon(session.get('id')), can_delete=can_delete)



@bp.route('/<int:resource_id>/delete', methods=['POST'])
@login_required
def delete_resource(resource_id):
    resource = db_manager.get_resource_by_id(resource_id)
    if not resource:
        return jsonify({'success': False, 'message': 'Recurso não encontrado.'}), 404

    current_user = db_manager.get_user('id', session.get('id'))
    if not current_user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 403

    if resource.user_id != session.get('id') and getattr(current_user, 'power', 0) < 1:
        return jsonify({'success': False, 'message': 'Permissão negada.'}), 403

    if resource.banner_url:
        delete_from_s3(resource.banner_url)

    if resource.attachment_urls:
        for f in resource.attachment_urls:
            try:
                delete_from_s3(f)
            except Exception:
                logging.getLogger(__name__).warning(f"Falha ao deletar anexo S3: {f}")

    success = db_manager.delete_resource_by_id(resource_id)
    if success:
        return jsonify({'success': True, 'message': 'Recurso deletado.'}), 200
    else:
        return jsonify({'success': False, 'message': 'Erro ao deletar recurso.'}), 500
