from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request

from django.http import HttpResponse
from .update_db import update_all_db
from .services import Skill


class MainView(APIView):

    def post(self, request: Request) -> Response:
        skill = Skill(request)
        return skill.get_response()


def index(request):
    return HttpResponse("Hello World")


async def update_db(request):
    await update_all_db()
    return HttpResponse("OK")

