import shutil
import tempfile
from http import HTTPStatus

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post, Follow

User = get_user_model()

PAGI_ON_NEXT_PAGE = 1

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """При запросе к namespace:name, применяется вернык шаблоны"""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', args={self.user.username}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}): (
                'posts/post_create.html'
            ),
            reverse('posts:follow_index'): 'posts/follow.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def post_and_paginator_context(self, post):
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.pk, self.post.pk)
        self.assertEqual(post.image, self.post.image)

    def form_context(self, response):
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_index_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        post_0 = response.context['page_obj'][0]
        self.post_and_paginator_context(post_0)

    def test_group_list_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}
        ))
        group = response.context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.description, self.group.description)
        post_0 = response.context['page_obj'][0]
        self.post_and_paginator_context(post_0)

    def test_profile_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:profile', args={self.user.username}
        ))
        self.assertEqual(response.context['author'], self.user)
        post_0 = response.context['page_obj'][0]
        self.post_and_paginator_context(post_0)

    def test_post_detail_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}
        ))
        post = response.context['post']
        self.post_and_paginator_context(post)

    def test_post_create_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_create'
        ))
        self.form_context(response)

    def test_post_edit_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}
        ))
        self.form_context(response)
        post = response.context['post']
        self.post_and_paginator_context(post)
        is_edit = response.context['is_edit']
        self.assertIsNotNone(is_edit)

    def test_new_post_in_group(self):
        """Проверка на то, что пост попал в нужную группу"""
        self.post2 = Post.objects.create(
            author=self.user,
            text='Новый Тестовый пост',
            group=self.group
        )
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group2.slug}
        ))
        self.assertNotIn(self.post2, response.context['page_obj'])
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}
        ))
        self.assertIn(self.post2, response.context['page_obj'])

    def test_cache_index(self):
        response = self.authorized_client.get(reverse('posts:index'))
        response_content = response.content
        self.post1 = Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_content)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn(self.post1, response.context['page_obj'])


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_paginator(self):
        """Проверка пагинатора"""
        for i in range(settings.NUMBERS_POSTS + PAGI_ON_NEXT_PAGE):
            Post.objects.create(
                author=self.user,
                text='Тестовый пост' + str(
                    settings.NUMBERS_POSTS
                    + PAGI_ON_NEXT_PAGE
                ),
                group=self.group
            )
            cache.clear()
        response_num = [
            (
                self.authorized_client.get(reverse('posts:index')),
                settings.NUMBERS_POSTS
            ),
            (self.authorized_client.get(reverse('posts:index') + '?page=2'),
                PAGI_ON_NEXT_PAGE),
            (self.authorized_client.get(reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )), settings.NUMBERS_POSTS),
            (self.authorized_client.get(reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ) + '?page=2'), PAGI_ON_NEXT_PAGE),
            (self.authorized_client.get(reverse(
                'posts:profile', args={self.user.username}
            )), settings.NUMBERS_POSTS),
            (self.authorized_client.get(reverse(
                'posts:profile',
                args={self.user.username}
            ) + '?page=2'), PAGI_ON_NEXT_PAGE)
        ]
        for response, num in response_num:
            with self.subTest(response=response):
                self.assertEqual(len(response.context['page_obj']), num)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user1 = User.objects.create_user(username='auth1')
        cls.author = User.objects.create_user(username='someauthor')

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client1 = Client()
        self.authorized_client1.force_login(self.user1)

    def test_follow(self):
        """Подписываемся"""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={
                'username': self.author.username}),
        )
        following = Follow.objects.filter(
            user=self.user,
            author=self.author
        ).exists()
        self.assertTrue(following)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND
        )

    def test_unfollow(self):
        """Отписываемся"""
        Follow.objects.create(user=self.user, author=self.author)
        response = self.authorized_client.get(
            reverse('posts:profile_unfollow', kwargs={
                'username': self.author.username}),
        )
        following = Follow.objects.filter(
            user=self.user,
            author=self.author
        ).exists()
        self.assertFalse(following)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND
        )

    def test_new_post_follow(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан и не появляется в ленте тех,
        кто не подписан.
        """
        Follow.objects.create(user=self.user, author=self.author)
        self.post = Post.objects.create(
            author=self.author,
            text='Тестовый пост',
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['page_obj'])
        response = self.authorized_client1.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])
