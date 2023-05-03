from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostUrlsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.post = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group = Post.objects.create(
            author=cls.user,
            text='Тестовый пост1234',
        )
        cls.INDEX = '/'
        cls.GROUP = '/group/test-slug/'
        cls.PROFILE = '/profile/auth/'
        cls.POST_DETAIL = f'/posts/{cls.post.id}/'
        cls.POST_CREATE = '/create/'
        cls.POST_EDIT = f'/posts/{cls.post.id}/edit/'
        cls.COMMENT_ADD = f'/posts/{cls.post.id}/comment/'
        cls.FOLLOW_INDEX = '/follow/'
        cls.PROFILE_FOLLOW = f'/profile/{cls.user.username}/follow/'
        cls.PROFILE_UNFOLLOW = f'/profile/{cls.user.username}/unfollow/'

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

    def test_url_httpstatus(self):
        """Тестирование всех статусов ответов"""
        responses_statuses = [
            (self.guest_client.get(self.INDEX), HTTPStatus.OK),
            (self.authorized_client.get(self.INDEX), HTTPStatus.OK),
            (self.guest_client.get(self.GROUP), HTTPStatus.OK),
            (self.authorized_client.get(self.GROUP), HTTPStatus.OK),
            (self.guest_client.get(self.PROFILE), HTTPStatus.OK),
            (self.authorized_client.get(self.PROFILE), HTTPStatus.OK),
            (self.guest_client.get(self.POST_DETAIL), HTTPStatus.OK),
            (self.authorized_client.get(self.POST_DETAIL), HTTPStatus.OK),
            (self.guest_client.get(self.POST_CREATE), HTTPStatus.FOUND),
            (self.authorized_client.get(self.POST_CREATE), HTTPStatus.OK),
            (self.guest_client.get(self.POST_EDIT), HTTPStatus.FOUND),
            (self.authorized_client.get(self.POST_EDIT), HTTPStatus.OK),
            (self.authorized_client2.get(self.POST_EDIT), HTTPStatus.FOUND),
            (self.authorized_client.get('/asd/'), HTTPStatus.NOT_FOUND),
            (self.authorized_client.get('/asd/'), HTTPStatus.NOT_FOUND),
            (self.guest_client.get(self.COMMENT_ADD), HTTPStatus.FOUND),
            (self.authorized_client.get(self.COMMENT_ADD), HTTPStatus.FOUND),
            (self.authorized_client.get(self.FOLLOW_INDEX), HTTPStatus.OK),
            (
                self.authorized_client.get(self.PROFILE_FOLLOW),
                HTTPStatus.FOUND
            ),
            (
                self.authorized_client.get(self.PROFILE_UNFOLLOW),
                HTTPStatus.FOUND
            )
        ]
        for response, status in responses_statuses:
            with self.subTest(responses_statuses=responses_statuses):
                self.assertEqual(
                    response.status_code,
                    status
                )

    def test_url_redirect_anonymous_on_admin_login(self):
        """Страницы перенаправят анонимного пользователя
        на страницу логина.
        """
        field_response = {
            self.guest_client.get(
                self.POST_CREATE,
                follow=True
            ): '/auth/login/?next=/create/',
            self.guest_client.get(
                self.POST_EDIT,
                follow=True
            ): (
                '/auth/login/?next=/posts/'
                + str(self.post.id)
                + '/edit/'
            )
        }
        for value, expected in field_response.items():
            with self.subTest(value=value):
                self.assertRedirects(value, expected)

    def test_task_list_url_redirect(self):
        """Страницы перенаправят не автора поста"""
        response_post_edit = self.authorized_client2.get(
            self.POST_EDIT,
            follow=True
        )
        self.assertRedirects(response_post_edit, (self.POST_DETAIL))

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.INDEX: 'posts/index.html',
            self.GROUP: 'posts/group_list.html',
            self.PROFILE: 'posts/profile.html',
            self.POST_DETAIL: 'posts/post_detail.html',
            self.POST_CREATE: 'posts/post_create.html',
            self.POST_EDIT: 'posts/post_create.html'
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
