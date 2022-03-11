import math
from datetime import datetime, timedelta

import requests
from rest_framework.response import Response
from fuzzywuzzy import process
import humanize

from .models import Bus, BusStop, YandexUser, Direction
from .dict2object import dict2object, Object
from .validate import validate


class Command:

    def __init__(self, words_from_command):
        self.words_from_command = words_from_command
        self.type = self._determine_type_of_command()
        self.bus_name = self._get_bus_name()
        self.guiding_bus_stop_name = self._get_guiding_bus_stop_name()
        self.bus_stop_name = self._get_bus_stop_name()

    def _determine_type_of_command(self):
        if self._is_command_for_remember_main_bus_schedule():
            return "remember main bus schedule"
        if self._is_command_for_get_main_bus_schedule():
            return "get main bus schedule"
        if self._is_command_for_get_bus_schedule():
            return "get bus schedule"
        if self._is_command_for_get_bus_schedules():
            return "get bus schedules"
        return "unknown command"

    def _is_command_for_get_bus_schedules(self):
        if "автобусов" in self.words_from_command:
            return True
        return False

    def _is_command_for_get_bus_schedule(self):
        if "автобус" in self.words_from_command or "автобуса" in self.words_from_command:
            return True
        return False

    def _is_command_for_get_main_bus_schedule(self):
        if self.words_from_command and (self.words_from_command[0] in ['автобус', 'автобуса']
                                        or 'мой' in self.words_from_command
                                        or self.words_from_command == ['во', 'сколько', 'будет', 'автобус']):
            return True
        return False

    def _is_command_for_remember_main_bus_schedule(self):
        if "запомни" in self.words_from_command:
            return True
        return False

    def _get_bus_name(self):
        fuzzy_bus_name = self._get_fuzzy_bus_name()
        if fuzzy_bus_name:
            all_bus_names = list(Bus.objects.values_list("name", flat=True).distinct())
            return process.extractOne(fuzzy_bus_name, all_bus_names)[0]

    def _get_fuzzy_bus_name(self):
        for index, word in enumerate(self.words_from_command):
            if word.isdigit():
                next_word = self.words_from_command[index + 1]
                if next_word == "на":
                    return word
                return word + next_word

    def _get_guiding_bus_stop_name(self):
        fuzzy_guiding_bus_stop_name = self._get_fuzzy_guiding_bus_stop_name()
        if fuzzy_guiding_bus_stop_name:
            all_bus_stop_names = list(BusStop.objects.values_list("name", flat=True).distinct())
            return process.extractOne(fuzzy_guiding_bus_stop_name, all_bus_stop_names)[0]

    def _get_fuzzy_guiding_bus_stop_name(self):
        for index, word in enumerate(self.words_from_command):
            if word == "сторону":
                return " ".join(self.words_from_command[index + 1:])

    def _get_bus_stop_name(self):
        fuzzy_bus_stop_name = self._get_fuzzy_bus_stop_name()
        if fuzzy_bus_stop_name:
            all_bus_stop_names = list(BusStop.objects.values_list("name", flat=True).distinct())
            return process.extractOne(fuzzy_bus_stop_name, all_bus_stop_names)[0]

    def _get_fuzzy_bus_stop_name(self):
        if "на" in self.words_from_command and "сторону" in self.words_from_command:
            index_of_start_of_bus_stop_name = self.words_from_command.index("на") + 1
            index_of_finish_of_bus_stop_name = self.words_from_command.index("сторону")
            return " ".join(self.words_from_command[index_of_start_of_bus_stop_name:index_of_finish_of_bus_stop_name])


class Skill:
    data: Object
    command: Command
    yandex_user: YandexUser

    def __init__(self, request):
        self.data = dict2object(request.data)
        self.yandex_user = self._get_yandex_user_from_request()
        self.main_bus_stop = self.yandex_user.main_bus_stop
        command = Command(self.data.request.nlu.tokens)
        self.command_type = command.type
        self.bus_name = command.bus_name
        self.bus_stop_name = command.bus_stop_name
        self.guiding_bus_stop_name = command.guiding_bus_stop_name

    def _get_yandex_user_from_request(self):
        if hasattr(self.data.session, 'user'):
            yandex_id = self.data.session.user.user_id
            return YandexUser.objects.get_or_create(yandex_id=yandex_id)[0]
        return None

    def get_response(self):
        response = {
            'version': self.data.version,
            'response': {
                'text': self._get_response_text(),
                'end_session': False,
            },
        }
        return Response(response)

    def _get_response_text(self):
        command_type_to_method_for_getting_response_text = {
            "remember main bus schedule": self._remember_main_bus_schedule,
            "get main bus schedule": self._get_main_bus_schedule,
            "get bus schedule": self._get_bus_schedule,
            "get bus schedules": self._get_bus_schedules,
            "unknown command": self._get_text_when_no_command,
        }
        return command_type_to_method_for_getting_response_text[self.command_type]()

    @validate('yandex_user', 'bus_name', 'bus_stop_name', 'guiding_bus_stop_name')
    def _remember_main_bus_schedule(self):
        self.yandex_user.main_bus_stop = self._get_bus_stop_from_command()
        self.yandex_user.save()
        return 'Я запомнила ваш автобус, теперь вы можете спрашивать у меня расписание автобуса в любое время'

    @validate('yandex_user', 'main_bus_stop')
    def _get_main_bus_schedule(self):
        return self._get_text_bus_schedule(self.main_bus_stop)

    @validate('bus_name', 'bus_stop_name', 'guiding_bus_stop_name')
    def _get_bus_schedule(self):
        return self._get_text_bus_schedule(self._get_bus_stop_from_command())

    @validate('bus_stop_name', 'guiding_bus_stop_name')
    def _get_bus_schedules(self):
        bus_stops = self._get_bus_stops_from_command()
        return ". ".join(self._get_text_bus_schedule(bus_stop) for bus_stop in bus_stops)

    @staticmethod
    def _get_text_when_no_command():
        return "Извините, я вас не поняла"

    def _get_bus_stop_from_command(self):
        directions = self._get_directions_from_command()
        return BusStop.objects.filter(name=self.bus_stop_name, direction__in=directions,
                                      direction__bus__name=self.bus_name).first()

    def _get_bus_stops_from_command(self):
        directions = self._get_directions_from_command()
        return BusStop.objects.filter(name=self.bus_stop_name, direction__in=directions)

    def _get_directions_from_command(self):
        directions_with_specified_bus_stops = Direction.objects.filter(bus_stops__name=self.bus_stop_name)
        directions_from_bus_stop_to_guiding_bus_stop = self._filter_directions_by_bus_stop(
            directions=directions_with_specified_bus_stops,
            first_bus_stop_name=self.bus_stop_name,
            second_bus_stop_name=self.guiding_bus_stop_name
        )
        bus_stop_names = self._get_bus_stop_names_after_specified_bus_stop_name(
            bus_stop_name=self.bus_stop_name,
            directions=directions_from_bus_stop_to_guiding_bus_stop
        )
        directions = []
        for bus_stop_name in bus_stop_names:
            filtered_directions = self._filter_directions_by_bus_stop(
                directions=directions_with_specified_bus_stops,
                first_bus_stop_name=self.bus_stop_name,
                second_bus_stop_name=bus_stop_name
            )
            directions.extend(filtered_directions)
        return directions

    def _filter_directions_by_bus_stop(self, directions, first_bus_stop_name, second_bus_stop_name):
        filtered_directions = []
        for direction in directions:
            if (self._is_direction_from_first_bus_stop_to_second_bus_stop(
                    direction, first_bus_stop_name, second_bus_stop_name)):
                filtered_directions.append(direction)
        return filtered_directions

    @staticmethod
    def _is_direction_from_first_bus_stop_to_second_bus_stop(direction, first_bus_stop_name, second_bus_stop_name):
        is_found_first_bus_stop = False
        for bus_stop in direction.bus_stops.all():
            if bus_stop.name == first_bus_stop_name:
                is_found_first_bus_stop = True
            if bus_stop.name == second_bus_stop_name and is_found_first_bus_stop:
                return True
        return False

    def _get_bus_stop_names_after_specified_bus_stop_name(self, bus_stop_name, directions):
        bus_stops_names = set()
        for direction in directions:
            bus_stop_name_after_specified_bus_stop_name = self._get_bus_stop_name_after_specified_bus_stop_name(
                bus_stop_name=bus_stop_name,
                direction=direction
            )
            bus_stops_names.add(bus_stop_name_after_specified_bus_stop_name)
        return bus_stops_names

    @staticmethod
    def _get_bus_stop_name_after_specified_bus_stop_name(bus_stop_name, direction):
        bus_stops = direction.bus_stops.all()
        for index, bus_stop in enumerate(bus_stops):
            if bus_stop.name == bus_stop_name:
                return bus_stops[index + 1].name

    def _get_text_bus_schedule(self, bus_stop):
        if not self.yandex_user or self.yandex_user.time_format == 'time':
            nearest_time, next_time = self._get_current_bus_times(bus_stop)
            bus_name = bus_stop.direction.bus.name
            return f'Автобус номер {bus_name} будет в {nearest_time}, а следующий в {next_time}'
        nearest_time_interval, next_time_interval = self._get_current_bus_time_interval(bus_stop)
        bus_name = bus_stop.direction.bus.name
        if nearest_time_interval and next_time_interval:
            return f'Автобус номер {bus_name} будет через {nearest_time_interval}, а следующий через ' \
                   f'{next_time_interval}'
        return ""

    def _get_current_bus_time_interval(self, bus_stop):
        schedules_for_today_and_tomorrow = self._get_schedules_for_today_and_tomorrow(bus_stop)
        current_bus_times = [
            time for time in schedules_for_today_and_tomorrow if self._is_current_bus_time(time)
        ]
        if len(current_bus_times) >= 2:
            now = datetime.now()
            humanize.i18n.activate("ru_RU")
            return [humanize.naturaldelta(x - now) for x in current_bus_times[:2]]
        return False, False

    def _get_current_bus_times(self, bus_stop):
        schedules_for_today_and_tomorrow = self._get_schedules_for_today_and_tomorrow(bus_stop)
        current_bus_times = [
            time for time in schedules_for_today_and_tomorrow if self._is_current_bus_time(time)
        ]
        return (x.strftime("%H %M") if x.hour > 9 else x.strftime("%H %M")[1:] for x in current_bus_times[:2])

    def _get_schedules_for_today_and_tomorrow(self, bus_stop):
        schedules_for_today = self._get_schedules_for_today(bus_stop)
        schedules_for_tomorrow = self._get_schedules_for_tomorrow(bus_stop)
        return schedules_for_today + schedules_for_tomorrow

    @staticmethod
    def _get_schedules_for_today(bus_stop):
        date_string = datetime.now().strftime("%Y-%m-%d")
        params = {
            "city": "brest",
            "transport": "autobus",
            "route": bus_stop.direction.bus.name,
            "direction": bus_stop.direction.name,
            "busStop": bus_stop.name,
            "date": date_string,
        }
        response = requests.get("https://kogda.by/api/getTimetable", params, headers={'User-Agent': 'Mozilla/5.0'})
        timetable = response.json()["timetable"]
        return [datetime.strptime(x + " " + date_string, "%H:%M %Y-%m-%d") for x in timetable]

    @staticmethod
    def _get_schedules_for_tomorrow(bus_stop):
        date_for_tomorrow = datetime.now() + timedelta(days=1)
        date_string = date_for_tomorrow.strftime("%Y-%m-%d")
        params = {
            "city": "brest",
            "transport": "autobus",
            "route": bus_stop.direction.bus.name,
            "direction": bus_stop.direction.name,
            "busStop": bus_stop.name,
            "date": date_string,
        }
        response = requests.get("https://kogda.by/api/getTimetable", params, headers={'User-Agent': 'Mozilla/5.0'})
        timetable = response.json()["timetable"]
        return [datetime.strptime(x + " " + date_string, "%H:%M %Y-%m-%d") for x in timetable]

    @staticmethod
    def _is_current_bus_time(bus_time):
        delta = bus_time - datetime.now()
        delta_minutes = delta.seconds / 60
        if delta.days >= 0 and delta_minutes > 2:
            return True
        return False
