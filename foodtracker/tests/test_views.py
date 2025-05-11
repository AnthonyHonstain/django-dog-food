from django.test import TestCase, Client
from django.urls import reverse


class TestHelloWorldView(TestCase):
    def setUp(self):
        self.client = Client()

    def test_hello_world(self):
        response = self.client.get(reverse("hello_world"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Hello World")
