import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from ..forms import PostForm
from ..models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост'
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Проверка создания нового поста"""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост1',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = Post.objects.latest('pub_date')
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group, self.group)
        self.assertEqual(new_post.author, self.user)
        self.assertRedirects(response, reverse(
            'posts:profile',
            args={self.user.username}
        ))
        self.assertTrue(
            Post.objects.filter(
                image='posts/small.gif'
            ).exists()
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_create_post_edite(self):
        """Проверка изменения поста"""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Пваы ываывафыва',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        ))
        edit_posts = Post.objects.get(id=self.post.id)
        self.assertEqual(edit_posts.text, form_data['text'])
        self.assertEqual(edit_posts.group, self.group)
        self.assertEqual(edit_posts.author, self.user)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_text_help_text(self):
        title_help_text = PostFormTest.form.fields['text'].help_text
        self.assertEqual(title_help_text, 'Текст нового поста')

    def test_group_help_text(self):
        title_help_text = PostFormTest.form.fields['group'].help_text
        self.assertEqual(
            title_help_text,
            'Группа, к которой будет относиться пост'
        )

    def test_authorize_create_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'СУпер коммент',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        ))
        new_commect = Comment.objects.get(post=self.post)
        self.assertEqual(new_commect.text, form_data['text'])
        self.assertEqual(new_commect.author, self.user)
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_nonauthorize_create_comment(self):
        """Попытка создания комментария неавторизованным пользователем"""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'СУпер коммент',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), comment_count)
