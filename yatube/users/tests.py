from http import HTTPStatus

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django import forms

User = get_user_model()


class UserModelTest(TestCase):

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='StasBasov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_signup_url_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        response_signup = self.guest_client.get('/auth/signup/')
        response_login = self.guest_client.get('/auth/login/')
        field_response = [
            response_signup,
            response_login
        ]
        for response in range(len(field_response)):
            with self.subTest(response=field_response[response]):
                self.assertEqual(
                    field_response[response].status_code,
                    HTTPStatus.OK
                )

    def test_logout_url_exists_at_desired_location(self):
        """Страницы доступны авторизованному пользователю."""
        response_password_change = self.authorized_client.get(
            '/auth/password_change/'
        )
        response_password_reset = self.authorized_client.get(
            '/auth/password_reset/'
        )
        response_logout = self.authorized_client.get('/auth/logout/')
        field_response = [
            response_password_change,
            response_password_reset,
            response_logout
        ]
        for response in range(len(field_response)):
            with self.subTest(response=field_response[response]):
                self.assertEqual(
                    field_response[response].status_code,
                    HTTPStatus.OK
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'users/signup.html': '/auth/signup/',
            'users/login.html': '/auth/login/',
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_urls_uses_correct_template1(self):
        """URL-адрес использует соответствующий шаблон1."""
        templates_url_names = {
            'users/password_change_form.html': '/auth/password_change/',
            'users/password_reset_form.html': '/auth/password_reset/',
            'users/logged_out.html': '/auth/logout/'
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_pages_uses_correct_template(self):
        """При запросе к namespace:name, применяется верныe шаблоны"""
        # Собираем в словарь пары reverse(name): "имя_html_шаблона"
        templates_page_names = {
            reverse('users:signup'): 'users/signup.html',
            reverse('users:logout'): 'users/logged_out.html',
            reverse('users:password_reset_form'): (
                'users/password_reset_form.html'
            ),
            reverse('users:password_reset_done'): (
                'users/password_reset_done.html'
            ),
            reverse('users:logout'): 'users/logged_out.html',
            reverse('users:login'): 'users/login.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_users_signup_context(self):
        """Проверка контекста users:signup"""
        response = self.authorized_client.get(reverse(
            'users:signup'
        ))
        form_fields = {
            'first_name': forms.fields.CharField,
            'last_name': forms.fields.CharField,
            'username': forms.fields.CharField,
            'email': forms.fields.EmailField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                # Проверяет, что поле формы является экземпляром
                # указанного класса
                self.assertIsInstance(form_field, expected)

    def test_new_user(self):
        user_count = User.objects.count()
        form_data = {
            'first_name': 'asfasdbcb',
            'last_name': 'asd',
            'username': 'sdfgdfg',
            'password1': '12345678qQ',
            'password2': '12345678qQ',
            'email': 'asdsad@gmail.com'
        }
        response = self.guest_client.post(
            reverse('users:signup'),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(response, reverse('posts:index'))
        self.assertEqual(User.objects.count(), user_count + 1)
