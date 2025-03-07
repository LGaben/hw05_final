from http import HTTPStatus

from django.test import TestCase


class CoreViewTest(TestCase):
    def test_error_page(self):
        response = self.client.get('/nonexist-page/')
        # Проверьте, что статус ответа сервера - 404
        # Проверьте, что используется шаблон core/404.html
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
