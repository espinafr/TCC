from flask import render_template, abort, session, request, jsonify, current_app
from app.extensions import login_required, db_manager, s3
from app.database import UserDetails
from app.data_sanitizer import ProfileEditForm
from botocore.exceptions import ClientError
from app.main.routes import get_interactions
from app.users import bp
from PIL import Image
from urllib.parse import unquote
import os, uuid, io, json

def delete_from_s3(url):
    if not url:
        return
    try:
        object_key = url.split(f"{current_app.config['S3_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/")[-1]
        
        # Decodifica a chave do objeto para lidar com caracteres especiais no nome do arquivo
        decoded_key = unquote(object_key)

        s3.client.delete_object(
            Bucket=current_app.config['S3_BUCKET_NAME'],
            Key=decoded_key
        )
        print(f"Objeto {decoded_key} deletado do S3 com sucesso.")
    except ClientError as e:
        # Loga o erro se a exclusão falhar, mas não impede a atualização do perfil
        print(f"Erro ao deletar objeto do S3: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao tentar deletar o objeto do S3: {e}")

def get_user_posts(id):
    posts = []
    for post in db_manager.get_user_posts(id):
        post_reactions = get_interactions(post.id)
        posts.append({  
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'tag': post.tag,
            'optional_tags': post.optional_tags,
            'created_at': post.created_at,
            'author': post.author_user.display_name,
            'authorat': post.author_user.user.username,
            'authoricon': post.author_user.icon_url,
            'userid': post.author_user.user_id,
            'image_urls': json.loads(post.image_urls) if post.image_urls else [], 
            'likes': post_reactions["likes"],
            'dislikes': post_reactions["dislikes"],
            'comments': post_reactions["comments"],
            'user_reaction': post_reactions["user_reaction"]
        })
    return posts

def upload_to_s3(file, folder):
    try:
        file_extension = os.path.splitext(file.filename)[1].lower()
        unique_filename = str(uuid.uuid4()) + file_extension
        img = Image.open(file)
        img_byte_arr = io.BytesIO()

        # Salva a imagem no buffer sem metadados EXIF
        if file_extension in ['.jpeg', '.jpg']:
            img.save(img_byte_arr, format='JPEG', optimize=True)
        elif file_extension == '.png':
            img.save(img_byte_arr, format='PNG', optimize=True)
        else:
            img.save(img_byte_arr, format=img.format, optimize=True)

        img_byte_arr.seek(0)
        s3.client.upload_fileobj(
            img_byte_arr,
            current_app.config['S3_BUCKET_NAME'],
            f'public/{folder}/{unique_filename}',
            ExtraArgs={'ContentType': file.content_type}
        )
        return f"https://{current_app.config['S3_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/public/{folder}/{unique_filename}"
    except ClientError as e:
        print(f'Erro S3: {e}')
    except Exception as e:
        print(f'Erro ao processar imagem: {e}')
    return None

@bp.route('/<int:id>')
def view_profile(id):
    user_details = db_manager.get_user_details(id)
    if not user_details:
        abort(404)
    
    user_posts = get_user_posts(id)
    
    return render_template(
        'profile.html',
        user={
            'id': user_details.user_id,
            'username': user_details.user.username,
            'display_name': user_details.display_name,
            'bio': user_details.bio,
            'creation_date': user_details.user.creation_date,
            'profile_image_url': user_details.icon_url,
            'banner_url': user_details.banner_url,
            'badges': [],
            'posts': user_posts
        },
        can_edit_profile=session.get('id') == id
    )

@bp.route('/<int:id>/editar', methods=['POST'])
@login_required
def edit_profile(id):
    current_user_id = session.get('id')
    if current_user_id != id:
        return jsonify({'success': False, 'message': 'Você não tem permissão para editar este perfil.'}), 403

    # Atualiza o usuário no banco 
    user = db_manager.get_user_details(id)
    if not user:
        return jsonify({'success': False, 'message': 'Usuário não encontrado.'}), 404
    
    form = ProfileEditForm()
    if form.validate_on_submit():
        display_name = form.editDisplayName.data.strip()
        bio = form.editBio.data.strip()
        remove_banner = form.remove_banner.data
        profile_image = form.editProfilePicInput.data
        banner_image = form.editBannerInput.data

        # URLs para salvar no banco
        profile_image_url = None
        banner_url = None
        
        if profile_image and profile_image.filename:
            if user.icon_url:
                delete_from_s3(user.icon_url)
            profile_image_url = upload_to_s3(profile_image, 'profile')
    
        if banner_image and banner_image.filename:
            if user.banner_url:
                delete_from_s3(user.banner_url)
            banner_url = upload_to_s3(banner_image, 'banner')

        with db_manager.get_db() as db:
            user = db.query(UserDetails).filter(UserDetails.user_id == id).first()

            # Atualize os campos conforme seu modelo
            if display_name:
                user.display_name = display_name
            if bio:
                user.bio = bio
            if profile_image_url:
                user.icon_url = profile_image_url
            if banner_url:
                user.banner_url = banner_url
            if remove_banner:
                user.banner_url = None

            try:
                db.commit()
            except Exception as e:
                db.rollback()
                return jsonify({'success': False, 'message': f'Erro ao salvar no banco: {e}'}), 500

            return jsonify({
                'success': True,
                'message': 'Perfil atualizado com sucesso!',
            })
    else:
        return jsonify({'success': False, 'errors': form.errors, 'message': 'Erro de validação.'}), 400