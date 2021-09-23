import asyncio
import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import aiohttp

from django.utils.timezone import make_aware
from asgiref.sync import sync_to_async
from .models import Bus, BusStop, Direction


MAIN_URL = "https://kogda.by/routes/brest/autobus/"


async def get_names_of_buses(session):
    url = MAIN_URL
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
        text = await response.text()
        soup = BeautifulSoup(text, 'html.parser')
        names = soup.find_all('a', class_='btn btn-primary bold route')
        return [x.text.strip() for x in names]


async def create_buses(session):
    buses = []
    names_of_buses = await get_names_of_buses(session)
    for name_of_bus in names_of_buses:
        bus = await sync_to_async(Bus.objects.create)(name=name_of_bus)
        buses.append(bus)
    return buses


async def get_names_of_directions(bus, session):
    url = MAIN_URL + f"{bus.name}/"
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
        soup = BeautifulSoup(await response.text(), 'html.parser')
        names = soup.find_all('a', {'data-parent': '#directions'})
        return [x.text.strip() for x in names]


async def create_directions(bus, session):
    directions = []
    names_of_directions = await get_names_of_directions(bus, session)
    for name_of_direction in names_of_directions:
        direction = await sync_to_async(Direction.objects.create)(name=name_of_direction, bus=bus)
        directions.append(direction)
    return directions


async def get_names_of_bus_stops(direction, session):
    url = MAIN_URL + f"{direction.bus.name}/"
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
        soup = BeautifulSoup(await response.text(), 'html.parser')
        direction_number = soup.find("a", text=re.compile(direction.name)).attrs['href']
        bus_stops = soup.select(f"{direction_number} > ul > li")
        return [x.find("a").text.strip() for x in bus_stops]


async def get_schedule(bus_stop, session):
    date_for_today = datetime.now()
    schedules_for_today = await get_schedule_for_date(bus_stop, date_for_today, session)
    date_for_tomorrow = datetime.now() + timedelta(days=1)
    schedules_for_tomorrow = await get_schedule_for_date(bus_stop, date_for_tomorrow, session)
    return schedules_for_today + schedules_for_tomorrow


async def get_schedule_for_date(bus_stop, date, session):
    url = "https://kogda.by/api/getTimetable"
    date_string = date.strftime("%Y-%m-%d")
    params = {
        "city": "brest",
        "transport": "autobus",
        "route": bus_stop.direction.bus.name,
        "direction": bus_stop.direction.name,
        "busStop": bus_stop.name,
        "date": date_string,
    }
    async with session.get(url, params=params, headers={'User-Agent': 'Mozilla/5.0'}) as response:
        timetable = await response.json()
        timetable = await get_fixed_text_times(timetable["timetable"])
    return [make_aware(datetime.strptime(x + " " + date_string, "%H:%M %Y-%m-%d")) for x in timetable]


async def get_fixed_text_times(text_times):
    fixed_text_times = []
    for text_time in text_times:
        if len(text_time) == 11:
            text_time = await get_fixed_two_text_times(text_time)
            fixed_text_times.extend(text_time)
        else:
            text_time = await get_fixed_59_text_time(text_time)
            fixed_text_times.append(text_time)
    return fixed_text_times


async def get_fixed_59_text_time(text_time):
    if int(text_time.split(":")[1]) > 59:
        return f"{text_time.split(':')[0]}:59"
    return text_time


async def get_fixed_two_text_times(text_time):
    if len(text_time) == 11:
        first_text_time = await get_fixed_59_text_time(text_time[:5])
        second_text_time = await get_fixed_59_text_time(text_time[6:11])
        return [first_text_time, second_text_time]
    return text_time


async def create_bus_stops(direction, session):
    bus_stops = []
    names_of_bus_stops = await get_names_of_bus_stops(direction, session)
    for name_of_bus_stop in names_of_bus_stops:
        bus_stop = await sync_to_async(BusStop.objects.create)(name=name_of_bus_stop, direction=direction)
        bus_stop.schedule = await get_schedule(bus_stop, session)
        await sync_to_async(bus_stop.save)()
        bus_stops.append(bus_stop)
    return bus_stops


async def create_directions_and_bus_stops(bus, session):
    directions = await create_directions(bus, session)
    for direction in directions:
        await create_bus_stops(direction, session)


def _delete_buses():
    Bus.objects.all().delete()


def _delete_directions():
    Direction.objects.all().delete()


def _delete_bus_stops():
    BusStop.objects.all().delete()


async def delete_all_objects():
    buses = await sync_to_async(Bus.objects.all)()
    await sync_to_async(buses.delete)()
    directions = await sync_to_async(Direction.objects.all)()
    await sync_to_async(directions.delete)()
    bus_stops = await sync_to_async(BusStop.objects.all)()
    await sync_to_async(bus_stops.delete)()


async def update_all_db():
    now = datetime.now()
    await delete_all_objects()
    async with aiohttp.ClientSession() as session:
        buses = await create_buses(session)
        tasks = []
        for bus in buses:
            task = asyncio.create_task(create_directions_and_bus_stops(bus, session))
            tasks.append(task)
        await asyncio.gather(*tasks)
        now2 = datetime.now()
        duration = now2 - now
        return duration.total_seconds()
